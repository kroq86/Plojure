import numpy as np
from ctypes import CDLL, POINTER, c_double, c_int
from collections import defaultdict
from typing import Tuple, List

# Load the shared library
mylib = CDLL('./mylib.so')
mylib.py_dot_product.argtypes = [POINTER(c_double), POINTER(c_double), c_int]
mylib.py_dot_product.restype = c_double

class VectorDatabase:
    def __init__(self):
        self.vectors = defaultdict(np.ndarray)

    def insert(self, key: str, vector: np.ndarray) -> None:
        self.vectors[key] = vector

    def retrieve(self, key: str) -> np.ndarray:
        return self.vectors.get(key, None)

    def cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        # Use ctypes to call the assembly dot product function
        dot_product = mylib.py_dot_product(v1.ctypes.data_as(POINTER(c_double)), v2.ctypes.data_as(POINTER(c_double)), len(v1))
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return dot_product / (norm_v1 * norm_v2)

    def search(self, query_vector: np.ndarray, k: int) -> List[Tuple[str, float]]:
        similarities = [(key, self.cosine_similarity(query_vector, vector)) for key, vector in self.vectors.items()]
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

# Example usage
if __name__ == "__main__":
    vector_db = VectorDatabase()

    # Insert vectors into the database
    vector_db.insert("vector_1", np.array([0.1, 0.2, 0.3]))
    vector_db.insert("vector_2", np.array([0.4, 0.5, 0.6]))
    vector_db.insert("vector_3", np.array([0.15, 0.25, 0.35]))

    # Retrieve a vector
    retrieved_vector = vector_db.retrieve("vector_1")
    print("Retrieved Vector:", retrieved_vector)

    # Perform similarity search
    query_vector = np.array([0.15, 0.25, 0.35])
    similar_vectors = vector_db.search(query_vector, k=2)
    print("Similar Vectors:", similar_vectors)
