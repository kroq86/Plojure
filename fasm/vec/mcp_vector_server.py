from mcp.server.fastmcp import FastMCP
import numpy as np
from typing import List, Dict, Tuple, Optional, Literal
import json
import os
from pathlib import Path

from duckdb_vec import DuckDBVectorDatabase

class MCPVectorDatabaseServer:
    """
    A Model Context Protocol (MCP) server that wraps DuckDBVectorDatabase
    and exposes vector search and storage functionality.
    """
    
    def __init__(self, db_path: str = ':memory:', server_name: str = "VectorDBServer"):
        self.vector_db = DuckDBVectorDatabase(db_path)
        self.mcp = FastMCP(server_name)
        
        self._register_tools()
        self._register_resources()
        self._register_prompts()
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.mcp.tool()
        def vector_search(query_vector: List[float], k: int = 10, method: str = "hnsw") -> str:
            """
            Search for similar vectors in the database
            
            Args:
                query_vector: The vector to search for
                k: Number of results to return
                method: Search method ('exact', 'approximate', 'lsh', or 'hnsw')
            
            Returns:
                JSON string with search results
            """
            valid_methods = ["exact", "approximate", "lsh", "hnsw"]
            if method not in valid_methods:
                return json.dumps({"error": f"Invalid method. Choose from: {', '.join(valid_methods)}"})
            
            method_typed = method  # type: Literal["exact", "approximate", "lsh", "hnsw"]
            
            try:
                results = self.vector_db.search(query_vector, k, method_typed)
                return json.dumps({
                    "results": [{"key": key, "similarity": float(similarity)} for key, similarity in results]
                })
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        def insert_vector(key: str, vector: List[float]) -> str:
            """
            Insert a vector into the database
            
            Args:
                key: Unique identifier for the vector
                vector: The vector to insert
            
            Returns:
                Success message
            """
            try:
                self.vector_db.insert(key, vector)
                return json.dumps({"status": "success", "message": f"Vector inserted with key: {key}"})
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        def delete_vector(key: str) -> str:
            """
            Delete a vector from the database
            
            Args:
                key: Unique identifier for the vector to delete
            
            Returns:
                Success message
            """
            try:
                success = self.vector_db.delete(key)
                if success:
                    return json.dumps({"status": "success", "message": f"Vector with key {key} deleted"})
                else:
                    return json.dumps({"status": "error", "message": f"Vector with key {key} not found"})
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        def get_metrics() -> str:
            """
            Get performance metrics from the vector database
            
            Returns:
                JSON string with performance metrics
            """
            try:
                metrics = self.vector_db.get_metrics()
                return json.dumps({
                    "cache_hits": metrics.cache_hits,
                    "cache_misses": metrics.cache_misses,
                    "memory_usage_mb": metrics.memory_usage,
                    "total_vectors": metrics.total_vectors,
                    "total_dimensions": metrics.total_dimensions,
                    "cache_size_bytes": metrics.cache_size
                })
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    def _register_resources(self):
        """Register all MCP resources"""
        
        @self.mcp.resource("vector://{key}")
        def get_vector(key: str) -> str:
            """
            Get a vector by key
            
            Args:
                key: The vector key to retrieve
            
            Returns:
                JSON string with vector data
            """
            vector = self.vector_db.retrieve(key)
            if vector is None:
                return json.dumps({"error": f"Vector with key {key} not found"})
            return json.dumps({
                "key": key,
                "vector": vector,
                "dimensions": len(vector)
            })
        
        @self.mcp.resource("metrics://performance")
        def get_performance_metrics() -> str:
            """
            Get database performance metrics as a resource
            
            Returns:
                Formatted string with performance metrics
            """
            metrics = self.vector_db.get_metrics()
            return f"""
                Vector Database Performance Metrics:
                ===================================
                Total Vectors: {metrics.total_vectors}
                Memory Usage: {metrics.memory_usage:.2f} MB
                Cache Hit Ratio: {metrics.cache_hits/(metrics.cache_hits + metrics.cache_misses) if (metrics.cache_hits + metrics.cache_misses) > 0 else 0:.2f}
                Cache Size: {metrics.cache_size/1024/1024:.2f} MB
            """
    
    def _register_prompts(self):
        """Register all MCP prompts"""
        
        @self.mcp.prompt()
        def search_vectors_prompt(description: str) -> str:
            """
            Create a prompt for vector search
            
            Args:
                description: Text description of what to search for
            
            Returns:
                A prompt for the LLM to guide vector search
            """
            return f"""
            I need to search for vectors similar to the concept: "{description}"
            
            Please help me:
            1. Create an appropriate vector representation of this concept
            2. Search the vector database for similar items
            3. Analyze and explain the results
            """
    
    def get_server(self):
        """Return the FastMCP server instance"""
        return self.mcp


# Create a global server instance
db_path = os.environ.get("VECTOR_DB_PATH", ":memory:")
server = MCPVectorDatabaseServer(db_path)
mcp = server.get_server()  # This is what the MCP client will look for

# If run directly
if __name__ == "__main__":
    mcp.run()  # Use run() instead of start() 