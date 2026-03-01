from ctypes import CDLL, POINTER, c_double, c_int
from typing import Tuple, List
from pathlib import Path
import math

class VectorDatabase:
    def __init__(self):
        self.vectors = {}
        self.load_library()

    def load_library(self):
        self.mylib = None
        library_paths = [
            Path(__file__).resolve().with_name("mylib.so"),
            Path(__file__).resolve().with_name("dot_product.so"),
            Path.cwd() / "mylib.so",
            Path.cwd() / "dot_product.so",
        ]

        for library_path in library_paths:
            if not library_path.exists():
                continue

            try:
                self.mylib = CDLL(str(library_path))
                self.mylib.py_dot_product.argtypes = [POINTER(c_double), POINTER(c_double), c_int]
                self.mylib.py_dot_product.restype = c_double
                self.mylib.py_vector_norm.argtypes = [POINTER(c_double), c_int]
                self.mylib.py_vector_norm.restype = c_double
                break
            except OSError:
                self.mylib = None

    def insert(self, key: str, vector: List[float]) -> None:
        self.vectors[key] = vector

    def retrieve(self, key: str) -> List[float]:
        return self.vectors.get(key, None)

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if self.mylib is not None:
            v1_array = (c_double * len(v1))(*v1)
            v2_array = (c_double * len(v2))(*v2)

            dot_product = self.mylib.py_dot_product(v1_array, v2_array, len(v1))
            norm_v1 = self.mylib.py_vector_norm(v1_array, len(v1))
            norm_v2 = self.mylib.py_vector_norm(v2_array, len(v2))
        else:
            dot_product = sum(left * right for left, right in zip(v1, v2))
            norm_v1 = math.sqrt(sum(value * value for value in v1))
            norm_v2 = math.sqrt(sum(value * value for value in v2))

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return dot_product / (norm_v1 * norm_v2)

    def search(self, query_vector: List[float], k: int) -> List[Tuple[str, float]]:
        similarities = [(key, self.cosine_similarity(query_vector, vector)) for key, vector in self.vectors.items()]
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]
