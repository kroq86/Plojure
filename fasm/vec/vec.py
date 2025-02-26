import ctypes
from ctypes import CDLL, POINTER, c_double, c_int
from collections import defaultdict
from typing import Tuple, List

# Load the shared library
mylib = CDLL('./mylib.so')
mylib.py_dot_product.argtypes = [POINTER(c_double), POINTER(c_double), c_int]
mylib.py_dot_product.restype = c_double

mylib.py_vector_norm.argtypes = [POINTER(c_double), c_int]
mylib.py_vector_norm.restype = c_double

class VectorDatabase:
    def __init__(self):
        self.vectors = {}

    def insert(self, key: str, vector: List[float]) -> None:
        self.vectors[key] = vector

    def retrieve(self, key: str) -> List[float]:
        return self.vectors.get(key, None)

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        # Convert lists to ctypes arrays
        v1_array = (c_double * len(v1))(*v1)
        v2_array = (c_double * len(v2))(*v2)

        # Use ctypes to call the assembly dot product function
        dot_product = mylib.py_dot_product(v1_array, v2_array, len(v1))
        
        # Calculate norms using assembly function
        norm_v1 = mylib.py_vector_norm(v1_array, len(v1))
        norm_v2 = mylib.py_vector_norm(v2_array, len(v2))

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return dot_product / (norm_v1 * norm_v2)

    def search(self, query_vector: List[float], k: int) -> List[Tuple[str, float]]:
        similarities = [(key, self.cosine_similarity(query_vector, vector)) for key, vector in self.vectors.items()]
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

# Example usage
if __name__ == "__main__":
    vector_db = VectorDatabase()

    # Insert vectors into the database
    vector_db.insert("vector_1", [0.1, 0.2, 0.3])
    vector_db.insert("vector_2", [0.4, 0.5, 0.6])
    vector_db.insert("vector_3", [0.15, 0.25, 0.35])

    # Retrieve a vector
    retrieved_vector = vector_db.retrieve("vector_1")
    print("Retrieved Vector:", retrieved_vector)

    # Perform similarity search
    query_vector = [0.15, 0.25, 0.35]
    similar_vectors = vector_db.search(query_vector, k=2)
    print("Similar Vectors:", similar_vectors)
