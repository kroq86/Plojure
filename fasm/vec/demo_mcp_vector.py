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
import shlex
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
    "artificial_intelligence",
    "machine_learning",
    "neural_networks", 
    "computer_vision",
    "natural_language_processing",
    "reinforcement_learning",
    "deep_learning",
    "robotics",
    "data_science",
    "big_data"
]

SERVER_SCRIPT = Path(__file__).parent / "mcp_vector_server.py"

def generate_random_vector(dim: int = 10) -> List[float]:
    """Generate a random unit vector of the specified dimension"""
    vec = np.random.normal(0, 1, dim)
    return (vec / np.linalg.norm(vec)).tolist()

def create_concept_vectors(concepts: List[str], dim: int = 10) -> Dict[str, List[float]]:
    """Create random vectors for each concept (in a real app, these would be meaningful embeddings)"""
    return {f"concept:{concept}": generate_random_vector(dim) for concept in concepts}

def extract_text_from_tool_result(result):
    """Extract text content from a CallToolResult object"""
    if hasattr(result, 'content') and result.content:
        for content_item in result.content:
            if hasattr(content_item, 'text') and content_item.text:
                return content_item.text
    return None

async def run_mcp_client():
    """Run the MCP client to interact with the vector database server"""
    # Use sys.executable to get the current Python interpreter path
    python_path = sys.executable
    
    # Create server parameters with command and args separated
    server_params = StdioServerParameters(
        command=python_path,
        args=[str(SERVER_SCRIPT)],
        env={"VECTOR_DB_PATH": ":memory:"}
    )
    
    print("Starting MCP client session...")
    print(f"Running: {python_path} {SERVER_SCRIPT}")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\n--- Available Tools ---")
            try:
                tools = await session.list_tools()
                if hasattr(tools, 'tools'):
                    for tool in tools.tools:
                        print(f"Tool: {tool.name} - {tool.description}")
            except Exception as e:
                print(f"Error listing tools: {str(e)}")
            
            print("\n--- Creating Test Vectors ---")
            vectors = create_concept_vectors(SAMPLE_CONCEPTS)
            for key, vector in vectors.items():
                try:
                    result = await session.call_tool("insert_vector", {"key": key, "vector": vector})
                    text_content = extract_text_from_tool_result(result)
                    if text_content:
                        result_json = json.loads(text_content)
                        print(f"Inserted {key}: {result_json.get('status', 'error')}")
                    else:
                        print(f"Inserted {key}: No text content in response")
                except Exception as e:
                    print(f"Error inserting {key}: {str(e)}")
            
            print("\n--- Database Metrics ---")
            try:
                metrics_result = await session.call_tool("get_metrics", {})
                text_content = extract_text_from_tool_result(metrics_result)
                if text_content:
                    metrics = json.loads(text_content)
                    print(f"Total vectors: {metrics.get('total_vectors', 'N/A')}")
                    print(f"Memory usage: {metrics.get('memory_usage_mb', 'N/A')} MB")
                else:
                    print("No metrics text content in response")
            except Exception as e:
                print(f"Error getting metrics: {str(e)}")
            
            print("\n--- Fetching Vector Resource ---")
            try:
                sample_key = f"concept:{SAMPLE_CONCEPTS[0]}"
                # URL encode the key to make it a valid URL
                safe_key = sample_key.replace(":", "%3A")
                vector_resource = await session.read_resource(f"vector://{safe_key}")
                if hasattr(vector_resource, 'content'):
                    content_text = vector_resource.content
                    vector_data = json.loads(content_text)
                    print(f"Retrieved vector for '{sample_key}':")
                    print(f"Dimensions: {vector_data.get('dimensions', 'N/A')}")
                else:
                    print(f"Resource has no content attribute: {vector_resource}")
            except Exception as e:
                print(f"Error fetching vector: {str(e)}")
            
            print("\n--- Performing Vector Search ---")
            try:
                query_vector = generate_random_vector()
                search_result = await session.call_tool(
                    "vector_search", 
                    {"query_vector": query_vector, "k": 3, "method": "exact"}
                )
                text_content = extract_text_from_tool_result(search_result)
                if text_content:
                    search_data = json.loads(text_content)
                    
                    print("Search results:")
                    for item in search_data.get("results", []):
                        print(f"Key: {item.get('key')}, Similarity: {item.get('similarity'):.4f}")
                else:
                    print("No search results text content in response")
            except Exception as e:
                print(f"Error searching vectors: {str(e)}")
            
            print("\n--- Performance Metrics Resource ---")
            try:
                metrics_resource = await session.read_resource("metrics://performance")
                if hasattr(metrics_resource, 'content'):
                    print(metrics_resource.content)
                else:
                    print(f"Resource has no content attribute: {metrics_resource}")
            except Exception as e:
                print(f"Error getting performance metrics: {str(e)}")
            
            print("\n--- Available Prompts ---")
            try:
                prompts = await session.list_prompts()
                if hasattr(prompts, 'prompts'):
                    for prompt in prompts.prompts:
                        print(f"Prompt: {prompt.name} - {prompt.description}")
            except Exception as e:
                print(f"Error listing prompts: {str(e)}")
            
            print("\n--- Deleting a Vector ---")
            try:
                delete_key = f"concept:{SAMPLE_CONCEPTS[-1]}"
                delete_result = await session.call_tool("delete_vector", {"key": delete_key})
                text_content = extract_text_from_tool_result(delete_result)
                if text_content:
                    delete_data = json.loads(text_content)
                    print(f"Deleted '{delete_key}': {delete_data.get('status', 'error')}")
                else:
                    print(f"Deleted '{delete_key}': No text content in response")
            except Exception as e:
                print(f"Error deleting vector: {str(e)}")
            
            print("\nMCP client session completed.")

if __name__ == "__main__":
    asyncio.run(run_mcp_client()) 