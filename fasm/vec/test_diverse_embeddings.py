import numpy as np
from duckdb_vec import DuckDBVectorDatabase, SearchMetrics
from typing import List, Tuple
import time
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import seaborn as sns

def generate_text_embeddings(num_vectors: int, dimensions: int = 768) -> List[Tuple[str, List[float]]]:
    """Simulate BERT-like text embeddings."""
    vectors = []
    # Create clusters to simulate semantic similarity
    num_clusters = 20
    cluster_centers = np.random.normal(0, 1, (num_clusters, dimensions))
    # Normalize cluster centers
    cluster_centers = cluster_centers / np.linalg.norm(cluster_centers, axis=1)[:, np.newaxis]
    
    cluster_vectors = {i: [] for i in range(num_clusters)}
    for i in range(num_vectors):
        # Select a random cluster
        cluster_idx = i % num_clusters
        # Generate vector near cluster center with controlled noise
        noise = np.random.normal(0, 0.05, dimensions)  # Reduced noise
        vector = cluster_centers[cluster_idx] + noise
        # Normalize the vector
        vector = vector / np.linalg.norm(vector)
        vectors.append((f"text_{i}", list(vector)))
        cluster_vectors[cluster_idx].append((f"text_{i}", list(vector)))
    return vectors, cluster_vectors

def generate_image_embeddings(num_vectors: int, dimensions: int = 2048) -> List[Tuple[str, List[float]]]:
    """Simulate ResNet-like image embeddings."""
    vectors = []
    # Create feature clusters to simulate visual similarity
    num_clusters = 15
    cluster_centers = np.random.normal(0, 1, (num_clusters, dimensions))
    # Normalize cluster centers
    cluster_centers = cluster_centers / np.linalg.norm(cluster_centers, axis=1)[:, np.newaxis]
    
    cluster_vectors = {i: [] for i in range(num_clusters)}
    for i in range(num_vectors):
        # Select a random cluster
        cluster_idx = i % num_clusters
        # Generate vector near cluster center with controlled noise
        noise = np.random.normal(0, 0.05, dimensions)  # Reduced noise
        vector = cluster_centers[cluster_idx] + noise
        # Add controlled sparsity
        sparsity_mask = np.random.binomial(1, 0.8, dimensions)  # Increased density
        vector = np.multiply(vector, sparsity_mask)
        # Normalize the vector
        vector = vector / np.linalg.norm(vector)
        vectors.append((f"img_{i}", list(vector)))
        cluster_vectors[cluster_idx].append((f"img_{i}", list(vector)))
    return vectors, cluster_vectors

def generate_audio_embeddings(num_vectors: int, dimensions: int = 512) -> List[Tuple[str, List[float]]]:
    """Simulate audio embeddings (e.g., from wav2vec)."""
    vectors = []
    # Create base patterns for temporal similarity
    num_patterns = 10
    base_patterns = []
    for p in range(num_patterns):
        pattern = np.sin(np.linspace(0, 10 + p, dimensions))
        pattern = pattern / np.linalg.norm(pattern)  # Normalize patterns
        base_patterns.append(pattern)
    
    cluster_vectors = {i: [] for i in range(num_patterns)}
    for i in range(num_vectors):
        # Select a base pattern
        pattern_idx = i % num_patterns
        base = base_patterns[pattern_idx]
        # Add minimal noise to create variations
        noise = np.random.normal(0, 0.05, dimensions)  # Reduced noise
        vector = base + noise
        # Normalize the vector
        vector = vector / np.linalg.norm(vector)
        vectors.append((f"audio_{i}", list(vector)))
        cluster_vectors[pattern_idx].append((f"audio_{i}", list(vector)))
    return vectors, cluster_vectors

def validate_clusters(cluster_vectors: dict, similarity_metric: str = "cosine") -> float:
    """Validate cluster quality by measuring intra-cluster similarity."""
    total_similarity = 0
    total_pairs = 0
    
    for cluster in cluster_vectors.values():
        if len(cluster) < 2:
            continue
        
        # Compare each vector with every other vector in the cluster
        for i in range(len(cluster)):
            for j in range(i + 1, len(cluster)):
                vec1 = np.array(cluster[i][1])
                vec2 = np.array(cluster[j][1])
                
                if similarity_metric == "cosine":
                    similarity = np.dot(vec1, vec2)
                elif similarity_metric == "euclidean":
                    similarity = -np.linalg.norm(vec1 - vec2)  # Negative because smaller is better
                else:  # dot_product
                    similarity = np.dot(vec1, vec2)
                
                total_similarity += similarity
                total_pairs += 1
    
    return total_similarity / total_pairs if total_pairs > 0 else 0.0

