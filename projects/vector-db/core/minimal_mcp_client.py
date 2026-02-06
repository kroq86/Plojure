#!/usr/bin/env python3
"""
Minimal MCP Vector Database Client

This is a stripped-down client that just demonstrates a single vector operation
to avoid complex error handling and debugging.
"""

import os
import sys
import json
import numpy as np
import asyncio
from pathlib import Path

try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
except ImportError:
    print("MCP SDK not found. Please install it with 'pip install mcp'")
    sys.exit(1)

SERVER_SCRIPT = Path(__file__).parent / "mcp_vector_server.py"

def generate_random_vector(dim: int = 10):
    """Generate a random unit vector"""
    vec = np.random.normal(0, 1, dim)
    return (vec / np.linalg.norm(vec)).tolist()

async def run_mcp_client():
    """Run a simple MCP client for vector operations"""
    # Use sys.executable to get the current Python interpreter path
    python_path = sys.executable
    
    # Create server parameters
    server_params = StdioServerParameters(
        command=python_path,
        args=[str(SERVER_SCRIPT)],
        env={"VECTOR_DB_PATH": ":memory:"}
    )
    
    print("Starting MCP client session...")
    print(f"Running: {python_path} {SERVER_SCRIPT}")
    
    try:
        async with stdio_client(server_params) as (read, write):
            try:
                async with ClientSession(read, write) as session:
                    # Initialize
                    await session.initialize()
                    
                    # Insert a test vector
                    key = "test-vector"
                    vector = generate_random_vector()
                    
                    print(f"\nInserting test vector with key '{key}'...")
                    try:
                        result = await session.call_tool("insert_vector", {"key": key, "vector": vector})
                        print(f"Result: {result}")
                    except Exception as e:
                        print(f"Error inserting vector: {e}")
            except Exception as e:
                print(f"Session error: {e}")
    except Exception as e:
        print(f"Client error: {e}")
    
    print("\nMCP client session completed.")

if __name__ == "__main__":
    asyncio.run(run_mcp_client()) 