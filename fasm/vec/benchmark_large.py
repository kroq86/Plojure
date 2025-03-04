from duckdb_vec import DuckDBVectorDatabase
import numpy as np
import time
from typing import List, Tuple, Dict
import matplotlib.pyplot as plt
from tabulate import tabulate
import psutil

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
    
    # Run comprehensive search benchmark with metrics
    search_metrics = db.search_with_metrics(query_vector, k)
    results["search_metrics"] = search_metrics
    
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
    search_metrics = results["search_metrics"]
    search_data = [
        ["exact", f"{search_metrics.exact_time:.4f}s"],
        ["approximate", f"{search_metrics.approx_time:.4f}s"],
        ["lsh", f"{search_metrics.lsh_time:.4f}s"]
    ]
    
    print("\nSearch Performance:")
    print(tabulate(search_data, headers=["Method", "Time"]))
    
    print("\nSearch Quality:")
    print(f"Recall@k: {search_metrics.recall_at_k:.2%}")
    print(f"Cache hit ratio: {search_metrics.cache_hit_ratio:.2%}")
    
    # Memory metrics
    metrics = results["metrics"]
    print("\nMemory Metrics:")
    print(f"Total memory usage: {search_metrics.memory_used:.2f} MB")
    print(f"Cache size: {metrics.cache_size/1024/1024:.2f} MB")
    print(f"Vectors in database: {metrics.total_vectors}")

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

def plot_performance_comparison(sizes, times):
    plt.figure(figsize=(10, 6))
    methods = ["exact", "approximate", "lsh"]
    for method in methods:
        plt.plot(sizes, [t[method] for t in times], marker='o', label=method)
    
    plt.xlabel("Number of Vectors")
    plt.ylabel("Search Time (seconds)")
    plt.title("Search Performance Comparison")
    plt.legend()
    plt.grid(True)
    plt.savefig("search_performance.png")
    plt.close()

def main():
    # Test parameters
    dimensions = 128
    k = 5
    
    # Test with different dataset sizes
    sizes = [10000, 50000, 100000]
    search_times = []
    
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
        
        # Store search times for plotting
        search_metrics = results["search_metrics"]
        search_times.append({
            "exact": search_metrics.exact_time,
            "approximate": search_metrics.approx_time,
            "lsh": search_metrics.lsh_time
        })
        
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
    
    # Plot performance comparison
    plot_performance_comparison(sizes, search_times)

if __name__ == "__main__":
    main() 