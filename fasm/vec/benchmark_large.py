from duckdb_vec import DuckDBVectorDatabase
import numpy as np
import time
from typing import List, Tuple, Dict
import matplotlib.pyplot as plt
from tabulate import tabulate

def generate_random_vectors(num_vectors: int, dimensions: int) -> List[Tuple[str, List[float]]]:
    vectors = []
    for i in range(num_vectors):
        vector = list(np.random.randn(dimensions))
        vectors.append((f"vec_{i}", vector))
    return vectors

def run_benchmark(db: DuckDBVectorDatabase, vectors: List[Tuple[str, List[float]]], query_vector: List[float], k: int):
    results = {}
    
    # Insertion benchmark
    start_time = time.time()
    db.batch_insert(vectors)
    insert_time = time.time() - start_time
    results["insertion"] = {
        "time": insert_time,
        "vectors_per_second": len(vectors) / insert_time
    }
    
    # Search benchmarks for different methods
    methods = ["exact", "approximate", "lsh"]
    search_results = {}
    
    for method in methods:
        start_time = time.time()
        similar_vectors = db.search(query_vector, k, method=method)
        search_time = time.time() - start_time
        
        search_results[method] = {
            "time": search_time,
            "results": similar_vectors
        }
    
    results["search"] = search_results
    
    # Get performance metrics
    results["metrics"] = db.get_metrics()
    
    return results

def print_results(results: Dict):
    print("\n=== Benchmark Results ===\n")
    
    # Insertion performance
    print(f"Insertion Performance:")
    print(f"Total time: {results['insertion']['time']:.2f} seconds")
    print(f"Vectors per second: {results['insertion']['vectors_per_second']:.2f}")
    
    # Search performance comparison
    search_data = []
    for method, data in results["search"].items():
        best_similarity = "N/A"
        if data["results"] and len(data["results"]) > 0:
            best_similarity = f"{data['results'][0][1]:.4f}"
        
        search_data.append([
            method,
            f"{data['time']:.4f}s",
            best_similarity
        ])
    
    print("\nSearch Performance:")
    print(tabulate(search_data, headers=["Method", "Time", "Best Similarity"]))
    
    # Cache and memory metrics
    metrics = results["metrics"]
    print("\nPerformance Metrics:")
    print(f"Cache hits: {metrics.cache_hits}")
    print(f"Cache misses: {metrics.cache_misses}")
    hit_ratio = 0 if metrics.cache_hits + metrics.cache_misses == 0 else metrics.cache_hits/(metrics.cache_hits + metrics.cache_misses)
    print(f"Cache hit ratio: {hit_ratio:.2%}")
    print(f"Memory usage: {metrics.memory_usage:.2f} MB")
    print(f"Total vectors: {metrics.total_vectors}")
    print(f"Cache size: {metrics.cache_size/1024/1024:.2f} MB")

def benchmark_similarity_metrics(db: DuckDBVectorDatabase, query_vector: List[float], k: int):
    metrics = ["cosine", "euclidean", "dot_product"]
    results = {}
    
    for metric in metrics:
        db.similarity_metric = metric
        start_time = time.time()
        similar_vectors = db.search(query_vector, k)
        search_time = time.time() - start_time
        results[metric] = {
            "time": search_time,
            "results": similar_vectors
        }
    
    return results

def main():
    # Test parameters
    dimensions = 128
    k = 5
    
    # Test with different dataset sizes
    sizes = [10000, 50000, 100000]
    
    for size in sizes:
        print(f"\n=== Testing with {size} vectors ===")
        vectors = generate_random_vectors(size, dimensions)
        query_vector = list(np.random.randn(dimensions))
        
        db = DuckDBVectorDatabase(
            f"vectors_benchmark_{size}.duckdb",
            chunk_size=1000,
            max_cache_size=1024 * 1024 * 1024  # 1GB cache
        )
        
        # Run main benchmark
        results = run_benchmark(db, vectors, query_vector, k)
        print_results(results)
        
        # Test different similarity metrics
        print("\nTesting different similarity metrics:")
        similarity_results = benchmark_similarity_metrics(db, query_vector, k)
        
        metric_data = []
        for metric, data in similarity_results.items():
            best_score = "N/A"
            if data["results"] and len(data["results"]) > 0:
                best_score = f"{data['results'][0][1]:.4f}"
            
            metric_data.append([
                metric,
                f"{data['time']:.4f}s",
                best_score
            ])
        
        print(tabulate(metric_data, headers=["Metric", "Time", "Best Score"]))
        
        db.close()

if __name__ == "__main__":
    main() 