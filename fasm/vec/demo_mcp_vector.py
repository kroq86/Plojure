#!/usr/bin/env python3
"""
Demo script for the MCP Vector Database Server

This script demonstrates:
1. Starting the MCP server in a separate process
2. Creating a sample database with test vectors
3. Connecting to the server using an MCP client
4. Performing various operations against the server
"""

import os
import sys
import time
import json
import random
import numpy as np
import subprocess
from typing import List, Dict, Any
import asyncio
from pathlib import Path

try:
    from mcp import types, ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
except ImportError:
    print("MCP SDK not found. Please install it with 'pip install mcp'")
    sys.exit(1)

SAMPLE_CONCEPTS = [
    "artificial intelligence",
    "machine learning",
    "neural networks", 
    "computer vision",
    "natural language processing",
    "reinforcement learning",
    "deep learning",
    "robotics",
    "data science",
    "big data"
]

SERVER_SCRIPT = Path(__file__).parent / "mcp_vector_server.py"

def generate_random_vector(dim: int = 10) -> List[float]:
    """Generate a random unit vector of the specified dimension"""
    vec = np.random.normal(0, 1, dim)
    return (vec / np.linalg.norm(vec)).tolist()

def create_concept_vectors(concepts: List[str], dim: int = 10) -> Dict[str, List[float]]:
    """Create random vectors for each concept (in a real app, these would be meaningful embeddings)"""
    return {f"concept:{concept}": generate_random_vector(dim) for concept in concepts}

async def run_mcp_client():
    """Run the MCP client to interact with the vector database server"""
    server_params = StdioServerParameters(
        cmd=["python", str(SERVER_SCRIPT)],
        env={"VECTOR_DB_PATH": ":memory:"}
    )
    
    print("Starting MCP client session...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\n--- Available Tools ---")
            tools = await session.list_tools()
            for tool in tools:
                print(f"Tool: {tool.name} - {tool.description}")
            
            print("\n--- Creating Test Vectors ---")
            vectors = create_concept_vectors(SAMPLE_CONCEPTS)
            for key, vector in vectors.items():
                result = await session.call_tool("insert_vector", {"key": key, "vector": vector})
                result_json = json.loads(result)
                print(f"Inserted {key}: {result_json.get('status', 'error')}")
            
            print("\n--- Database Metrics ---")
            metrics_result = await session.call_tool("get_metrics", {})
            metrics = json.loads(metrics_result)
            print(f"Total vectors: {metrics.get('total_vectors', 'N/A')}")
            print(f"Memory usage: {metrics.get('memory_usage_mb', 'N/A')} MB")
            
            print("\n--- Fetching Vector Resource ---")
            sample_key = f"concept:{SAMPLE_CONCEPTS[0]}"
            vector_resource, _ = await session.read_resource(f"vector://{sample_key}")
            vector_data = json.loads(vector_resource)
            print(f"Retrieved vector for '{sample_key}':")
            print(f"Dimensions: {vector_data.get('dimensions', 'N/A')}")
            
            print("\n--- Performing Vector Search ---")
            query_vector = generate_random_vector()
            search_result = await session.call_tool(
                "vector_search", 
                {"query_vector": query_vector, "k": 3, "method": "exact"}
            )
            search_data = json.loads(search_result)
            
            print("Search results:")
            for item in search_data.get("results", []):
                print(f"Key: {item.get('key')}, Similarity: {item.get('similarity'):.4f}")
            
            print("\n--- Performance Metrics Resource ---")
            metrics_resource, _ = await session.read_resource("metrics://performance")
            print(metrics_resource)
            
            print("\n--- Available Prompts ---")
            prompts = await session.list_prompts()
            for prompt in prompts:
                print(f"Prompt: {prompt.name} - {prompt.description}")
            
            print("\n--- Deleting a Vector ---")
            delete_key = f"concept:{SAMPLE_CONCEPTS[-1]}"
            delete_result = await session.call_tool("delete_vector", {"key": delete_key})
            delete_data = json.loads(delete_result)
            print(f"Deleted '{delete_key}': {delete_data.get('status', 'error')}")
            
            print("\nMCP client session completed.")

if __name__ == "__main__":
    asyncio.run(run_mcp_client()) 