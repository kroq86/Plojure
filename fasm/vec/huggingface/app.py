import os
import sys
import json
import numpy as np
import gradio as gr
import subprocess
import uvicorn
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Dict, Optional, Union

from duckdb_vec import DuckDBVectorDatabase

app = FastAPI(title="MCP Vector Database")
db_path = os.environ.get("VECTOR_DB_PATH", ":memory:")
vector_db = DuckDBVectorDatabase(db_path=db_path)

document_store = {
    "doc1": "Python is a high-level programming language known for its readability and versatility.",
    "doc2": "Machine learning models require training data to learn patterns and make predictions.",
    "doc3": "Database indexing improves query performance by creating data structures that speed up data retrieval.",
    "doc4": "Artificial intelligence systems aim to simulate human intelligence in machines.",
    "doc5": "Cloud computing provides on-demand delivery of computing resources over the internet."
}

def init_sample_data():
    def simple_embedding(text: str, dim: int = 10) -> List[float]:
        np.random.seed(hash(text) % 2**32)
        vec = np.random.normal(0, 1, dim)
        
        char_counts = {}
        for char in text.lower():
            if char.isalpha():
                char_counts[char] = char_counts.get(char, 0) + 1
        
        for i, char in enumerate("abcdefghij"):
            if i < dim and char in char_counts:
                vec[i] += char_counts[char] * 0.1
        
        return (vec / np.linalg.norm(vec)).tolist()
    
    for doc_id, doc_text in document_store.items():
        vector = simple_embedding(doc_text)
        vector_db.insert(doc_id, vector)
        print(f"Inserted {doc_id} with vector length {len(vector)}")

def simple_embedding(text: str, dim: int = 10) -> List[float]:
    np.random.seed(hash(text) % 2**32)
    vec = np.random.normal(0, 1, dim)
    
    char_counts = {}
    for char in text.lower():
        if char.isalpha():
            char_counts[char] = char_counts.get(char, 0) + 1
    
    for i, char in enumerate("abcdefghij"):
        if i < dim and char in char_counts:
            vec[i] += char_counts[char] * 0.1
    
    return (vec / np.linalg.norm(vec)).tolist()

@app.get("/")
def read_root():
    return {"message": "MCP Vector Database API", "version": "1.0.0"}

@app.get("/vectors")
def get_all_vectors():
    keys = vector_db.get_all_keys()
    result = {}
    for key in keys:
        if key in document_store:
            result[key] = document_store[key]
        else:
            result[key] = "Vector without associated document"
    return result

