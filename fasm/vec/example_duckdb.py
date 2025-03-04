from duckdb_vec import DuckDBVectorDatabase
import numpy as np

def main():
    # Initialize the database with a file path (or use :memory: for in-memory database)
    db = DuckDBVectorDatabase("vectors.duckdb")

    # Create some example vectors
    vectors = [
        ("doc1", [1.0, 2.0, 3.0]),
        ("doc2", [2.0, 3.0, 4.0]),
        ("doc3", [3.0, 4.0, 5.0]),
        ("doc4", [1.0, 1.0, 1.0])
    ]

    # Batch insert vectors
    db.batch_insert(vectors)

    # Perform a similarity search
    query_vector = [1.0, 2.0, 3.0]
    k = 2
    results = db.search(query_vector, k)
    
    print("\nTop", k, "most similar vectors to", query_vector)
    for key, similarity in results:
        vector = db.retrieve(key)
        print(f"Key: {key}, Similarity: {similarity:.4f}, Vector: {vector}")

    # Demonstrate SQL capabilities
    print("\nAll vectors in the database:")
    all_keys = db.get_all_keys()
    for key in all_keys:
        vector = db.retrieve(key)
        print(f"Key: {key}, Vector: {vector}")

    # Clean up
    db.close()

if __name__ == "__main__":
    main() 