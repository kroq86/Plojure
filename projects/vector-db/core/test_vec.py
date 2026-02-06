import pytest
from vec import VectorDatabase

def test_insert_and_retrieve():
    db = VectorDatabase()
    db.insert("vector_1", [0.1, 0.2, 0.3])
    assert db.retrieve("vector_1") == [0.1, 0.2, 0.3]

def test_cosine_similarity():
    db = VectorDatabase()
    v1 = [0.1, 0.2, 0.3]
    v2 = [0.4, 0.5, 0.6]
    similarity = db.cosine_similarity(v1, v2)
    assert similarity > 0

def test_search():
    db = VectorDatabase()
    db.insert("vector_1", [0.1, 0.2, 0.3])
    db.insert("vector_2", [0.4, 0.5, 0.6])
    query_vector = [0.15, 0.25, 0.35]
    similar_vectors = db.search(query_vector, k=2)
    assert len(similar_vectors) == 2