@app.get("/search_text")
def search_text(query: str = Query(..., description="Text to search for"), 
               k: int = Query(3, description="Number of results to return"),
               method: str = Query("hnsw", description="Search method to use")):
    try:
        query_vector = simple_embedding(query)
        
        results = vector_db.search(query_vector, k, method)
        
        formatted_results = []
        for key, similarity in results:
            doc_text = document_store.get(key, "No document text available")
            formatted_results.append({
                "key": key,
                "similarity": float(similarity),
                "document": doc_text
            })
        
        return {"query": query, "results": formatted_results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Search error: {str(e)}")

@app.post("/vectors/{key}")
def insert_vector(key: str, vector: List[float]):
    try:
        vector_db.insert(key, vector)
        return {"status": "success", "message": f"Vector inserted with key: {key}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/vectors/{key}")
def delete_vector(key: str):
    success = vector_db.delete(key)
    if success:
        return {"status": "success", "message": f"Vector with key {key} deleted"}
    else:
        raise HTTPException(status_code=404, detail=f"Vector with key {key} not found")

@app.post("/search")
def search_vectors(query_vector: List[float], k: int = 3, method: str = "hnsw"):
    try:
        results = vector_db.search(query_vector, k, method)
        formatted_results = []
        
        for key, similarity in results:
            doc_text = document_store.get(key, "No document text available")
            formatted_results.append({
                "key": key,
                "similarity": float(similarity),
                "document": doc_text
            })
        
        return {"results": formatted_results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/metrics")
def get_metrics():
    try:
        metrics = vector_db.get_metrics()
        return {
            "cache_hits": metrics.cache_hits,
            "cache_misses": metrics.cache_misses,
            "memory_usage_mb": metrics.memory_usage,
            "total_vectors": metrics.total_vectors,
            "cache_size_bytes": metrics.cache_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def search_similar_docs(document_text: str, num_results: int, search_method: str):
    def simple_embedding(text: str, dim: int = 10) -> List[float]:
        np.random.seed(hash(text) % 2**32)
        vec = np.random.normal(0, 1, dim)
        char_counts = {}
        for char in text.lower():
            if char.isalpha():
                char_counts[char] = char_counts.get(char, 0) + 1
        for i, char in enumerate("abcdefghij"):
            if i < dim and char in char_counts:
                vec[i] += char_counts[char] * 0.1
        return (vec / np.linalg.norm(vec)).tolist()
    
    query_vector = simple_embedding(document_text)
    
    results = vector_db.search(query_vector, num_results, search_method)
    
    formatted_results = ""
    for i, (key, similarity) in enumerate(results):
        doc_text = document_store.get(key, "No document text available")
        formatted_results += f"Result {i+1}:\n"
        formatted_results += f"Document ID: {key}\n"
        formatted_results += f"Similarity: {similarity:.4f}\n"
        formatted_results += f"Content: {doc_text}\n\n"
    
    return formatted_results

def add_document(doc_id: str, document_text: str):
    def simple_embedding(text: str, dim: int = 10) -> List[float]:
        np.random.seed(hash(text) % 2**32)
        vec = np.random.normal(0, 1, dim)
        char_counts = {}
        for char in text.lower():
            if char.isalpha():
                char_counts[char] = char_counts.get(char, 0) + 1
        for i, char in enumerate("abcdefghij"):
            if i < dim and char in char_counts:
                vec[i] += char_counts[char] * 0.1
        return (vec / np.linalg.norm(vec)).tolist()
    
    try:
        vector = simple_embedding(document_text)
        
        vector_db.insert(doc_id, vector)
        
        document_store[doc_id] = document_text
        
        return f"Document '{doc_id}' added successfully!"
    except Exception as e:
        return f"Error adding document: {str(e)}"

def list_documents():
    keys = vector_db.get_all_keys()
    result = ""
    
    for key in keys:
        doc_text = document_store.get(key, "Vector without associated document")
        result += f"ID: {key}\n"
        result += f"Content: {doc_text}\n\n"
    
    if not result:
        return "No documents found in the database."
    
    return result

def delete_document(doc_id: str):
    success = vector_db.delete(doc_id)
    if success:
        if doc_id in document_store:
            del document_store[doc_id]
        return f"Document '{doc_id}' deleted successfully!"
    else:
        return f"Document '{doc_id}' not found in the database."

def get_database_stats():
    metrics = vector_db.get_metrics()
    stats = f"Total Vectors: {metrics.total_vectors}\n"
    stats += f"Memory Usage: {metrics.memory_usage:.2f} MB\n"
    stats += f"Cache Hit Ratio: {metrics.cache_hits/(metrics.cache_hits + metrics.cache_misses) if (metrics.cache_hits + metrics.cache_misses) > 0 else 0:.2f}\n"
    stats += f"Cache Size: {metrics.cache_size/1024/1024:.2f} MB\n"
    return stats

def create_gradio_interface():
    with gr.Blocks(title="DuckDBVectorDatabase MCP Demo") as interface:
        gr.Markdown("# DuckDBVectorDatabase MCP Demo")
        gr.Markdown("This demo showcases the DuckDBVectorDatabase with a simple interface for semantic search.")
        
        with gr.Tab("Search Documents"):
            with gr.Row():
                with gr.Column():
                    search_input = gr.Textbox(label="Enter text to search for similar documents", lines=5)
                    num_results = gr.Slider(minimum=1, maximum=10, value=3, step=1, label="Number of results")
                    search_method = gr.Dropdown(choices=["exact", "approximate", "lsh", "hnsw"], value="hnsw", label="Search Method")
                    search_button = gr.Button("Search")
                
                with gr.Column():
                    search_output = gr.Textbox(label="Search Results", lines=10)
        
        with gr.Tab("Manage Documents"):
            with gr.Row():
                with gr.Column():
                    doc_id = gr.Textbox(label="Document ID")
                    doc_text = gr.Textbox(label="Document Text", lines=5)
                    add_button = gr.Button("Add Document")
                    add_output = gr.Textbox(label="Result", lines=2)
                
                with gr.Column():
                    delete_id = gr.Textbox(label="Document ID to Delete")
                    delete_button = gr.Button("Delete Document")
                    delete_output = gr.Textbox(label="Result", lines=2)
        
        with gr.Tab("View Documents"):
            list_button = gr.Button("List All Documents")
            doc_list = gr.Textbox(label="Documents", lines=15)
        
        with gr.Tab("Database Stats"):
            stats_button = gr.Button("Get Database Statistics")
            stats_output = gr.Textbox(label="Statistics", lines=6)
        
        search_button.click(search_similar_docs, inputs=[search_input, num_results, search_method], outputs=search_output)
        add_button.click(add_document, inputs=[doc_id, doc_text], outputs=add_output)
        delete_button.click(delete_document, inputs=[delete_id], outputs=delete_output)
        list_button.click(list_documents, inputs=[], outputs=doc_list)
        stats_button.click(get_database_stats, inputs=[], outputs=stats_output)
        
    return interface

@app.on_event("startup")
def startup_event():
    init_sample_data()
    print("Sample data initialized")

gradio_app = create_gradio_interface()
app = gr.mount_gradio_app(app, gradio_app, path="/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port) 