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
    num_clusters = 4
    # Generate more separated cluster centers
    cluster_centers = []
    for i in range(num_clusters):
        # Create orthogonal-like centers
        center = np.random.normal(0, 1, dimensions)
        # Make it more orthogonal to previous centers
        for prev_center in cluster_centers:
            center = center - np.dot(center, prev_center) * prev_center
        center = center / np.linalg.norm(center)
        cluster_centers.append(center)
    cluster_centers = np.array(cluster_centers)
    
    cluster_vectors = {i: [] for i in range(num_clusters)}
    for i in range(num_vectors):
        cluster_idx = i % num_clusters
        noise = np.random.normal(0, 0.01, dimensions)  # Reduced noise further
        vector = cluster_centers[cluster_idx] + noise
        vector = vector / np.linalg.norm(vector)
        vectors.append((f"text_{i}", list(vector)))
        cluster_vectors[cluster_idx].append((f"text_{i}", list(vector)))
    return vectors, cluster_vectors

def generate_image_embeddings(num_vectors: int, dimensions: int = 2048) -> List[Tuple[str, List[float]]]:
    """Simulate ResNet-like image embeddings."""
    vectors = []
    num_clusters = 4
    # Generate sparse orthogonal-like centers
    cluster_centers = []
    for i in range(num_clusters):
        # Create sparse orthogonal-like centers
        center = np.zeros(dimensions)
        active_dims = np.random.choice(dimensions, size=dimensions//4, replace=False)
        center[active_dims] = np.random.normal(0, 1, dimensions//4)
        # Make it more orthogonal to previous centers
        for prev_center in cluster_centers:
            center = center - np.dot(center, prev_center) * prev_center
        center = center / np.linalg.norm(center)
        cluster_centers.append(center)
    cluster_centers = np.array(cluster_centers)
    
    cluster_vectors = {i: [] for i in range(num_clusters)}
    for i in range(num_vectors):
        cluster_idx = i % num_clusters
        noise = np.random.normal(0, 0.01, dimensions)  # Reduced noise
        vector = cluster_centers[cluster_idx] + noise
        # Maintain sparsity pattern of cluster center
        vector = vector * (cluster_centers[cluster_idx] != 0)
        vector = vector / (np.linalg.norm(vector) + 1e-8)
        vectors.append((f"img_{i}", list(vector)))
        cluster_vectors[cluster_idx].append((f"img_{i}", list(vector)))
    return vectors, cluster_vectors

def generate_audio_embeddings(num_vectors: int, dimensions: int = 512) -> List[Tuple[str, List[float]]]:
    """Simulate audio embeddings (e.g., from wav2vec)."""
    vectors = []
    num_patterns = 4  # Reduced number of patterns for clearer clusters
    base_patterns = []
    
    # Generate base patterns with guaranteed non-zero values
    for p in range(num_patterns):
        # Use cosine waves with different frequencies and phases to ensure non-zero patterns
        t = np.linspace(0, 2*np.pi, dimensions)
        pattern = np.cos(t * (p + 1)) + np.sin(t * (p + 2))
        norm = np.linalg.norm(pattern)
        if norm > 0:  # Ensure we don't divide by zero
            pattern = pattern / norm
        else:
            pattern = np.ones(dimensions) / np.sqrt(dimensions)  # Fallback to uniform vector
        base_patterns.append(pattern)
    
    cluster_vectors = {i: [] for i in range(num_patterns)}
    for i in range(num_vectors):
        pattern_idx = i % num_patterns
        base = base_patterns[pattern_idx]
        noise = np.random.normal(0, 0.02, dimensions)  # Small noise
        vector = base + noise
        # Safe normalization
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        else:
            vector = np.ones(dimensions) / np.sqrt(dimensions)  # Fallback to uniform vector
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
                
                # Skip invalid vectors
                if np.any(np.isnan(vec1)) or np.any(np.isnan(vec2)):
                    continue
                
                if similarity_metric == "cosine":
                    # Safe cosine similarity calculation
                    norm1 = np.linalg.norm(vec1)
                    norm2 = np.linalg.norm(vec2)
                    if norm1 > 0 and norm2 > 0:
                        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
                    else:
                        continue
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
    
    # Test with multiple query vectors from different clusters
    total_metrics = []
    num_test_queries = min(5, len(cluster_vectors))
    
    for cluster_idx in range(num_test_queries):
        if cluster_idx >= len(cluster_vectors):
            break
        cluster = cluster_vectors[cluster_idx]
        if not cluster or len(cluster) < k:
            continue
            
        # Use center vector from each cluster as query
        cluster_vectors_array = np.array([v[1] for v in cluster])
        cluster_center = np.mean(cluster_vectors_array, axis=0)
        cluster_center = cluster_center / np.linalg.norm(cluster_center)
        
        # Find k-1 nearest neighbors (excluding the query vector itself)
        metrics = db.search_with_metrics(list(cluster_center), k)
        total_metrics.append(metrics)
    
    # Average the metrics
    if total_metrics:
        avg_metrics = SearchMetrics(
            exact_time=np.mean([m.exact_time for m in total_metrics]),
            approx_time=np.mean([m.approx_time for m in total_metrics]),
            lsh_time=np.mean([m.lsh_time for m in total_metrics]),
            recall_at_k=np.mean([m.recall_at_k for m in total_metrics]),
            memory_used=np.mean([m.memory_used for m in total_metrics]),
            cache_hit_ratio=np.mean([m.cache_hit_ratio for m in total_metrics])
        )
    else:
        avg_metrics = SearchMetrics(0, 0, 0, 0, 0, 0)
    
    # Clear database for next test
    db.conn.execute("DELETE FROM vectors")
    db.clear_cache()
    
    return avg_metrics

def visualize_embeddings(vectors: List[Tuple[str, List[float]]], title: str):
    """Visualize embeddings using t-SNE."""
    # Extract vectors and filter out any invalid values
    vector_data = np.array([v[1] for v in vectors])
    
    # Check for and remove any NaN values
    valid_indices = ~np.any(np.isnan(vector_data), axis=1)
    if not np.all(valid_indices):
        print(f"Warning: Found {np.sum(~valid_indices)} invalid vectors in {title}, removing them for visualization")
        vector_data = vector_data[valid_indices]
    
    if len(vector_data) == 0:
        print(f"Error: No valid vectors to visualize for {title}")
        return
        
    # Use subset for speed but ensure we have enough valid vectors
    max_vectors = min(1000, len(vector_data))
    vector_subset = vector_data[:max_vectors]
    
    # Apply t-SNE
    tsne = TSNE(n_components=2, random_state=42)
    try:
        embedded = tsne.fit_transform(vector_subset)
        
        # Plot
        plt.figure(figsize=(10, 8))
        plt.scatter(embedded[:, 0], embedded[:, 1], alpha=0.5)
        plt.title(f't-SNE visualization of {title}')
        plt.savefig(f'tsne_{title}.png')
        plt.close()
        
        # Calculate and print clustering metrics
        distances = np.linalg.norm(vector_subset - vector_subset.mean(axis=0), axis=1)
        print(f"\n{title} Statistics:")
        print(f"Mean L2 distance from center: {distances.mean():.4f}")
        print(f"Std L2 distance from center: {distances.std():.4f}")
    except Exception as e:
        print(f"Error visualizing {title}: {str(e)}")

def main():
    # Test parameters
    num_vectors = 1000
    k = 10  # Increased k for better recall evaluation
    
    # Initialize database with optimized parameters
    db = DuckDBVectorDatabase(
        ":memory:",
        chunk_size=200,  # Increased chunk size for better batching
        max_cache_size=2 * 1024 * 1024 * 1024  # Increased cache size
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