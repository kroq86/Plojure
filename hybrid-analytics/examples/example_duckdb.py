from duckdb_vec import DuckDBVectorDatabase
import numpy as np

def main():
    # Initialize database with 1GB cache
    db = DuckDBVectorDatabase(
        "vectors.duckdb",
        chunk_size=1000,
        max_cache_size=1024 * 1024 * 1024
    )
    
    # Generate some test vectors
    num_vectors = 10000
    dimensions = 128
    vectors = []
    for i in range(num_vectors):
        vector = list(np.random.randn(dimensions))
        vectors.append((f"vec_{i}", vector))
    
    # Insert vectors
    print(f"Inserting {num_vectors} vectors...")
    db.batch_insert(vectors)
    
    # Generate a query vector
    query_vector = list(np.random.randn(dimensions))
    k = 5
    
    # Test different search methods
    print("\nTesting search methods:")
    for method in ["exact", "approximate", "lsh"]:
        results = db.search(query_vector, k, method=method)
        print(f"\n{method.capitalize()} Search Results:")
        for i, (key, similarity) in enumerate(results, 1):
            print(f"{i}. {key}: {similarity:.4f}")
    
    # Test different similarity metrics
    print("\nTesting similarity metrics:")
    for metric in ["cosine", "euclidean", "dot_product"]:
        db.similarity_metric = metric
        results = db.search(query_vector, k)
        print(f"\n{metric.capitalize()} Similarity Results:")
        for i, (key, similarity) in enumerate(results, 1):
            print(f"{i}. {key}: {similarity:.4f}")
    
    # Get performance metrics
    metrics = db.get_metrics()
    print("\nPerformance Metrics:")
    print(f"Total vectors: {metrics.total_vectors:,}")
    print(f"Memory usage: {metrics.memory_usage:.2f} MB")
    print(f"Cache size: {metrics.cache_size/1024/1024:.2f} MB")
    print(f"Cache hits: {metrics.cache_hits:,}")
    print(f"Cache misses: {metrics.cache_misses:,}")
    
    # Clean up
    db.close()

if __name__ == "__main__":
    main() 