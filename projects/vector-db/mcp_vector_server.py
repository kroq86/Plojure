from mcp.server.fastmcp import FastMCP
from typing import List
import json
import os
import threading
import time

from starlette.responses import JSONResponse

from duckdb_vec import DuckDBVectorDatabase

class MCPVectorDatabaseServer:
    """
    A Model Context Protocol (MCP) server that wraps DuckDBVectorDatabase
    and exposes vector search and storage functionality.
    """
    
    def __init__(self, db_path: str = ':memory:', server_name: str = "VectorDBServer"):
        self.vector_db = DuckDBVectorDatabase(db_path)
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        port = int(os.environ.get("MCP_PORT", "8000"))
        mount_path = os.environ.get("MCP_MOUNT_PATH", "/")
        streamable_http_path = os.environ.get("MCP_STREAMABLE_HTTP_PATH", "/mcp")
        self._write_lock = threading.RLock()
        self._started_at = time.time()
        self._ready = False
        self.mcp = FastMCP(
            server_name,
            host=host,
            port=port,
            mount_path=mount_path,
            streamable_http_path=streamable_http_path,
        )
        
        self._register_tools()
        self._register_resources()
        self._register_prompts()
        self._register_http_routes()
        self._ready = True

    def _server_status(self) -> dict:
        db_ok = False
        error = None
        try:
            self.vector_db.conn.execute("SELECT 1").fetchone()
            db_ok = True
        except Exception as exc:
            error = str(exc)

        return {
            "status": "ok" if db_ok else "error",
            "ready": self._ready and db_ok,
            "db_ok": db_ok,
            "uptime_seconds": round(time.time() - self._started_at, 3),
            "runtime": self.vector_db.get_runtime_info(),
            "error": error,
        }
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.mcp.tool()
        def vector_search(query_vector: List[float], k: int = 10, method: str = "exact") -> str:
            """
            Search for similar vectors in the database
            
            Args:
                query_vector: The vector to search for
                k: Number of results to return
                method: Search method ('exact', 'approximate', or 'lsh')
            
            Returns:
                JSON string with search results
            """
            valid_methods = ["exact", "approximate", "lsh"]
            if method not in valid_methods:
                return json.dumps({"error": f"Invalid method. Choose from: {', '.join(valid_methods)}"})

            try:
                results = self.vector_db.search(query_vector, k, method)
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
                with self._write_lock:
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
                with self._write_lock:
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
                    "cache_size_bytes": metrics.cache_size,
                    "runtime": self.vector_db.get_runtime_info()
                })
            except Exception as e:
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        def upsert_document_chunk(
            key: str,
            content: str,
            path: str,
            start_line: int,
            end_line: int,
        ) -> str:
            """
            Insert or update a repository/document chunk and its derived embedding.
            """
            try:
                with self._write_lock:
                    self.vector_db.upsert_document_chunk(
                        key=key,
                        content=content,
                        path=path,
                        start_line=start_line,
                        end_line=end_line,
                    )
                return json.dumps({"status": "success", "key": key, "path": path})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        def index_repository(
            root_path: str,
            chunk_size_lines: int = 40,
            overlap_lines: int = 10,
        ) -> str:
            """
            Index source files in a repository into searchable document chunks.
            """
            try:
                with self._write_lock:
                    result = self.vector_db.index_repository(
                        root_path=root_path,
                        chunk_size_lines=chunk_size_lines,
                        overlap_lines=overlap_lines,
                    )
                return json.dumps({"status": "success", **result})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        def index_workspace(
            workspace_root: str = "/workspace",
            chunk_size_lines: int = 40,
            overlap_lines: int = 10,
        ) -> str:
            """
            Index a mounted workspace path for code and docs retrieval.
            """
            try:
                with self._write_lock:
                    result = self.vector_db.index_workspace(
                        workspace_root,
                        chunk_size_lines=chunk_size_lines,
                        overlap_lines=overlap_lines,
                    )
                return json.dumps({"status": "success", **result})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        def refresh_path(
            root_path: str,
            target_path: str,
            chunk_size_lines: int = 40,
            overlap_lines: int = 10,
        ) -> str:
            """
            Re-index a single file or subtree after changes.
            """
            try:
                with self._write_lock:
                    result = self.vector_db.refresh_path(
                        root_path=root_path,
                        target_path=target_path,
                        chunk_size_lines=chunk_size_lines,
                        overlap_lines=overlap_lines,
                    )
                return json.dumps({"status": "success", **result})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        def semantic_search_code(query: str, k: int = 5, method: str = "exact") -> str:
            """
            Search indexed repository/document chunks using deterministic text embeddings.
            """
            valid_methods = ["exact", "approximate", "lsh"]
            if method not in valid_methods:
                return json.dumps({"error": f"Invalid method. Choose from: {', '.join(valid_methods)}"})

            try:
                results = self.vector_db.search_document_chunks(query, k=k, method=method)
                return json.dumps({"results": results})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        def search_symbols(query: str, k: int = 5) -> str:
            """
            Search indexed chunks by declared symbol names with symbol-aware reranking.
            """
            try:
                results = self.vector_db.search_symbols(query, k=k)
                return json.dumps({"results": results})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        def search_docs(query: str, k: int = 5, method: str = "exact") -> str:
            """
            Search only documentation-like files among indexed chunks.
            """
            valid_methods = ["exact", "approximate", "lsh"]
            if method not in valid_methods:
                return json.dumps({"error": f"Invalid method. Choose from: {', '.join(valid_methods)}"})

            try:
                results = self.vector_db.search_docs(query, k=k, method=method)
                return json.dumps({"results": results})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        def ask_repository_context(question: str, k: int = 5, method: str = "exact") -> str:
            """
            Retrieve the most relevant repository chunks to ground an answer externally.
            """
            valid_methods = ["exact", "approximate", "lsh"]
            if method not in valid_methods:
                return json.dumps({"error": f"Invalid method. Choose from: {', '.join(valid_methods)}"})

            try:
                result = self.vector_db.ask_repository_context(question, k=k, method=method)
                return json.dumps(result)
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

        @self.mcp.resource("chunk://{key}")
        def get_document_chunk(key: str) -> str:
            chunk = self.vector_db.get_document_chunk(key)
            if chunk is None:
                return json.dumps({"error": f"Chunk with key {key} not found"})
            return json.dumps({
                "key": chunk.key,
                "path": chunk.path,
                "content": chunk.content,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "metadata": chunk.metadata,
            })

    def _register_http_routes(self):
        @self.mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
        async def health_check(request):
            return JSONResponse(self._server_status(), status_code=200)

        @self.mcp.custom_route("/ready", methods=["GET"], include_in_schema=False)
        async def ready_check(request):
            status = self._server_status()
            return JSONResponse(status, status_code=200 if status["ready"] else 503)
    
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
db_path = os.environ.get("VECTOR_DB_PATH", "/data/vectors.duckdb")
server = MCPVectorDatabaseServer(db_path)
mcp = server.get_server()  # This is what the MCP client will look for

# If run directly
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mount_path = os.environ.get("MCP_MOUNT_PATH")
    mcp.run(transport=transport, mount_path=mount_path)
