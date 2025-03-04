import duckdb
import numpy as np
from typing import List, Tuple, Optional, Dict, Callable, Literal
import ctypes
from ctypes import CDLL, POINTER, c_double, c_int
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import sys
from collections import OrderedDict
import random
from dataclasses import dataclass
import psutil
import time

@dataclass
class PerformanceMetrics:
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage: float = 0.0
    total_vectors: int = 0
    total_dimensions: int = 0
    cache_size: int = 0

@dataclass
class SearchMetrics:
    exact_time: float = 0.0
    approx_time: float = 0.0
    lsh_time: float = 0.0
    recall_at_k: float = 0.0
    precision_at_k: float = 0.0
    memory_used: float = 0.0
    cache_hit_ratio: float = 0.0

class LSHIndex:
    def __init__(self, num_hash_functions: int = 20, num_bands: int = 10):
        self.num_hash_functions = num_hash_functions
        self.num_bands = num_bands
        self.hash_ranges = None
        self.dimensions = None
        self.bucket_dict: Dict[int, List[str]] = {}
        self.vector_count = 0
    
    def _initialize_hash_ranges(self, dimensions: int):
        if self.dimensions != dimensions:
            self.dimensions = dimensions
            # Use normal distribution for better hyperplane separation
            self.hash_ranges = np.random.normal(0, 1, (self.num_hash_functions, dimensions))
            # Normalize the hash ranges
            self.hash_ranges /= np.linalg.norm(self.hash_ranges, axis=1)[:, np.newaxis]
    
    def _hash_vector(self, vector: List[float]) -> List[int]:
        vector_array = np.array(vector, dtype=np.float64)
        if self.hash_ranges is None or self.dimensions != len(vector):
            self._initialize_hash_ranges(len(vector))
        # Normalize the input vector
        vector_array /= np.linalg.norm(vector_array)
        projections = np.dot(self.hash_ranges, vector_array)
        return (projections > 0).astype(int).tolist()
    
    def insert(self, key: str, vector: List[float]):
        self.vector_count += 1
        hash_signature = self._hash_vector(vector)
        
        # Use multiple bands for better recall
        for band in range(self.num_bands):
            start_idx = band * (self.num_hash_functions // self.num_bands)
            end_idx = start_idx + (self.num_hash_functions // self.num_bands)
            band_signature = tuple(hash_signature[start_idx:end_idx])
            band_hash = hash((band, band_signature))
            
            if band_hash not in self.bucket_dict:
                self.bucket_dict[band_hash] = []
            self.bucket_dict[band_hash].append(key)
    
    def query(self, vector: List[float], min_candidates: int = 100) -> List[str]:
        hash_signature = self._hash_vector(vector)
        candidate_keys = set()
        
        # Query all bands
        for band in range(self.num_bands):
            start_idx = band * (self.num_hash_functions // self.num_bands)
            end_idx = start_idx + (self.num_hash_functions // self.num_bands)
            band_signature = tuple(hash_signature[start_idx:end_idx])
            band_hash = hash((band, band_signature))
            
            if band_hash in self.bucket_dict:
                candidate_keys.update(self.bucket_dict[band_hash])
        
        # If too few candidates, use more bands or return all keys
        if len(candidate_keys) < min_candidates:
            return list(set().union(*self.bucket_dict.values()))
        
        return list(candidate_keys)

class DuckDBVectorDatabase:
    def __init__(self, 
                 db_path: str = ':memory:', 
                 chunk_size: int = 1000, 
                 max_cache_size: int = 1024 * 1024 * 1024,
                 similarity_metric: Literal["cosine", "euclidean", "dot_product"] = "cosine"):
        self.conn = duckdb.connect(db_path)
        self.chunk_size = chunk_size
        self.max_cache_size = max_cache_size
        self.similarity_metric = similarity_metric
        self.load_library()
        self._initialize_db()
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._cache_lock = Lock()
        self._current_cache_size = 0
        self.metrics = PerformanceMetrics()
        self.lsh_index = LSHIndex()
        self._vector_dimension = None

    def load_library(self):
        self.mylib = CDLL('./mylib.so')
        self.mylib.py_dot_product.argtypes = [POINTER(c_double), POINTER(c_double), c_int]
        self.mylib.py_dot_product.restype = c_double
        self.mylib.py_vector_norm.argtypes = [POINTER(c_double), c_int]
        self.mylib.py_vector_norm.restype = c_double

    def _initialize_db(self):
        # Drop existing indices first to avoid conflicts
        self.conn.execute("DROP INDEX IF EXISTS idx_vectors_key")
        self.conn.execute("DROP INDEX IF EXISTS idx_vectors_partition")
        
        # Drop and recreate table
        self.conn.execute("DROP TABLE IF EXISTS vectors")
        self.conn.execute("""
            CREATE TABLE vectors (
                key VARCHAR PRIMARY KEY,
                vector BLOB,
                dimensions INTEGER,
                partition_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indices after table
        self.conn.execute("CREATE INDEX idx_vectors_key ON vectors(key)")
        self.conn.execute("CREATE INDEX idx_vectors_partition ON vectors(partition_id)")

    def _serialize_vector(self, vector: List[float]) -> bytes:
        return np.array(vector, dtype=np.float64).tobytes()

    def _deserialize_vector(self, data: bytes, dimensions: int) -> List[float]:
        return list(np.frombuffer(data, dtype=np.float64))

    def _get_cached_vector(self, key: str) -> Optional[List[float]]:
        with self._cache_lock:
            vector = self._cache.get(key)
            if vector is not None:
                self.metrics.cache_hits += 1
            else:
                self.metrics.cache_misses += 1
            return vector

    def _monitor_cache_size(self, vector: List[float]) -> int:
        # More accurate memory calculation: 8 bytes per double + Python list overhead
        return len(vector) * 8 + 64  # 64 bytes for Python list overhead

    def _evict_cache(self):
        with self._cache_lock:
            # Evict in larger chunks for better efficiency
            target_size = self.max_cache_size * 0.8  # Keep 20% free
            while self._current_cache_size > target_size and self._cache:
                for _ in range(min(100, len(self._cache))):  # Evict up to 100 items at once
                    _, vector = self._cache.popitem(last=False)
                    self._current_cache_size -= self._monitor_cache_size(vector)
                if self._current_cache_size <= target_size:
                    break

    def _set_cached_vector(self, key: str, vector: List[float]):
        with self._cache_lock:
            vector_size = self._monitor_cache_size(vector)
            if key in self._cache:
                self._current_cache_size -= self._monitor_cache_size(self._cache[key])
            self._cache[key] = vector
            self._current_cache_size += vector_size
            if self._current_cache_size > self.max_cache_size:
                self._evict_cache()

    def get_metrics(self) -> PerformanceMetrics:
        process = psutil.Process()
        self.metrics.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        self.metrics.cache_size = self._current_cache_size
        self.metrics.total_vectors = self.conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        return self.metrics

    def _calculate_similarity(self, v1: List[float], v2: List[float]) -> float:
        v1_array = (c_double * len(v1))(*v1)
        v2_array = (c_double * len(v2))(*v2)

        if self.similarity_metric == "cosine":
            dot_product = self.mylib.py_dot_product(v1_array, v2_array, len(v1))
            norm_v1 = self.mylib.py_vector_norm(v1_array, len(v1))
            norm_v2 = self.mylib.py_vector_norm(v2_array, len(v2))
            
            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
            return dot_product / (norm_v1 * norm_v2)
        
        elif self.similarity_metric == "euclidean":
            diff = np.array(v1) - np.array(v2)
            return -np.sqrt(np.sum(diff * diff))  # Negative because larger values should be "more similar"
        
        else:  # dot_product
            return self.mylib.py_dot_product(v1_array, v2_array, len(v1))

    def insert(self, key: str, vector: List[float], partition_id: Optional[int] = None) -> None:
        if partition_id is None:
            partition_id = hash(key) % (self.chunk_size)
        
        vector_data = self._serialize_vector(vector)
        self.conn.execute("""
            INSERT OR REPLACE INTO vectors (key, vector, dimensions, partition_id)
            VALUES (?, ?, ?, ?)
        """, [key, vector_data, len(vector), partition_id])
        self._set_cached_vector(key, vector)
        self.lsh_index.insert(key, vector)

    def retrieve(self, key: str) -> List[float]:
        cached = self._get_cached_vector(key)
        if cached is not None:
            return cached

        result = self.conn.execute("""
            SELECT vector, dimensions FROM vectors WHERE key = ?
        """, [key]).fetchone()
        
        if result is None:
            return None
        
        vector_data, dimensions = result
        vector = self._deserialize_vector(vector_data, dimensions)
        self._set_cached_vector(key, vector)
        return vector

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if len(v1) != len(v2):
            raise ValueError("Vectors must have the same dimensions")

        v1_array = (c_double * len(v1))(*v1)
        v2_array = (c_double * len(v2))(*v2)

        dot_product = self.mylib.py_dot_product(v1_array, v2_array, len(v1))
        norm_v1 = self.mylib.py_vector_norm(v1_array, len(v1))
        norm_v2 = self.mylib.py_vector_norm(v2_array, len(v2))

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return dot_product / (norm_v1 * norm_v2)

    def _process_partition(self, partition_vectors: List[Tuple[str, bytes, int]], query_vector: List[float]) -> List[Tuple[str, float]]:
        similarities = []
        for key, vector_data, dimensions in partition_vectors:
            vector = self._deserialize_vector(vector_data, dimensions)
            similarity = self._calculate_similarity(query_vector, vector)
            similarities.append((key, similarity))
        return similarities

    def search(self, query_vector: List[float], k: int, method: Literal["exact", "approximate", "lsh"] = "exact", num_threads: int = 4) -> List[Tuple[str, float]]:
        if method == "lsh":
            return self.lsh_search(query_vector, k)
        elif method == "approximate":
            return self.approximate_search(query_vector, k, self.chunk_size // 10)
        else:
            return self._exact_search(query_vector, k, num_threads)

    def _exact_search(self, query_vector: List[float], k: int, num_threads: int = 4) -> List[Tuple[str, float]]:
        all_partitions = self.conn.execute("""
            SELECT DISTINCT partition_id FROM vectors
        """).fetchall()
        
        all_similarities = []
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            
            for (partition_id,) in all_partitions:
                partition_vectors = self.conn.execute("""
                    SELECT key, vector, dimensions 
                    FROM vectors 
                    WHERE partition_id = ?
                """, [partition_id]).fetchall()
                
                future = executor.submit(self._process_partition, partition_vectors, query_vector)
                futures.append(future)
            
            for future in futures:
                all_similarities.extend(future.result())
        
        all_similarities.sort(key=lambda x: x[1], reverse=True)
        return all_similarities[:k]

    def lsh_search(self, query_vector: List[float], k: int) -> List[Tuple[str, float]]:
        # Get candidates from LSH with increased min_candidates
        candidate_keys = self.lsh_index.query(query_vector, min_candidates=k * 10)
        if not candidate_keys or len(candidate_keys) < k:
            # Fallback to approximate search if too few candidates
            return self.approximate_search(query_vector, k, self.chunk_size // 5)
        
        # Batch retrieve vectors for better performance
        placeholders = ','.join(['?' for _ in candidate_keys])
        vectors_data = self.conn.execute(f"""
            SELECT key, vector, dimensions 
            FROM vectors 
            WHERE key IN ({placeholders})
            LIMIT ?  -- Limit the number of vectors to process
        """, [*candidate_keys, min(len(candidate_keys), k * 20)]).fetchall()
        
        # Calculate similarities in parallel
        similarities = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for key, vector_data, dimensions in vectors_data:
                vector = self._deserialize_vector(vector_data, dimensions)
                self._set_cached_vector(key, vector)
                future = executor.submit(self._calculate_similarity, query_vector, vector)
                futures.append((key, future))
            
            for key, future in futures:
                similarity = future.result()
                similarities.append((key, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

    def batch_insert(self, vectors: List[Tuple[str, List[float]]], partition_size: Optional[int] = None) -> None:
        if partition_size is None:
            partition_size = self.chunk_size

        try:
            self.conn.execute("BEGIN TRANSACTION")
            
            for i in range(0, len(vectors), 1000):  # Process in chunks of 1000
                batch = vectors[i:i + 1000]
                data = []
                for j, (key, vec) in enumerate(batch):
                    partition_id = (i + j) // partition_size
                    data.append((key, self._serialize_vector(vec), len(vec), partition_id))
                    self._set_cached_vector(key, vec)
                
                self.conn.executemany("""
                    INSERT OR REPLACE INTO vectors (key, vector, dimensions, partition_id)
                    VALUES (?, ?, ?, ?)
                """, data)
            
            self.conn.execute("COMMIT")
        except Exception as e:
            self.conn.execute("ROLLBACK")
            raise Exception(f"Batch insert failed: {str(e)}")

    def approximate_search(self, query_vector: List[float], k: int, sample_size: int) -> List[Tuple[str, float]]:
        total_vectors = self.conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        sample_ratio = min(1.0, sample_size / total_vectors)
        
        # Improved stratified sampling with better partition coverage
        sampled_vectors = self.conn.execute("""
            WITH partitions AS (
                SELECT DISTINCT partition_id,
                       COUNT(*) OVER (PARTITION BY partition_id) as partition_size,
                       SUM(1) OVER () as total_vectors
                FROM vectors
            )
            SELECT v.key, v.vector, v.dimensions 
            FROM vectors v
            JOIN partitions p ON v.partition_id = p.partition_id
            WHERE random() <= ? * (1.0 + LOG10(p.partition_size))
                  OR partition_size <= ?  -- Include all vectors from small partitions
            ORDER BY random()
            LIMIT ?
        """, [
            sample_ratio * 3,  # Triple the sample ratio
            k * 2,  # Small partition threshold
            sample_size * 4  # Quadruple the sample size
        ]).fetchall()
        
        # Process in parallel for better performance
        similarities = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for key, vector_data, dimensions in sampled_vectors:
                vector = self._deserialize_vector(vector_data, dimensions)
                self._set_cached_vector(key, vector)
                future = executor.submit(self._calculate_similarity, query_vector, vector)
                futures.append((key, future))
            
            for key, future in futures:
                similarity = future.result()
                similarities.append((key, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

    def delete(self, key: str) -> bool:
        with self._cache_lock:
            self._cache.pop(key, None)
        
        affected = self.conn.execute("""
            DELETE FROM vectors WHERE key = ?
        """, [key]).rowcount
        return affected > 0

    def get_all_keys(self) -> List[str]:
        return [row[0] for row in self.conn.execute("SELECT key FROM vectors").fetchall()]

    def clear_cache(self):
        with self._cache_lock:
            self._cache.clear()

    def close(self):
        self.clear_cache()
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def calculate_recall(self, exact_results: List[Tuple[str, float]], 
                        approx_results: List[Tuple[str, float]], k: int) -> float:
        if not exact_results or not approx_results:
            return 0.0
            
        # Get top-k results
        exact_keys = set(key for key, _ in exact_results[:k])
        approx_keys = set(key for key, _ in approx_results[:k])
        
        # Calculate intersection
        common_keys = exact_keys.intersection(approx_keys)
        
        # Calculate recall
        recall = len(common_keys) / min(k, len(exact_keys)) if exact_keys else 0.0
        
        return recall

    def search_with_metrics(self, query_vector: List[float], k: int) -> SearchMetrics:
        metrics = SearchMetrics()
        process = psutil.Process()
        
        # Exact search
        start_time = time.time()
        exact_results = self._exact_search(query_vector, k)
        metrics.exact_time = time.time() - start_time
        
        # Approximate search
        start_time = time.time()
        approx_results = self.approximate_search(query_vector, k, self.chunk_size // 10)
        metrics.approx_time = time.time() - start_time
        
        # LSH search
        start_time = time.time()
        lsh_results = self.lsh_search(query_vector, k)
        metrics.lsh_time = time.time() - start_time
        
        # Calculate recall for both approximate methods
        metrics.recall_at_k = max(
            self.calculate_recall(exact_results, approx_results, k),
            self.calculate_recall(exact_results, lsh_results, k)
        )
        
        # Memory and cache metrics
        metrics.memory_used = process.memory_info().rss / 1024 / 1024
        total_ops = self.metrics.cache_hits + self.metrics.cache_misses
        metrics.cache_hit_ratio = self.metrics.cache_hits / total_ops if total_ops > 0 else 0
        
        return metrics 