def plot_metrics(metrics_list: List[SearchMetrics], labels: List[str], title: str):
    """Plot performance metrics."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot times
    times = [(m.exact_time, m.approx_time, m.lsh_time) for m in metrics_list]
    times = np.array(times).T
    ax1.bar(labels, times[0], label='Exact')
    ax1.bar(labels, times[1], bottom=times[0], label='Approximate')
    ax1.bar(labels, times[2], bottom=times[0]+times[1], label='LSH')
    ax1.set_title('Search Times')
    ax1.legend()
    ax1.set_ylabel('Time (seconds)')
    
    # Plot recall
    recalls = [m.recall_at_k for m in metrics_list]
    ax2.bar(labels, recalls)
    ax2.set_title('Recall@k')
    ax2.set_ylabel('Recall')
    
    # Plot memory usage
    memory = [m.memory_used for m in metrics_list]
    ax3.bar(labels, memory)
    ax3.set_title('Memory Usage')
    ax3.set_ylabel('MB')
    
    # Plot cache hit ratio
    cache_hits = [m.cache_hit_ratio for m in metrics_list]
    ax4.bar(labels, cache_hits)
    ax4.set_title('Cache Hit Ratio')
    ax4.set_ylabel('Ratio')
    
    plt.tight_layout()
    plt.savefig(f'performance_{title}.png')
    plt.close()

def test_embedding_type(db: DuckDBVectorDatabase, vectors: List[Tuple[str, List[float]]], 
                       cluster_vectors: dict, k: int = 5) -> SearchMetrics:
    """Test database performance for a specific type of embedding."""
    # Insert vectors
    db.batch_insert(vectors)
    
    # Select query vector from the largest cluster
    largest_cluster = max(cluster_vectors.values(), key=len)
    query_vector = np.array(largest_cluster[0][1])  # Use first vector from largest cluster
    
    # Perform search with metrics
    metrics = db.search_with_metrics(list(query_vector), k)
    
    # Clear database for next test
    db.conn.execute("DELETE FROM vectors")
    db.clear_cache()
    
    return metrics

def visualize_embeddings(vectors: List[Tuple[str, List[float]]], title: str):
    """Visualize embeddings using t-SNE."""
    # Extract vectors
    vector_data = np.array([v[1] for v in vectors])
    
    # Apply t-SNE
    tsne = TSNE(n_components=2, random_state=42)
    embedded = tsne.fit_transform(vector_data[:1000])  # Use subset for speed
    
    # Plot
    plt.figure(figsize=(10, 8))
    plt.scatter(embedded[:, 0], embedded[:, 1], alpha=0.5)
    plt.title(f't-SNE visualization of {title}')
    plt.savefig(f'tsne_{title}.png')
    plt.close()
    
    # Calculate and print clustering metrics
    distances = np.linalg.norm(vector_data[:1000] - vector_data[:1000].mean(axis=0), axis=1)
    print(f"\n{title} Statistics:")
    print(f"Mean L2 distance from center: {distances.mean():.4f}")
    print(f"Std L2 distance from center: {distances.std():.4f}")

def main():
    # Test parameters
    num_vectors = 10000
    k = 5
    
    # Initialize database with smaller chunk size for better distribution
    db = DuckDBVectorDatabase(
        ":memory:",
        chunk_size=500,
        max_cache_size=1024 * 1024 * 1024
    )
    
    # Generate different types of embeddings
    text_vectors, text_clusters = generate_text_embeddings(num_vectors)
    image_vectors, image_clusters = generate_image_embeddings(num_vectors)
    audio_vectors, audio_clusters = generate_audio_embeddings(num_vectors)
    
    # Validate cluster quality
    print("\nValidating cluster quality...")
    for name, clusters in [("Text", text_clusters), ("Image", image_clusters), ("Audio", audio_clusters)]:
        similarity = validate_clusters(clusters, "cosine")
        print(f"{name} cluster similarity: {similarity:.4f}")
    
    # Visualize embeddings
    print("\nGenerating embedding visualizations...")
    visualize_embeddings(text_vectors, "text_embeddings")
    visualize_embeddings(image_vectors, "image_embeddings")
    visualize_embeddings(audio_vectors, "audio_embeddings")
    
    # Test each embedding type
    print("\nTesting different embedding types...")
    
    metrics_list = []
    labels = ['Text', 'Image', 'Audio']
    
    # Test text embeddings
    print("\nTesting text embeddings...")
    text_metrics = test_embedding_type(db, text_vectors, text_clusters, k)
    metrics_list.append(text_metrics)
    print(f"Text embeddings recall@{k}: {text_metrics.recall_at_k:.4f}")
    
    # Test image embeddings
    print("\nTesting image embeddings...")
    image_metrics = test_embedding_type(db, image_vectors, image_clusters, k)
    metrics_list.append(image_metrics)
    print(f"Image embeddings recall@{k}: {image_metrics.recall_at_k:.4f}")
    
    # Test audio embeddings
    print("\nTesting audio embeddings...")
    audio_metrics = test_embedding_type(db, audio_vectors, audio_clusters, k)
    metrics_list.append(audio_metrics)
    print(f"Audio embeddings recall@{k}: {audio_metrics.recall_at_k:.4f}")
    
    # Plot performance metrics
    plot_metrics(metrics_list, labels, "embedding_types")
    
    # Test different similarity metrics
    print("\nTesting different similarity metrics...")
    for metric in ["cosine", "euclidean", "dot_product"]:
        db.similarity_metric = metric
        metrics_list = []
        
        print(f"\nUsing {metric} similarity:")
        text_metrics = test_embedding_type(db, text_vectors[:1000], {k: v[:1000] for k, v in text_clusters.items()}, k)
        metrics_list.append(text_metrics)
        print(f"Text embeddings recall@{k}: {text_metrics.recall_at_k:.4f}")
        
        image_metrics = test_embedding_type(db, image_vectors[:1000], {k: v[:1000] for k, v in image_clusters.items()}, k)
        metrics_list.append(image_metrics)
        print(f"Image embeddings recall@{k}: {image_metrics.recall_at_k:.4f}")
        
        audio_metrics = test_embedding_type(db, audio_vectors[:1000], {k: v[:1000] for k, v in audio_clusters.items()}, k)
        metrics_list.append(audio_metrics)
        print(f"Audio embeddings recall@{k}: {audio_metrics.recall_at_k:.4f}")
        
        plot_metrics(metrics_list, labels, f"similarity_{metric}")
    
    # Clean up
    db.close()

if __name__ == "__main__":
    main() 