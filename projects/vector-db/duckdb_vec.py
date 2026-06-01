import duckdb
import numpy as np
import platform
from typing import List, Tuple, Optional, Dict, Callable, Literal, Set, Union
from ctypes import CDLL, POINTER, c_double, c_float, c_int, c_ubyte
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import hashlib
import heapq
import json
import os
import psutil
import random
import re
import threading
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


@dataclass
class DocumentChunk:
    key: str
    path: str
    content: str
    start_line: int
    end_line: int
    metadata: Dict[str, str]


@dataclass
class ChunkSymbol:
    key: str
    path: str
    symbol: str
    symbol_lower: str
    start_line: int
    end_line: int


@dataclass
class PartitionBatch:
    keys: List[str]
    matrix: np.ndarray
    dimensions: int
    normalized_matrix: Optional[np.ndarray] = None
    matrix_f32: Optional[np.ndarray] = None
    normalized_matrix_f32: Optional[np.ndarray] = None

class LSHIndex:
    def __init__(self, num_hash_functions: int = 20, num_bands: int = 10):
        self.num_hash_functions = num_hash_functions
        self.num_bands = num_bands
        self.hash_ranges = None
        self.hash_ranges_f32 = None
        self.dimensions = None
        self.bucket_dict: Dict[int, List[str]] = {}
        self.vector_count = 0
        self._native_signatures = None
    
    def _initialize_hash_ranges(self, dimensions: int):
        if self.dimensions != dimensions:
            self.dimensions = dimensions
            # Use normal distribution for better hyperplane separation
            self.hash_ranges = np.random.normal(0, 1, (self.num_hash_functions, dimensions))
            # Normalize the hash ranges
            self.hash_ranges /= np.linalg.norm(self.hash_ranges, axis=1)[:, np.newaxis]
            self.hash_ranges_f32 = np.ascontiguousarray(self.hash_ranges.astype(np.float32))

    def set_native_signatures(self, callback: Optional[Callable[[List[float], np.ndarray], List[int]]]) -> None:
        self._native_signatures = callback
    
    def _hash_vector(self, vector: List[float]) -> List[int]:
        if self.hash_ranges is None or self.dimensions != len(vector):
            self._initialize_hash_ranges(len(vector))
        if self._native_signatures is not None and self.hash_ranges_f32 is not None:
            return self._native_signatures(vector, self.hash_ranges_f32)
        vector_array = np.array(vector, dtype=np.float64)
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
                 db_path: str = 'vectors.duckdb', 
                 chunk_size: int = 1000, 
                 max_cache_size: int = 1024 * 1024 * 1024,
                 similarity_metric: Literal["cosine", "euclidean", "dot_product"] = "cosine",
                 embedding_dimension: int = 256,
                 embedding_provider: Optional[str] = None,
                 embedding_model: Optional[str] = None,
                 use_asm: Optional[bool] = None):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        # DuckDB автоматически сохраняет данные при закрытии соединения
        self.chunk_size = chunk_size
        self.max_cache_size = max_cache_size
        self.similarity_metric = similarity_metric
        self.embedding_dimension = embedding_dimension
        self.embedding_provider = embedding_provider or os.environ.get("EMBEDDING_PROVIDER", "auto")
        self.embedding_model = embedding_model or os.environ.get("EMBEDDING_MODEL")
        self.embedding_cache_dir = os.environ.get("EMBEDDING_CACHE_DIR") or os.environ.get("FASTEMBED_CACHE_PATH")
        env_use_asm = os.environ.get("USE_ASM")
        self.use_asm = use_asm if use_asm is not None else env_use_asm not in {"0", "false", "False"}
        self._embedding_backend = "hash"
        self._fastembed_model = None
        self._sentence_transformer = None
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._cache_lock = Lock()
        self._partition_batches: Dict[Tuple[int, int], PartitionBatch] = {}
        self._partition_batch_lock = Lock()
        self._write_lock = threading.RLock()
        self._current_cache_size = 0
        self.metrics = PerformanceMetrics()
        self.lsh_index = LSHIndex()
        self.lsh_index.set_native_signatures(self._hash_vector_native_f32)
        self._vector_dimension = None
        self._initialize_embedding_backend()
        self.load_library()
        self._initialize_db()
        self._rebuild_lsh_index()

    def _initialize_embedding_backend(self):
        provider = (self.embedding_provider or "auto").lower()
        if provider in {"auto", "fastembed"}:
            try:
                from fastembed import TextEmbedding

                model_name = self.embedding_model or "BAAI/bge-small-en-v1.5"
                kwargs = {"model_name": model_name}
                if self.embedding_cache_dir:
                    Path(self.embedding_cache_dir).mkdir(parents=True, exist_ok=True)
                    kwargs["cache_dir"] = self.embedding_cache_dir
                self._fastembed_model = TextEmbedding(**kwargs)
                self._embedding_backend = "fastembed"
                self.embedding_model = model_name
                return
            except Exception:
                if provider == "fastembed":
                    raise

        if provider in {"auto", "sentence_transformers"}:
            try:
                from sentence_transformers import SentenceTransformer

                model_name = self.embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
                kwargs = {}
                if self.embedding_cache_dir:
                    Path(self.embedding_cache_dir).mkdir(parents=True, exist_ok=True)
                    kwargs["cache_folder"] = self.embedding_cache_dir
                self._sentence_transformer = SentenceTransformer(model_name, **kwargs)
                self._embedding_backend = "sentence_transformers"
                self.embedding_model = model_name
                return
            except Exception:
                if provider == "sentence_transformers":
                    raise

        if provider == "openai":
            self._embedding_backend = "openai"
            return

        self._embedding_backend = "hash"

    def load_library(self):
        if not self.use_asm:
            self.mylib = None
            return

        suffix = ".dylib" if platform.system() == "Darwin" else ".so"
        library_paths = [
            Path(__file__).resolve().with_name(f"dot_product{suffix}"),
            Path.cwd() / f"dot_product{suffix}",
            Path(__file__).resolve().with_name(f"mylib{suffix}"),
            Path.cwd() / f"mylib{suffix}",
        ]

        self.mylib = None
        for library_path in library_paths:
            if not library_path.exists():
                continue

            try:
                self.mylib = CDLL(str(library_path))
                self.mylib.py_dot_product.argtypes = [POINTER(c_double), POINTER(c_double), c_int]
                self.mylib.py_dot_product.restype = c_double
                self.mylib.py_vector_norm.argtypes = [POINTER(c_double), c_int]
                self.mylib.py_vector_norm.restype = c_double
                self.mylib.py_squared_distance.argtypes = [POINTER(c_double), POINTER(c_double), c_int]
                self.mylib.py_squared_distance.restype = c_double
                self.mylib.py_batch_dot_product_scores.argtypes = [
                    POINTER(c_double), POINTER(c_double), c_int, c_int, POINTER(c_double)
                ]
                self.mylib.py_batch_dot_product_scores.restype = None
                self.mylib.py_batch_cosine_scores.argtypes = [
                    POINTER(c_double), POINTER(c_double), c_int, c_int, POINTER(c_double)
                ]
                self.mylib.py_batch_cosine_scores.restype = None
                self.mylib.py_batch_euclidean_scores.argtypes = [
                    POINTER(c_double), POINTER(c_double), c_int, c_int, POINTER(c_double)
                ]
                self.mylib.py_batch_euclidean_scores.restype = None
                self.mylib.py_batch_topk_scores.argtypes = [
                    POINTER(c_double), POINTER(c_double), c_int, c_int, c_int, c_int, POINTER(c_int), POINTER(c_double)
                ]
                self.mylib.py_batch_topk_scores.restype = c_int
                self.mylib.py_batch_topk_scores_f32.argtypes = [
                    POINTER(c_float), POINTER(c_float), c_int, c_int, c_int, c_int, POINTER(c_int), POINTER(c_double)
                ]
                self.mylib.py_batch_topk_scores_f32.restype = c_int
                self.mylib.py_lsh_signatures_f32.argtypes = [
                    POINTER(c_float), POINTER(c_float), c_int, c_int, POINTER(c_ubyte)
                ]
                self.mylib.py_lsh_signatures_f32.restype = None
                break
            except OSError:
                self.mylib = None

    def _initialize_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                key VARCHAR PRIMARY KEY,
                vector BLOB,
                dimensions INTEGER,
                partition_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_key ON vectors(key)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_partition ON vectors(partition_id)")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                key VARCHAR PRIMARY KEY,
                path VARCHAR NOT NULL,
                content TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                metadata JSON,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_path ON document_chunks(path)")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS indexed_paths (
                path VARCHAR PRIMARY KEY,
                content_hash VARCHAR NOT NULL,
                chunk_size_lines INTEGER NOT NULL,
                overlap_lines INTEGER NOT NULL,
                file_size_bytes BIGINT NOT NULL,
                modified_ns BIGINT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunk_symbols (
                key VARCHAR NOT NULL,
                path VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                symbol_lower VARCHAR NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key, symbol_lower)
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_symbols_symbol_lower ON chunk_symbols(symbol_lower)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_symbols_path ON chunk_symbols(path)")

    def _rebuild_lsh_index(self):
        self.lsh_index = LSHIndex()
        self.lsh_index.set_native_signatures(self._hash_vector_native_f32)
        rows = self.conn.execute("""
            SELECT key, vector, dimensions
            FROM vectors
        """).fetchall()

        for key, vector_data, dimensions in rows:
            vector = self._deserialize_vector(vector_data, dimensions)
            self.lsh_index.insert(key, vector)

    def reset_database(self):
        self.conn.execute("DROP TABLE IF EXISTS vectors")
        self.conn.execute("DROP TABLE IF EXISTS document_chunks")
        self.conn.execute("DROP TABLE IF EXISTS chunk_symbols")
        self.conn.execute("""
            CREATE TABLE vectors (
                key VARCHAR PRIMARY KEY,
                vector BLOB,
                dimensions INTEGER,
                partition_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX idx_vectors_key ON vectors(key)")
        self.conn.execute("CREATE INDEX idx_vectors_partition ON vectors(partition_id)")
        self.conn.execute("""
            CREATE TABLE document_chunks (
                key VARCHAR PRIMARY KEY,
                path VARCHAR NOT NULL,
                content TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                metadata JSON,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX idx_document_chunks_path ON document_chunks(path)")
        self.conn.execute("""
            CREATE TABLE indexed_paths (
                path VARCHAR PRIMARY KEY,
                content_hash VARCHAR NOT NULL,
                chunk_size_lines INTEGER NOT NULL,
                overlap_lines INTEGER NOT NULL,
                file_size_bytes BIGINT NOT NULL,
                modified_ns BIGINT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE chunk_symbols (
                key VARCHAR NOT NULL,
                path VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                symbol_lower VARCHAR NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key, symbol_lower)
            )
        """)
        self.conn.execute("CREATE INDEX idx_chunk_symbols_symbol_lower ON chunk_symbols(symbol_lower)")
        self.conn.execute("CREATE INDEX idx_chunk_symbols_path ON chunk_symbols(path)")
        self.clear_cache()
        self.lsh_index = LSHIndex()
        self.lsh_index.set_native_signatures(self._hash_vector_native_f32)
        self._invalidate_partition_batch()

    def _serialize_vector(self, vector: List[float]) -> bytes:
        return np.array(vector, dtype=np.float64).tobytes()

    def _deserialize_vector(self, data: bytes, dimensions: int) -> List[float]:
        return list(np.frombuffer(data, dtype=np.float64))

    def _tokenize_text(self, text: str) -> List[str]:
        return re.findall(r"[A-Za-z_][A-Za-z0-9_./:-]*", text.lower())

    def _extract_path_targets(self, text: str) -> List[str]:
        raw_targets = re.findall(r"(?:[A-Za-z0-9_\-./]+(?:\.[A-Za-z0-9_]+)+)", text)
        normalized = []
        for target in raw_targets:
            candidate = target.strip().lower()
            if "/" in candidate:
                candidate = candidate.split("/workspace/projects/vector-db/", 1)[-1]
            normalized.append(candidate)
        return normalized

    def _extract_identifier_targets(self, text: str) -> List[str]:
        tokens = self._tokenize_text(text)
        return [
            token for token in tokens
            if ("_" in token or "." in token) and len(token) >= 4
        ]

    def _embed_text_hash(self, text: str) -> List[float]:
        vector = np.zeros(self.embedding_dimension, dtype=np.float64)
        tokens = self._tokenize_text(text)
        if not tokens:
            return vector.tolist()

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "little") % self.embedding_dimension
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            weight = 1.0 + (len(token) / 32.0)
            vector[index] += sign * weight

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector.tolist()

    def _embed_text_sentence_transformers(self, text: str) -> List[float]:
        embedding = self._sentence_transformer.encode(text, normalize_embeddings=True)
        return np.asarray(embedding, dtype=np.float64).tolist()

    def _embed_text_fastembed(self, text: str) -> List[float]:
        embedding = next(self._fastembed_model.embed([text]))
        return np.asarray(embedding, dtype=np.float64).tolist()

    def _embed_text_openai(self, text: str) -> List[float]:
        from openai import OpenAI

        client = OpenAI()
        model_name = self.embedding_model or "text-embedding-3-small"
        response = client.embeddings.create(model=model_name, input=text)
        return list(response.data[0].embedding)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._embedding_backend == "fastembed":
            embeddings = self._fastembed_model.embed(texts)
            return [np.asarray(embedding, dtype=np.float64).tolist() for embedding in embeddings]
        if self._embedding_backend == "sentence_transformers":
            embeddings = self._sentence_transformer.encode(texts, normalize_embeddings=True)
            return [np.asarray(embedding, dtype=np.float64).tolist() for embedding in embeddings]
        if self._embedding_backend == "openai":
            from openai import OpenAI

            client = OpenAI()
            model_name = self.embedding_model or "text-embedding-3-small"
            response = client.embeddings.create(model=model_name, input=texts)
            return [list(item.embedding) for item in response.data]
        return [self._embed_text_hash(text) for text in texts]

    def embed_text(self, text: str) -> List[float]:
        if self._embedding_backend == "fastembed":
            return self._embed_text_fastembed(text)
        if self._embedding_backend == "sentence_transformers":
            return self._embed_text_sentence_transformers(text)
        if self._embedding_backend == "openai":
            return self._embed_text_openai(text)
        return self._embed_text_hash(text)

    def _extract_symbols(self, text: str) -> List[str]:
        symbols = []
        patterns = [
            r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\basync\s+def\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\binterface\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\benum\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\btype\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
            r"\bnamespace\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bstruct\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bexport\s+(?:default\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bexport\s+async\s+function\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bconst\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\blet\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bvar\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\b(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>",
            r"\b(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s+)?function\b",
            r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\([^()\n]*\)\s*(?::\s*[A-Za-z_][A-Za-z0-9_<>,\[\]\s|?.:]*)?\s*\{",
            r"\bself\.([A-Za-z_][A-Za-z0-9_]*)\s*=",
            r"^\s*(?:template\s*<[^>]+>\s*)?(?:(?:inline|virtual|constexpr|static|extern)\s+)*(?:[\w:&*<>\[\],~]+\s+)+([A-Za-z_~][A-Za-z0-9_:~]*)\s*\([^;{}]*\)\s*(?:const\b)?\s*(?:noexcept\b)?\s*(?:\{|$)",
        ]
        for pattern in patterns:
            symbols.extend(re.findall(pattern, text, flags=re.MULTILINE))
        return symbols

    def _build_chunk_symbols(
        self,
        key: str,
        path: str,
        content: str,
        start_line: int,
        end_line: int,
    ) -> List[ChunkSymbol]:
        seen: Set[str] = set()
        records: List[ChunkSymbol] = []
        for symbol in self._extract_symbols(content):
            symbol_lower = symbol.lower()
            if symbol_lower in seen:
                continue
            seen.add(symbol_lower)
            records.append(
                ChunkSymbol(
                    key=key,
                    path=path,
                    symbol=symbol,
                    symbol_lower=symbol_lower,
                    start_line=start_line,
                    end_line=end_line,
                )
            )
        return records

    def _replace_chunk_symbols(self, symbols: List[ChunkSymbol]) -> None:
        if not symbols:
            return
        rows = [
            (
                item.key,
                item.path,
                item.symbol,
                item.symbol_lower,
                item.start_line,
                item.end_line,
            )
            for item in symbols
        ]
        self.conn.executemany("""
            INSERT OR REPLACE INTO chunk_symbols (
                key, path, symbol, symbol_lower, start_line, end_line, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, rows)

    def _match_bonus(self, query_tokens: List[str], chunk: DocumentChunk) -> float:
        if not query_tokens:
            return 0.0

        path_lower = chunk.path.lower()
        filename_lower = Path(chunk.path).name.lower()
        content_lower = chunk.content.lower()
        symbols = {symbol.lower() for symbol in self._extract_symbols(chunk.content)}
        explicit_paths = self._extract_path_targets(" ".join(query_tokens))
        identifier_targets = self._extract_identifier_targets(" ".join(query_tokens))

        bonus = 0.0
        if explicit_paths:
            for explicit_path in explicit_paths:
                if explicit_path == path_lower or explicit_path.endswith(path_lower):
                    bonus += 2.5
                elif explicit_path in path_lower:
                    bonus += 1.5

        for token in query_tokens:
            if token in filename_lower:
                bonus += 0.35
            if token in path_lower:
                bonus += 0.25
            if token in symbols:
                bonus += 0.6
            elif re.search(rf"\b{re.escape(token)}\b", content_lower):
                bonus += 0.2

        for identifier in identifier_targets:
            if identifier in symbols:
                bonus += 1.0
            elif re.search(rf"\b{re.escape(identifier)}\b", content_lower):
                bonus += 0.8
        return bonus

    def _rerank_document_results(self, query: str, results: List[Dict[str, object]]) -> List[Dict[str, object]]:
        query_tokens = self._tokenize_text(query)
        reranked = []
        for result in results:
            chunk = DocumentChunk(
                key=result["key"],
                path=result["path"],
                content=result["content"],
                start_line=result["start_line"],
                end_line=result["end_line"],
                metadata=result["metadata"],
            )
            base_score = float(result["similarity"])
            rerank_bonus = self._match_bonus(query_tokens, chunk)
            result["rerank_score"] = base_score + rerank_bonus
            reranked.append(result)

        reranked.sort(key=lambda item: item["rerank_score"], reverse=True)
        return reranked

    def chunk_text(self, content: str, chunk_size_lines: int = 40, overlap_lines: int = 10) -> List[Tuple[str, int, int]]:
        lines = content.splitlines()
        if not lines:
            return []

        chunks = []
        step = max(1, chunk_size_lines - overlap_lines)
        for start_idx in range(0, len(lines), step):
            end_idx = min(len(lines), start_idx + chunk_size_lines)
            chunk = "\n".join(lines[start_idx:end_idx]).strip()
            if chunk:
                chunks.append((chunk, start_idx + 1, end_idx))
            if end_idx >= len(lines):
                break
        return chunks

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

    def _invalidate_partition_batch(
        self,
        partition_id: Optional[int] = None,
        dimensions: Optional[int] = None,
    ):
        with self._partition_batch_lock:
            if partition_id is None and dimensions is None:
                self._partition_batches.clear()
                return

            keys_to_delete = []
            for cache_key in self._partition_batches:
                cache_partition_id, cache_dimensions = cache_key
                if partition_id is not None and cache_partition_id != partition_id:
                    continue
                if dimensions is not None and cache_dimensions != dimensions:
                    continue
                keys_to_delete.append(cache_key)

            for cache_key in keys_to_delete:
                self._partition_batches.pop(cache_key, None)

    def _set_cached_vector(self, key: str, vector: List[float]):
        with self._cache_lock:
            vector_size = self._monitor_cache_size(vector)
            if key in self._cache:
                self._current_cache_size -= self._monitor_cache_size(self._cache[key])
            self._cache[key] = vector
            self._current_cache_size += vector_size
            if self._current_cache_size > self.max_cache_size:
                self._evict_cache()

    def _normalize_matrix_rows(self, matrix: np.ndarray) -> np.ndarray:
        normalized = np.array(matrix, dtype=np.float64, copy=True, order="C")
        norms = np.linalg.norm(normalized, axis=1)
        non_zero = norms != 0
        normalized[non_zero] /= norms[non_zero, np.newaxis]
        normalized[~non_zero] = 0.0
        return normalized

    def _normalize_matrix_rows_f32(self, matrix: np.ndarray) -> np.ndarray:
        normalized = np.array(matrix, dtype=np.float32, copy=True, order="C")
        norms = np.linalg.norm(normalized, axis=1)
        non_zero = norms != 0
        normalized[non_zero] /= norms[non_zero, np.newaxis]
        normalized[~non_zero] = 0.0
        return normalized

    def _hash_vector_native_f32(self, vector: List[float], projections: np.ndarray) -> List[int]:
        if self.mylib is None:
            vector_array = np.asarray(vector, dtype=np.float64)
            norm = np.linalg.norm(vector_array)
            if norm == 0:
                return [0 for _ in range(projections.shape[0])]
            normalized = vector_array / norm
            return (np.asarray(projections, dtype=np.float64) @ normalized > 0).astype(int).tolist()

        vector_np = np.ascontiguousarray(np.asarray(vector, dtype=np.float32))
        projections_np = np.ascontiguousarray(projections, dtype=np.float32)
        output = np.empty(projections_np.shape[0], dtype=np.uint8)
        self.mylib.py_lsh_signatures_f32(
            vector_np.ctypes.data_as(POINTER(c_float)),
            projections_np.ctypes.data_as(POINTER(c_float)),
            projections_np.shape[0],
            projections_np.shape[1],
            output.ctypes.data_as(POINTER(c_ubyte)),
        )
        return output.astype(np.int32).tolist()

    def _build_partition_batch(self, rows: List[Tuple[str, bytes, int]]) -> PartitionBatch:
        if not rows:
            empty64 = np.empty((0, 0), dtype=np.float64)
            empty32 = np.empty((0, 0), dtype=np.float32)
            return PartitionBatch(keys=[], matrix=empty64, dimensions=0, matrix_f32=empty32)

        keys: List[str] = []
        vectors: List[List[float]] = []
        dimensions = rows[0][2]
        for key, vector_data, dimensions in rows:
            vector = self._get_cached_vector(key)
            if vector is None:
                vector = self._deserialize_vector(vector_data, dimensions)
                self._set_cached_vector(key, vector)
            keys.append(key)
            vectors.append(vector)

        matrix = np.ascontiguousarray(np.asarray(vectors, dtype=np.float64))
        matrix_f32 = np.ascontiguousarray(matrix.astype(np.float32))
        normalized_matrix = None
        normalized_matrix_f32 = None
        if self.similarity_metric == "cosine":
            normalized_matrix = self._normalize_matrix_rows(matrix)
            normalized_matrix_f32 = self._normalize_matrix_rows_f32(matrix_f32)

        return PartitionBatch(
            keys=keys,
            matrix=matrix,
            dimensions=dimensions,
            normalized_matrix=normalized_matrix,
            matrix_f32=matrix_f32,
            normalized_matrix_f32=normalized_matrix_f32,
        )

    def _get_partition_batch(self, partition_id: int, dimensions: int) -> PartitionBatch:
        cache_key = (partition_id, dimensions)
        with self._partition_batch_lock:
            cached_batch = self._partition_batches.get(cache_key)
        if cached_batch is not None:
            return cached_batch

        rows = self.conn.execute("""
            SELECT key, vector, dimensions
            FROM vectors
            WHERE partition_id = ?
              AND dimensions = ?
        """, [partition_id, dimensions]).fetchall()
        batch = self._build_partition_batch(rows)
        with self._partition_batch_lock:
            self._partition_batches[cache_key] = batch
        return batch

    def get_metrics(self) -> PerformanceMetrics:
        process = psutil.Process()
        self.metrics.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        self.metrics.cache_size = self._current_cache_size
        totals = self.conn.execute("""
            SELECT COUNT(*), COALESCE(SUM(dimensions), 0)
            FROM vectors
        """).fetchone()
        self.metrics.total_vectors = totals[0]
        self.metrics.total_dimensions = totals[1]
        return self.metrics

    def get_runtime_info(self) -> Dict[str, object]:
        return {
            "embedding_backend": self._embedding_backend,
            "embedding_model": self.embedding_model,
            "use_asm": self.use_asm,
            "asm_loaded": self.mylib is not None,
            "similarity_metric": self.similarity_metric,
        }

    def _calculate_similarity(self, v1: List[float], v2: List[float]) -> float:
        if self.mylib is not None:
            # Use optimized C library
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
                squared_distance = self.mylib.py_squared_distance(v1_array, v2_array, len(v1))
                return -np.sqrt(squared_distance)
            
            else:  # dot_product
                return self.mylib.py_dot_product(v1_array, v2_array, len(v1))
        else:
            # Pure Python fallback
            v1_np = np.array(v1)
            v2_np = np.array(v2)
            
            if self.similarity_metric == "cosine":
                dot_product = np.dot(v1_np, v2_np)
                norm_v1 = np.linalg.norm(v1_np)
                norm_v2 = np.linalg.norm(v2_np)
                
                if norm_v1 == 0 or norm_v2 == 0:
                    return 0.0
                return dot_product / (norm_v1 * norm_v2)
            
            elif self.similarity_metric == "euclidean":
                diff = v1_np - v2_np
                return -np.sqrt(np.sum(diff * diff))
            
            else:  # dot_product
                return np.dot(v1_np, v2_np)

    def _score_matrix_numpy(self, query_vector: List[float], matrix: np.ndarray) -> np.ndarray:
        query_np = np.asarray(query_vector, dtype=np.float64)

        if self.similarity_metric == "cosine":
            query_norm = np.linalg.norm(query_np)
            matrix_norms = np.linalg.norm(matrix, axis=1)
            dots = matrix @ query_np
            denom = matrix_norms * query_norm
            with np.errstate(divide="ignore", invalid="ignore"):
                scores = np.divide(dots, denom, out=np.zeros_like(dots), where=denom != 0)
            return scores

        if self.similarity_metric == "euclidean":
            diff = matrix - query_np
            return -np.sqrt(np.sum(diff * diff, axis=1))

        return matrix @ query_np

    def _score_matrix_native(
        self,
        query_vector: List[float],
        matrix: np.ndarray,
        metric_override: Optional[Literal["cosine", "euclidean", "dot_product"]] = None,
    ) -> np.ndarray:
        query_np = np.ascontiguousarray(np.asarray(query_vector, dtype=np.float64))
        matrix_np = np.ascontiguousarray(matrix, dtype=np.float64)
        output = np.empty(matrix_np.shape[0], dtype=np.float64)

        query_ptr = query_np.ctypes.data_as(POINTER(c_double))
        matrix_ptr = matrix_np.ctypes.data_as(POINTER(c_double))
        output_ptr = output.ctypes.data_as(POINTER(c_double))
        num_vectors, dimensions = matrix_np.shape
        metric = metric_override or self.similarity_metric

        if metric == "cosine":
            self.mylib.py_batch_cosine_scores(query_ptr, matrix_ptr, num_vectors, dimensions, output_ptr)
        elif metric == "euclidean":
            self.mylib.py_batch_euclidean_scores(query_ptr, matrix_ptr, num_vectors, dimensions, output_ptr)
        else:
            self.mylib.py_batch_dot_product_scores(query_ptr, matrix_ptr, num_vectors, dimensions, output_ptr)

        return output

    def _metric_code(
        self,
        metric_override: Optional[Literal["cosine", "euclidean", "dot_product"]] = None,
    ) -> int:
        metric = metric_override or self.similarity_metric
        if metric == "cosine":
            return 0
        if metric == "euclidean":
            return 1
        return 2

    def _select_topk_scores(
        self,
        keys: List[str],
        scores: np.ndarray,
        k: int,
    ) -> List[Tuple[str, float]]:
        if k <= 0 or not keys:
            return []

        limit = min(k, len(keys))
        if limit == len(keys):
            order = np.argsort(scores)[::-1]
        else:
            candidate_indices = np.argpartition(scores, -limit)[-limit:]
            order = candidate_indices[np.argsort(scores[candidate_indices])[::-1]]
        return [(keys[int(idx)], float(scores[int(idx)])) for idx in order]

    def _score_topk_native(
        self,
        query_vector: List[float],
        matrix: np.ndarray,
        keys: List[str],
        k: int,
        metric_override: Optional[Literal["cosine", "euclidean", "dot_product"]] = None,
    ) -> List[Tuple[str, float]]:
        if k <= 0 or matrix.size == 0 or not keys:
            return []

        query_np = np.ascontiguousarray(np.asarray(query_vector, dtype=np.float64))
        matrix_np = np.ascontiguousarray(matrix, dtype=np.float64)
        limit = min(k, matrix_np.shape[0])
        indices = np.full(limit, -1, dtype=np.int32)
        scores = np.full(limit, -np.inf, dtype=np.float64)

        query_ptr = query_np.ctypes.data_as(POINTER(c_double))
        matrix_ptr = matrix_np.ctypes.data_as(POINTER(c_double))
        indices_ptr = indices.ctypes.data_as(POINTER(c_int))
        scores_ptr = scores.ctypes.data_as(POINTER(c_double))
        count = self.mylib.py_batch_topk_scores(
            query_ptr,
            matrix_ptr,
            matrix_np.shape[0],
            matrix_np.shape[1],
            self._metric_code(metric_override),
            limit,
            indices_ptr,
            scores_ptr,
        )
        return [
            (keys[int(indices[i])], float(scores[i]))
            for i in range(count)
            if indices[i] >= 0
        ]

    def _score_topk_native_f32(
        self,
        query_vector: List[float],
        matrix: np.ndarray,
        keys: List[str],
        k: int,
        metric_override: Optional[Literal["cosine", "euclidean", "dot_product"]] = None,
    ) -> List[Tuple[str, float]]:
        if k <= 0 or matrix.size == 0 or not keys:
            return []

        query_np = np.ascontiguousarray(np.asarray(query_vector, dtype=np.float32))
        matrix_np = np.ascontiguousarray(matrix, dtype=np.float32)
        limit = min(k, matrix_np.shape[0])
        indices = np.full(limit, -1, dtype=np.int32)
        scores = np.full(limit, -np.inf, dtype=np.float64)

        count = self.mylib.py_batch_topk_scores_f32(
            query_np.ctypes.data_as(POINTER(c_float)),
            matrix_np.ctypes.data_as(POINTER(c_float)),
            matrix_np.shape[0],
            matrix_np.shape[1],
            self._metric_code(metric_override),
            limit,
            indices.ctypes.data_as(POINTER(c_int)),
            scores.ctypes.data_as(POINTER(c_double)),
        )
        return [
            (keys[int(indices[i])], float(scores[i]))
            for i in range(count)
            if indices[i] >= 0
        ]

    def _score_partition_batch(self, batch: PartitionBatch, query_vector: List[float]) -> List[Tuple[str, float]]:
        if batch.matrix.size == 0:
            return []

        if self.similarity_metric == "cosine" and batch.normalized_matrix is not None:
            query_np = np.asarray(query_vector, dtype=np.float64)
            query_norm = np.linalg.norm(query_np)
            if query_norm == 0:
                scores = np.zeros(len(batch.keys), dtype=np.float64)
            else:
                normalized_query = np.ascontiguousarray(query_np / query_norm, dtype=np.float64)
                if self.mylib is not None:
                    scores = self._score_matrix_native(
                        normalized_query.tolist(),
                        batch.normalized_matrix,
                        metric_override="dot_product",
                    )
                else:
                    scores = batch.normalized_matrix @ normalized_query
        else:
            if self.mylib is not None:
                scores = self._score_matrix_native(query_vector, batch.matrix)
            else:
                scores = self._score_matrix_numpy(query_vector, batch.matrix)

        return list(zip(batch.keys, scores.tolist()))

    def _topk_partition_batch(
        self,
        batch: PartitionBatch,
        query_vector: List[float],
        k: int,
    ) -> List[Tuple[str, float]]:
        if batch.matrix.size == 0 or k <= 0:
            return []
        if batch.dimensions and batch.dimensions != len(query_vector):
            return []

        if self.similarity_metric == "cosine" and batch.normalized_matrix is not None:
            query_np = np.asarray(query_vector, dtype=np.float64)
            query_norm = np.linalg.norm(query_np)
            if query_norm == 0:
                return [(key, 0.0) for key in batch.keys[: min(k, len(batch.keys))]]
            if self.mylib is not None and batch.normalized_matrix_f32 is not None:
                normalized_query_f32 = np.ascontiguousarray(query_np / query_norm, dtype=np.float32)
                return self._score_topk_native_f32(
                    normalized_query_f32.tolist(),
                    batch.normalized_matrix_f32,
                    batch.keys,
                    k,
                    metric_override="dot_product",
                )
            normalized_query = np.ascontiguousarray(query_np / query_norm, dtype=np.float64)
            if self.mylib is not None:
                return self._score_topk_native(
                    normalized_query.tolist(),
                    batch.normalized_matrix,
                    batch.keys,
                    k,
                    metric_override="dot_product",
                )
            scores = batch.normalized_matrix @ normalized_query
            return self._select_topk_scores(batch.keys, scores, k)

        if self.mylib is not None and batch.matrix_f32 is not None:
            return self._score_topk_native_f32(query_vector, batch.matrix_f32, batch.keys, k)

        if self.mylib is not None:
            return self._score_topk_native(query_vector, batch.matrix, batch.keys, k)

        scores = self._score_matrix_numpy(query_vector, batch.matrix)
        return self._select_topk_scores(batch.keys, scores, k)

    def _process_partition_batch(self, partition_vectors: List[Tuple[str, bytes, int]], query_vector: List[float]) -> List[Tuple[str, float]]:
        if not partition_vectors:
            return []
        batch = self._build_partition_batch(partition_vectors)
        if batch.dimensions and batch.dimensions != len(query_vector):
            return []
        return self._score_partition_batch(batch, query_vector)

    def insert(self, key: str, vector: List[float], partition_id: Optional[int] = None) -> None:
        if partition_id is None:
            partition_id = hash(key) % (self.chunk_size)
        
        vector_data = self._serialize_vector(vector)
        self.conn.execute("""
            INSERT OR REPLACE INTO vectors (key, vector, dimensions, partition_id)
            VALUES (?, ?, ?, ?)
        """, [key, vector_data, len(vector), partition_id])
        self._set_cached_vector(key, vector)
        self._invalidate_partition_batch(partition_id, len(vector))
        self.lsh_index.insert(key, vector)

    def upsert_document_chunk(
        self,
        key: str,
        content: str,
        path: str,
        start_line: int,
        end_line: int,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        vector = self.embed_text(content)
        self.insert(key, vector)
        self.conn.execute("""
            INSERT OR REPLACE INTO document_chunks (key, path, content, start_line, end_line, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            key,
            path,
            content,
            start_line,
            end_line,
            json.dumps(metadata or {}),
        ])
        self.conn.execute("DELETE FROM chunk_symbols WHERE key = ?", [key])
        self._replace_chunk_symbols(
            self._build_chunk_symbols(key, path, content, start_line, end_line)
        )

    def _record_indexed_path(
        self,
        path: str,
        content_hash: str,
        chunk_size_lines: int,
        overlap_lines: int,
        file_size_bytes: int,
        modified_ns: int,
    ) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO indexed_paths (
                path, content_hash, chunk_size_lines, overlap_lines, file_size_bytes, modified_ns, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            path,
            content_hash,
            chunk_size_lines,
            overlap_lines,
            file_size_bytes,
            modified_ns,
        ])

    def _indexed_path_is_fresh(
        self,
        path: str,
        content_hash: str,
        chunk_size_lines: int,
        overlap_lines: int,
        file_size_bytes: int,
        modified_ns: int,
    ) -> bool:
        row = self.conn.execute("""
            SELECT content_hash, chunk_size_lines, overlap_lines, file_size_bytes, modified_ns
            FROM indexed_paths
            WHERE path = ?
        """, [path]).fetchone()
        if row is None:
            return False
        return row == (
            content_hash,
            chunk_size_lines,
            overlap_lines,
            file_size_bytes,
            modified_ns,
        )

    def get_document_chunk(self, key: str) -> Optional[DocumentChunk]:
        row = self.conn.execute("""
            SELECT key, path, content, start_line, end_line, metadata
            FROM document_chunks
            WHERE key = ?
        """, [key]).fetchone()
        if row is None:
            return None

        metadata = json.loads(row[5]) if row[5] else {}
        return DocumentChunk(
            key=row[0],
            path=row[1],
            content=row[2],
            start_line=row[3],
            end_line=row[4],
            metadata=metadata,
        )

    def delete_chunks_by_path(self, path: str) -> int:
        rows = self.conn.execute("""
            SELECT dc.key, v.partition_id
            FROM document_chunks dc
            LEFT JOIN vectors v ON v.key = dc.key
            WHERE dc.path = ?
        """, [path]).fetchall()
        if not rows:
            self.conn.execute("DELETE FROM indexed_paths WHERE path = ?", [path])
            return 0

        keys = [row[0] for row in rows]
        partition_ids = {row[1] for row in rows if row[1] is not None}

        placeholders = ",".join(["?" for _ in keys])
        with self._cache_lock:
            for key in keys:
                cached_vector = self._cache.pop(key, None)
                if cached_vector is not None:
                    self._current_cache_size -= self._monitor_cache_size(cached_vector)

        self.conn.execute(f"DELETE FROM vectors WHERE key IN ({placeholders})", keys)
        self.conn.execute("DELETE FROM document_chunks WHERE path = ?", [path])
        self.conn.execute("DELETE FROM chunk_symbols WHERE path = ?", [path])
        self.conn.execute("DELETE FROM indexed_paths WHERE path = ?", [path])

        for partition_id in partition_ids:
            self._invalidate_partition_batch(partition_id)
        self._rebuild_lsh_index()
        return len(keys)

    def delete_chunks_by_prefix(self, prefix: str) -> int:
        normalized_prefix = prefix.strip("/").replace("\\", "/")
        if not normalized_prefix:
            return 0

        rows = self.conn.execute("""
            SELECT DISTINCT path
            FROM document_chunks
            WHERE path = ? OR path LIKE ?
        """, [normalized_prefix, f"{normalized_prefix}/%"]).fetchall()
        deleted = 0
        for (path,) in rows:
            deleted += self.delete_chunks_by_path(path)
        return deleted

    def search_document_chunks(
        self,
        query: str,
        k: int = 5,
        method: Literal["exact", "approximate", "lsh"] = "exact",
    ) -> List[Dict[str, object]]:
        query_vector = self.embed_text(query)
        chunk_count = self.conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
        if chunk_count == 0:
            return []

        explicit_paths = set(self._extract_path_targets(query))
        if explicit_paths:
            placeholders = ",".join(["?" for _ in explicit_paths])
            rows = self.conn.execute(f"""
                SELECT key, path, content, start_line, end_line, metadata
                FROM document_chunks
                WHERE lower(path) IN ({placeholders})
                   OR {" OR ".join(["lower(path) LIKE ?" for _ in explicit_paths])}
            """, [
                *explicit_paths,
                *[f"%{path}%" for path in explicit_paths],
            ]).fetchall()
            direct_matches = []
            for row in rows:
                metadata = json.loads(row[5]) if row[5] else {}
                direct_matches.append({
                    "key": row[0],
                    "path": row[1],
                    "content": row[2],
                    "start_line": row[3],
                    "end_line": row[4],
                    "metadata": metadata,
                    "similarity": 0.0,
                })
            if direct_matches:
                return self._rerank_document_results(query, direct_matches)[:k]

        raw_results = self.search(query_vector, max(k * 8, k), method)
        results: List[Dict[str, object]] = []
        for key, similarity in raw_results:
            chunk = self.get_document_chunk(key)
            if chunk is None:
                continue
            results.append({
                "key": chunk.key,
                "path": chunk.path,
                "content": chunk.content,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "metadata": chunk.metadata,
                "similarity": float(similarity),
            })
            if len(results) >= max(k * 6, k):
                break
        return self._rerank_document_results(query, results)[:k]

    def ask_repository_context(
        self,
        question: str,
        k: int = 5,
        method: Literal["exact", "approximate", "lsh"] = "exact",
    ) -> Dict[str, object]:
        matches = self.search_document_chunks(question, k=k, method=method)
        context_blocks = [
            f"{match['path']}:{match['start_line']}-{match['end_line']}\n{match['content']}"
            for match in matches
        ]
        return {
            "question": question,
            "matches": matches,
            "context": "\n\n---\n\n".join(context_blocks),
        }

    def _normalize_root_and_target(self, root_path: str, target_path: Optional[str] = None) -> Tuple[Path, Optional[Path]]:
        root = Path(root_path).resolve()
        target = None
        if target_path is not None:
            raw_target = Path(target_path)
            target = raw_target if raw_target.is_absolute() else root / raw_target
            target = target.resolve()
        return root, target

    def _default_allowed_extensions(self) -> Set[str]:
        return {
            ".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ts", ".tsx",
            ".js", ".jsx", ".rs", ".go", ".java", ".c", ".h", ".cpp", ".hpp",
            ".asm", ".sh", ".lisp", ".clj", ".sql",
        }

    def _default_excluded_dirs(self) -> Set[str]:
        return {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "core"}

    def _is_excluded_relative_path(self, relative_path: str, excluded_dirs: Set[str]) -> bool:
        parts = Path(relative_path).parts
        return any(part in excluded_dirs for part in parts[:-1])

    def _index_file(self, file_path: Path, root: Path, chunk_size_lines: int, overlap_lines: int) -> Tuple[int, bool]:
        relative_path = str(file_path.relative_to(root))
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return 0, False

        stat_result = file_path.stat()
        content_hash = hashlib.blake2b(content.encode("utf-8"), digest_size=16).hexdigest()
        if self._indexed_path_is_fresh(
            relative_path,
            content_hash,
            chunk_size_lines,
            overlap_lines,
            stat_result.st_size,
            stat_result.st_mtime_ns,
        ):
            return 0, True

        self.delete_chunks_by_path(relative_path)
        chunks = self.chunk_text(content, chunk_size_lines=chunk_size_lines, overlap_lines=overlap_lines)
        if not chunks:
            self._record_indexed_path(
                relative_path,
                content_hash,
                chunk_size_lines,
                overlap_lines,
                stat_result.st_size,
                stat_result.st_mtime_ns,
            )
            return 0, False

        chunk_payloads = []
        chunk_symbols: List[ChunkSymbol] = []
        for chunk_content, start_line, end_line in chunks:
            chunk_key = f"{relative_path}:{start_line}-{end_line}"
            metadata = {
                "root": str(root),
                "filename": file_path.name,
            }
            chunk_payloads.append((chunk_key, chunk_content, start_line, end_line, metadata))
            chunk_symbols.extend(
                self._build_chunk_symbols(
                    chunk_key,
                    relative_path,
                    chunk_content,
                    start_line,
                    end_line,
                )
            )

        vectors = self.embed_texts([payload[1] for payload in chunk_payloads])
        self.batch_insert([(payload[0], vector) for payload, vector in zip(chunk_payloads, vectors)])
        self.conn.executemany("""
            INSERT OR REPLACE INTO document_chunks (key, path, content, start_line, end_line, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            (
                chunk_key,
                relative_path,
                chunk_content,
                start_line,
                end_line,
                json.dumps(metadata),
            )
            for chunk_key, chunk_content, start_line, end_line, metadata in chunk_payloads
        ])
        self._replace_chunk_symbols(chunk_symbols)
        self._record_indexed_path(
            relative_path,
            content_hash,
            chunk_size_lines,
            overlap_lines,
            stat_result.st_size,
            stat_result.st_mtime_ns,
        )
        return len(chunk_payloads), False

    def index_repository(
        self,
        root_path: str,
        include_extensions: Optional[List[str]] = None,
        chunk_size_lines: int = 40,
        overlap_lines: int = 10,
        max_file_size_bytes: int = 200_000,
    ) -> Dict[str, int]:
        root = Path(root_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Path does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {root}")

        allowed_extensions = set(include_extensions or self._default_allowed_extensions())
        excluded_dirs = self._default_excluded_dirs()

        with self._write_lock:
            for excluded_dir in excluded_dirs:
                self.delete_chunks_by_prefix(excluded_dir)

            indexed_files = 0
            indexed_chunks = 0
            skipped_files = 0
            seen_content_hashes: Dict[str, str] = {}
            for current_root, dirnames, filenames in os.walk(root):
                dirnames[:] = [dirname for dirname in dirnames if dirname not in excluded_dirs]
                for filename in filenames:
                    file_path = Path(current_root) / filename
                    relative_path = str(file_path.relative_to(root))
                    if self._is_excluded_relative_path(relative_path, excluded_dirs):
                        self.delete_chunks_by_path(relative_path)
                        skipped_files += 1
                        continue
                    if allowed_extensions and file_path.suffix.lower() not in allowed_extensions:
                        continue
                    if file_path.stat().st_size > max_file_size_bytes:
                        continue

                    try:
                        content_hash = hashlib.blake2b(file_path.read_bytes(), digest_size=16).hexdigest()
                    except OSError:
                        continue
                    existing_path = seen_content_hashes.get(content_hash)
                    if existing_path is not None:
                        self.delete_chunks_by_path(relative_path)
                        skipped_files += 1
                        continue
                    seen_content_hashes[content_hash] = relative_path

                    file_chunks, skipped = self._index_file(file_path, root, chunk_size_lines, overlap_lines)
                    if skipped:
                        skipped_files += 1
                        continue
                    indexed_chunks += file_chunks
                    indexed_files += 1

            return {"indexed_files": indexed_files, "indexed_chunks": indexed_chunks, "skipped_files": skipped_files}

    def index_workspace(self, workspace_root: str, **kwargs) -> Dict[str, int]:
        return self.index_repository(workspace_root, **kwargs)

    def refresh_path(
        self,
        root_path: str,
        target_path: str,
        include_extensions: Optional[List[str]] = None,
        chunk_size_lines: int = 40,
        overlap_lines: int = 10,
    ) -> Dict[str, int]:
        root, target = self._normalize_root_and_target(root_path, target_path)
        if target is None or not target.exists():
            raise FileNotFoundError(f"Path does not exist: {target_path}")

        allowed_extensions = set(include_extensions or self._default_allowed_extensions())
        excluded_dirs = self._default_excluded_dirs()

        with self._write_lock:
            indexed_files = 0
            indexed_chunks = 0
            skipped_files = 0
            if target.is_file():
                relative_path = str(target.relative_to(root))
                if self._is_excluded_relative_path(relative_path, excluded_dirs):
                    self.delete_chunks_by_path(relative_path)
                    return {"indexed_files": 0, "indexed_chunks": 0, "skipped_files": 1}
                if target.suffix.lower() in allowed_extensions:
                    file_chunks, skipped = self._index_file(target, root, chunk_size_lines, overlap_lines)
                    if skipped:
                        skipped_files = 1
                    else:
                        indexed_chunks = file_chunks
                        indexed_files = 1
            else:
                result = self.index_repository(
                    str(target),
                    include_extensions=list(allowed_extensions),
                    chunk_size_lines=chunk_size_lines,
                    overlap_lines=overlap_lines,
                )
                return result

            return {"indexed_files": indexed_files, "indexed_chunks": indexed_chunks, "skipped_files": skipped_files}

    def search_symbols(self, query: str, k: int = 5) -> List[Dict[str, object]]:
        query_tokens = self._tokenize_text(query)
        if not query_tokens:
            return []
        explicit_paths = self._extract_path_targets(query)
        identifier_targets = self._extract_identifier_targets(query)
        lookup_terms = {token.lower() for token in query_tokens}
        lookup_terms.update(identifier_targets)
        if not lookup_terms:
            return []

        clauses = ["symbol_lower = ?" for _ in lookup_terms]
        params: List[object] = list(lookup_terms)
        path_filter = ""
        if explicit_paths:
            path_filter = " AND (" + " OR ".join(["lower(cs.path) = ? OR lower(cs.path) LIKE ?" for _ in explicit_paths]) + ")"
            for explicit_path in explicit_paths:
                params.extend([explicit_path, f"%{explicit_path}%"])

        rows = self.conn.execute(f"""
            SELECT
                dc.key,
                dc.path,
                dc.content,
                dc.start_line,
                dc.end_line,
                dc.metadata,
                list(cs.symbol) AS matched_symbols
            FROM chunk_symbols cs
            JOIN document_chunks dc ON dc.key = cs.key
            WHERE ({' OR '.join(clauses)}) {path_filter}
            GROUP BY dc.key, dc.path, dc.content, dc.start_line, dc.end_line, dc.metadata
        """, params).fetchall()

        symbol_hits: List[Dict[str, object]] = []
        for row in rows:
            metadata = json.loads(row[5]) if row[5] else {}
            chunk = DocumentChunk(row[0], row[1], row[2], row[3], row[4], metadata)
            matched_symbols = sorted({symbol.lower() for symbol in (row[6] or [])})
            bonus = self._match_bonus(query_tokens, chunk)
            exact_bonus = sum(1.5 for symbol in matched_symbols if symbol in lookup_terms)
            symbol_hits.append({
                "key": chunk.key,
                "path": chunk.path,
                "content": chunk.content,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "metadata": chunk.metadata,
                "matched_symbols": matched_symbols,
                "rerank_score": bonus + exact_bonus + len(matched_symbols),
            })

        symbol_hits.sort(
            key=lambda item: (
                item["rerank_score"],
                len(item["matched_symbols"]),
                -item["start_line"],
            ),
            reverse=True,
        )
        return symbol_hits[:k]

    def search_docs(self, query: str, k: int = 5, method: Literal["exact", "approximate", "lsh"] = "exact") -> List[Dict[str, object]]:
        doc_extensions = {".md", ".txt", ".rst"}
        matches = self.search_document_chunks(query, k=max(k * 3, k), method=method)
        filtered = [match for match in matches if Path(match["path"]).suffix.lower() in doc_extensions]
        return filtered[:k]

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

        if self.mylib is not None:
            v1_array = (c_double * len(v1))(*v1)
            v2_array = (c_double * len(v2))(*v2)

            dot_product = self.mylib.py_dot_product(v1_array, v2_array, len(v1))
            norm_v1 = self.mylib.py_vector_norm(v1_array, len(v1))
            norm_v2 = self.mylib.py_vector_norm(v2_array, len(v2))

            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
            return dot_product / (norm_v1 * norm_v2)
        else:
            # Pure Python fallback
            v1_np = np.array(v1)
            v2_np = np.array(v2)
            
            dot_product = np.dot(v1_np, v2_np)
            norm_v1 = np.linalg.norm(v1_np)
            norm_v2 = np.linalg.norm(v2_np)

            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
            return dot_product / (norm_v1 * norm_v2)

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
            WHERE dimensions = ?
        """, [len(query_vector)]).fetchall()
        
        all_similarities = []
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            
            for (partition_id,) in all_partitions:
                partition_batch = self._get_partition_batch(partition_id, len(query_vector))
                future = executor.submit(self._topk_partition_batch, partition_batch, query_vector, k)
                futures.append(future)
            
            for future in futures:
                all_similarities.extend(future.result())

        return heapq.nlargest(k, all_similarities, key=lambda item: item[1])

    def lsh_search(self, query_vector: List[float], k: int) -> List[Tuple[str, float]]:
        # Get candidates from LSH with increased min_candidates
        min_candidates = max(k * 50, 1000)  # Ensure minimum candidates
        candidate_keys = self.lsh_index.query(query_vector, min_candidates=min_candidates)
        
        if not candidate_keys or len(candidate_keys) < k:
            # Try with more hash functions before falling back
            old_num_functions = self.lsh_index.num_hash_functions
            self.lsh_index.num_hash_functions = 40
            candidate_keys = self.lsh_index.query(query_vector, min_candidates=min_candidates)
            self.lsh_index.num_hash_functions = old_num_functions
            
            if not candidate_keys or len(candidate_keys) < k:
                return self.approximate_search(query_vector, k, self.chunk_size // 2)
        
        # Batch retrieve vectors with pagination for large candidate sets
        similarities = []
        batch_size = 1000
        
        for i in range(0, len(candidate_keys), batch_size):
            batch_keys = candidate_keys[i:i + batch_size]
            placeholders = ','.join(['?' for _ in batch_keys])
            vectors_data = self.conn.execute(f"""
                SELECT key, vector, dimensions 
                FROM vectors 
                WHERE key IN ({placeholders})
                  AND dimensions = ?
            """, [*batch_keys, len(query_vector)]).fetchall()
            
            batch = self._build_partition_batch(vectors_data)
            similarities.extend(self._topk_partition_batch(batch, query_vector, max(k * 4, k)))
            
            # Early stopping if we have enough good candidates
            similarities = heapq.nlargest(max(k * 10, k), similarities, key=lambda item: item[1])
            if len(similarities) >= k and similarities[k-1][1] > 0.5:
                break
        
        return heapq.nlargest(k, similarities, key=lambda item: item[1])

    def batch_insert(self, vectors: List[Tuple[str, List[float]]], partition_size: Optional[int] = None) -> None:
        if partition_size is None:
            partition_size = self.chunk_size

        try:
            self.conn.execute("BEGIN TRANSACTION")
            
            for i in range(0, len(vectors), 1000):  # Process in chunks of 1000
                batch = vectors[i:i + 1000]
                data = []
                affected_partitions = set()
                for j, (key, vec) in enumerate(batch):
                    partition_id = (i + j) // partition_size
                    data.append((key, self._serialize_vector(vec), len(vec), partition_id))
                    self._set_cached_vector(key, vec)
                    affected_partitions.add(partition_id)
                
                self.conn.executemany("""
                    INSERT OR REPLACE INTO vectors (key, vector, dimensions, partition_id)
                    VALUES (?, ?, ?, ?)
                """, data)
                for partition_id in affected_partitions:
                    for _, vec in batch:
                        self._invalidate_partition_batch(partition_id, len(vec))
            
            self.conn.execute("COMMIT")
            self._rebuild_lsh_index()
        except Exception as e:
            self.conn.execute("ROLLBACK")
            raise Exception(f"Batch insert failed: {str(e)}")

    def approximate_search(self, query_vector: List[float], k: int, sample_size: int) -> List[Tuple[str, float]]:
        dimensions = len(query_vector)
        total_vectors = self.conn.execute(
            "SELECT COUNT(*) FROM vectors WHERE dimensions = ?",
            [dimensions],
        ).fetchone()[0]
        if total_vectors == 0:
            return []
        
        # Adaptive sampling based on dataset size
        if total_vectors < 50000:
            sample_ratio = 0.2  # 20% for small datasets
        elif total_vectors < 100000:
            sample_ratio = 0.1  # 10% for medium datasets
        else:
            sample_ratio = 0.05  # 5% for large datasets
        
        # Improved stratified sampling with better partition coverage
        sampled_vectors = self.conn.execute("""
            WITH partitions AS (
                SELECT DISTINCT partition_id,
                       COUNT(*) OVER (PARTITION BY partition_id) as partition_size,
                       SUM(1) OVER () as total_vectors
                FROM vectors
                WHERE dimensions = ?
            ),
            ranked_vectors AS (
                SELECT v.key, v.vector, v.dimensions,
                       ROW_NUMBER() OVER (PARTITION BY v.partition_id ORDER BY RANDOM()) as rn,
                       p.partition_size
                FROM vectors v
                JOIN partitions p ON v.partition_id = p.partition_id
                WHERE v.dimensions = ?
            )
            SELECT key, vector, dimensions
            FROM ranked_vectors
            WHERE (rn <= partition_size * ? AND RANDOM() <= 0.5)  -- Stratified sampling
               OR (rn <= ? AND partition_size <= ?)  -- Include small partitions
               OR RANDOM() <= 0.05  -- Random sampling for diversity
            LIMIT ?
        """, [
            dimensions,
            dimensions,
            sample_ratio,
            k * 2,  # Take more from small partitions
            k * 4,  # Small partition threshold
            max(sample_size * 2, k * 100)  # Ensure enough samples
        ]).fetchall()
        
        batch = self._build_partition_batch(sampled_vectors)
        return self._topk_partition_batch(batch, query_vector, k)

    def delete(self, key: str) -> bool:
        with self._cache_lock:
            self._cache.pop(key, None)

        partition_row = self.conn.execute("""
            SELECT partition_id FROM vectors WHERE key = ?
        """, [key]).fetchone()

        affected = self.conn.execute("""
            DELETE FROM vectors WHERE key = ?
        """, [key]).rowcount
        if affected > 0:
            if partition_row is not None:
                self._invalidate_partition_batch(partition_row[0])
            self._rebuild_lsh_index()
        return affected > 0

    def get_all_keys(self) -> List[str]:
        return [row[0] for row in self.conn.execute("SELECT key FROM vectors").fetchall()]

    def clear_cache(self):
        with self._cache_lock:
            self._cache.clear()
            self._current_cache_size = 0
        self._invalidate_partition_batch()

    def close(self):
        self.clear_cache()
        # DuckDB автоматически сохраняет данные при закрытии
        self.conn.close()
        print(f"✅ База данных сохранена в файл: {self.db_path}")

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
        
        # Exact search first to establish ground truth
        start_time = time.time()
        exact_results = self._exact_search(query_vector, k)
        metrics.exact_time = time.time() - start_time
        
        # LSH search (do this before approximate to warm up cache)
        start_time = time.time()
        lsh_results = self.lsh_search(query_vector, k)
        metrics.lsh_time = time.time() - start_time
        lsh_recall = self.calculate_recall(exact_results, lsh_results, k)
        
        # Approximate search
        start_time = time.time()
        approx_results = self.approximate_search(query_vector, k, self.chunk_size // 2)  # Increased sample size
        metrics.approx_time = time.time() - start_time
        approx_recall = self.calculate_recall(exact_results, approx_results, k)
        
        # Use the best results
        if lsh_recall >= approx_recall:
            metrics.recall_at_k = lsh_recall
        else:
            metrics.recall_at_k = approx_recall
        
        # Memory and cache metrics
        metrics.memory_used = process.memory_info().rss / 1024 / 1024
        total_ops = self.metrics.cache_hits + self.metrics.cache_misses
        metrics.cache_hit_ratio = self.metrics.cache_hits / total_ops if total_ops > 0 else 0
        
        return metrics 
