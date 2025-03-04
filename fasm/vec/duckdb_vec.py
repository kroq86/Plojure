import duckdb
import numpy as np
from typing import List, Tuple, Optional, Dict
import ctypes
from ctypes import CDLL, POINTER, c_double, c_int
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import sys
from collections import OrderedDict

class DuckDBVectorDatabase:
    def __init__(self, db_path: str = ':memory:', chunk_size: int = 1000, max_cache_size: int = 1024 * 1024 * 1024):
        self.conn = duckdb.connect(db_path)
        self.chunk_size = chunk_size
        self.max_cache_size = max_cache_size
        self.load_library()
        self._initialize_db()
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._cache_lock = Lock()
        self._current_cache_size = 0

    def load_library(self):
        self.mylib = CDLL('./mylib.so')
        self.mylib.py_dot_product.argtypes = [POINTER(c_double), POINTER(c_double), c_int]
        self.mylib.py_dot_product.restype = c_double
        self.mylib.py_vector_norm.argtypes = [POINTER(c_double), c_int]
        self.mylib.py_vector_norm.restype = c_double

    def _initialize_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                key VARCHAR PRIMARY KEY,
                vector BLOB,
                dimensions INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                partition_id INTEGER
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_key ON vectors(key)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_partition ON vectors(partition_id)")

    def _serialize_vector(self, vector: List[float]) -> bytes:
        return np.array(vector, dtype=np.float64).tobytes()

    def _deserialize_vector(self, data: bytes, dimensions: int) -> List[float]:
        return list(np.frombuffer(data, dtype=np.float64))

    def _get_cached_vector(self, key: str) -> Optional[List[float]]:
        with self._cache_lock:
            return self._cache.get(key)

    def _monitor_cache_size(self, vector: List[float]) -> int:
        return sys.getsizeof(vector) + sys.getsizeof(float()) * len(vector)

    def _evict_cache(self):
        with self._cache_lock:
            while self._current_cache_size > self.max_cache_size and self._cache:
                _, vector = self._cache.popitem(last=False)
                self._current_cache_size -= self._monitor_cache_size(vector)

    def _set_cached_vector(self, key: str, vector: List[float]):
        with self._cache_lock:
            vector_size = self._monitor_cache_size(vector)
            if key in self._cache:
                self._current_cache_size -= self._monitor_cache_size(self._cache[key])
            self._cache[key] = vector
            self._current_cache_size += vector_size
            if self._current_cache_size > self.max_cache_size:
                self._evict_cache()

    def insert(self, key: str, vector: List[float], partition_id: Optional[int] = None) -> None:
        if partition_id is None:
            partition_id = hash(key) % (self.chunk_size)
        
        vector_data = self._serialize_vector(vector)
        self.conn.execute("""
            INSERT OR REPLACE INTO vectors (key, vector, dimensions, partition_id)
            VALUES (?, ?, ?, ?)
        """, [key, vector_data, len(vector), partition_id])
        self._set_cached_vector(key, vector)

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
            similarity = self.cosine_similarity(query_vector, vector)
            similarities.append((key, similarity))
        return similarities

    def search(self, query_vector: List[float], k: int, num_threads: int = 4) -> List[Tuple[str, float]]:
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
        
        # Stratified sampling across partitions
        sampled_vectors = self.conn.execute("""
            WITH partitions AS (
                SELECT DISTINCT partition_id,
                       COUNT(*) OVER (PARTITION BY partition_id) as partition_size
                FROM vectors
            )
            SELECT v.key, v.vector, v.dimensions 
            FROM vectors v
            JOIN partitions p ON v.partition_id = p.partition_id
            WHERE random() <= ? * (1.0 + LOG(p.partition_size))
            ORDER BY random()
            LIMIT ?
        """, [sample_ratio, sample_size]).fetchall()
        
        similarities = self._process_partition(sampled_vectors, query_vector)
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