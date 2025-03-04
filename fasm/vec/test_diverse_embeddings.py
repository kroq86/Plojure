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
    for i in range(num_vectors):
        # BERT embeddings tend to be normally distributed
        vector = list(np.random.normal(0, 0.1, dimensions))
        vectors.append((f"text_{i}", vector))
    return vectors

def generate_image_embeddings(num_vectors: int, dimensions: int = 2048) -> List[Tuple[str, List[float]]]:
    """Simulate ResNet-like image embeddings."""
    vectors = []
    for i in range(num_vectors):
        # Image embeddings often have more pronounced features
        vector = list(np.random.normal(0, 0.2, dimensions))
        # Add some sparsity typical in image embeddings
        vector = np.multiply(vector, np.random.binomial(1, 0.7, dimensions))
        vectors.append((f"img_{i}", vector))
    return vectors

def generate_audio_embeddings(num_vectors: int, dimensions: int = 512) -> List[Tuple[str, List[float]]]:
    """Simulate audio embeddings (e.g., from wav2vec)."""
    vectors = []
    for i in range(num_vectors):
        # Audio embeddings often have temporal patterns
        base = np.sin(np.linspace(0, 10, dimensions))
        noise = np.random.normal(0, 0.1, dimensions)
        vector = list(base + noise)
        vectors.append((f"audio_{i}", vector))
    return vectors

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
                       query_vector: List[float], k: int = 5) -> SearchMetrics:
    """Test database performance for a specific type of embedding."""
    # Insert vectors
    db.batch_insert(vectors)
    
    # Perform search with metrics
    metrics = db.search_with_metrics(query_vector, k)
    
    # Clear database for next test
    db.conn.execute("DELETE FROM vectors")
    db.clear_cache()
    
    return metrics

def main():
    # Test parameters
    num_vectors = 10000
    k = 5
    
    # Initialize database
    db = DuckDBVectorDatabase(
        ":memory:",
        chunk_size=1000,
        max_cache_size=1024 * 1024 * 1024  # 1GB cache
    )
    
    # Generate different types of embeddings
    text_vectors = generate_text_embeddings(num_vectors)
    image_vectors = generate_image_embeddings(num_vectors)
    audio_vectors = generate_audio_embeddings(num_vectors)
    
    # Generate query vectors for each type
    text_query = list(np.random.normal(0, 0.1, 768))
    image_query = list(np.random.normal(0, 0.2, 2048))
    audio_query = list(np.random.normal(0, 0.1, 512))
    
    # Test each embedding type
    print("\nTesting different embedding types...")
    
    metrics_list = []
    labels = ['Text', 'Image', 'Audio']
    
    # Test text embeddings
    print("\nTesting text embeddings...")
    text_metrics = test_embedding_type(db, text_vectors, text_query, k)
    metrics_list.append(text_metrics)
    print(f"Text embeddings recall@{k}: {text_metrics.recall_at_k:.4f}")
    
    # Test image embeddings
    print("\nTesting image embeddings...")
    image_metrics = test_embedding_type(db, image_vectors, image_query, k)
    metrics_list.append(image_metrics)
    print(f"Image embeddings recall@{k}: {image_metrics.recall_at_k:.4f}")
    
    # Test audio embeddings
    print("\nTesting audio embeddings...")
    audio_metrics = test_embedding_type(db, audio_vectors, audio_query, k)
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
        text_metrics = test_embedding_type(db, text_vectors[:1000], text_query, k)
        metrics_list.append(text_metrics)
        print(f"Text embeddings recall@{k}: {text_metrics.recall_at_k:.4f}")
        
        image_metrics = test_embedding_type(db, image_vectors[:1000], image_query, k)
        metrics_list.append(image_metrics)
        print(f"Image embeddings recall@{k}: {image_metrics.recall_at_k:.4f}")
        
        audio_metrics = test_embedding_type(db, audio_vectors[:1000], audio_query, k)
        metrics_list.append(audio_metrics)
        print(f"Audio embeddings recall@{k}: {audio_metrics.recall_at_k:.4f}")
        
        plot_metrics(metrics_list, labels, f"similarity_{metric}")
    
    # Clean up
    db.close()

if __name__ == "__main__":
    main() 