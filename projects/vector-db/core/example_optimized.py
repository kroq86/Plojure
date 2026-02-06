from duckdb_vec import DuckDBVectorDatabase
import numpy as np
import time
from typing import List, Tuple

def generate_random_vectors(num_vectors: int, dimensions: int) -> List[Tuple[str, List[float]]]:
    vectors = []
    for i in range(num_vectors):
        vector = list(np.random.randn(dimensions))
        vectors.append((f"vec_{i}", vector))
    return vectors

def benchmark_search(db: DuckDBVectorDatabase, query_vector: List[float], k: int):
    start_time = time.time()
    results = db.search(query_vector, k)
    search_time = time.time() - start_time
    return results, search_time

def benchmark_approximate_search(db: DuckDBVectorDatabase, query_vector: List[float], k: int, sample_size: int):
    start_time = time.time()
    results = db.approximate_search(query_vector, k, sample_size)
    search_time = time.time() - start_time
    return results, search_time

def main():
    num_vectors = 10000
    dimensions = 128
    k = 5
    
    print(f"Generating {num_vectors} random vectors with {dimensions} dimensions...")
    vectors = generate_random_vectors(num_vectors, dimensions)
    query_vector = list(np.random.randn(dimensions))

    db = DuckDBVectorDatabase("vectors_optimized.duckdb", chunk_size=1000)
    
    print("\nInserting vectors in batches...")
    start_time = time.time()
    db.batch_insert(vectors)
    insert_time = time.time() - start_time
    print(f"Insertion time: {insert_time:.2f} seconds")

    print("\nPerforming exact search...")
    results_exact, time_exact = benchmark_search(db, query_vector, k)
    print(f"Exact search time: {time_exact:.2f} seconds")
    print("Top 5 exact results:")
    for key, similarity in results_exact:
        print(f"Key: {key}, Similarity: {similarity:.4f}")

    print("\nPerforming approximate search (10% sample)...")
    sample_size = num_vectors // 10
    results_approx, time_approx = benchmark_approximate_search(db, query_vector, k, sample_size)
    print(f"Approximate search time: {time_approx:.2f} seconds")
    print("Top 5 approximate results:")
    for key, similarity in results_approx:
        print(f"Key: {key}, Similarity: {similarity:.4f}")

    print(f"\nSpeed improvement: {time_exact/time_approx:.2f}x faster with approximate search")

    db.close()

if __name__ == "__main__":
    main() 