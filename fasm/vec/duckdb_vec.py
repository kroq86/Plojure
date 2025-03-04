import duckdb
import numpy as np
from typing import List, Tuple
import ctypes
from ctypes import CDLL, POINTER, c_double, c_int
import json

class DuckDBVectorDatabase:
    def __init__(self, db_path: str = ':memory:'):
        self.conn = duckdb.connect(db_path)
        self.load_library()
        self._initialize_db()

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_key ON vectors(key)")

    def _serialize_vector(self, vector: List[float]) -> bytes:
        return np.array(vector, dtype=np.float64).tobytes()

    def _deserialize_vector(self, data: bytes, dimensions: int) -> List[float]:
        return list(np.frombuffer(data, dtype=np.float64))

    def insert(self, key: str, vector: List[float]) -> None:
        vector_data = self._serialize_vector(vector)
        self.conn.execute("""
            INSERT OR REPLACE INTO vectors (key, vector, dimensions)
            VALUES (?, ?, ?)
        """, [key, vector_data, len(vector)])

    def retrieve(self, key: str) -> List[float]:
        result = self.conn.execute("""
            SELECT vector, dimensions FROM vectors WHERE key = ?
        """, [key]).fetchone()
        
        if result is None:
            return None
        
        vector_data, dimensions = result
        return self._deserialize_vector(vector_data, dimensions)

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

    def search(self, query_vector: List[float], k: int) -> List[Tuple[str, float]]:
        all_vectors = self.conn.execute("""
            SELECT key, vector, dimensions FROM vectors
        """).fetchall()
        
        similarities = []
        for key, vector_data, dimensions in all_vectors:
            vector = self._deserialize_vector(vector_data, dimensions)
            similarity = self.cosine_similarity(query_vector, vector)
            similarities.append((key, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

    def batch_insert(self, vectors: List[Tuple[str, List[float]]]) -> None:
        data = [(key, self._serialize_vector(vec), len(vec)) 
                for key, vec in vectors]
        
        self.conn.executemany("""
            INSERT OR REPLACE INTO vectors (key, vector, dimensions)
            VALUES (?, ?, ?)
        """, data)

    def delete(self, key: str) -> bool:
        affected = self.conn.execute("""
            DELETE FROM vectors WHERE key = ?
        """, [key]).rowcount
        return affected > 0

    def get_all_keys(self) -> List[str]:
        return [row[0] for row in self.conn.execute("SELECT key FROM vectors").fetchall()]

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 