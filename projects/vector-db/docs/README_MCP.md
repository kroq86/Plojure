# DuckDBVectorDatabase MCP Integration

This document describes the integration of DuckDBVectorDatabase with the Model Context Protocol (MCP), allowing you to use the vector database capabilities with Claude and other MCP-compatible systems.

## Components

The MCP integration consists of several key components:

1. **`mcp_vector_server.py`**: The MCP server that exposes DuckDBVectorDatabase functionality through the Model Context Protocol.
2. **`minimal_mcp_client.py`**: A minimal client demonstrating basic vector insertion.
3. **`demo_mcp_vector.py`**: A comprehensive demo showcasing all available vector operations.
4. **`duckdb_vec.py`**: The core vector database implementation using DuckDB.

## Quick Start

### 1. Test with the Minimal Client

Run the minimal client to verify basic functionality:

```bash
python minimal_mcp_client.py
```

If successful, you should see a message confirming that a test vector was inserted.

### 2. Explore Full Functionality

Run the comprehensive demo to see all available operations:

```bash
python demo_mcp_vector.py
```

This demo showcases:
- Inserting concept vectors
- Retrieving database metrics
- Fetching vector resources by key
- Performing vector similarity searches
- Deleting vectors

### 3. Install in Claude Desktop

Install the MCP server in Claude Desktop:

```bash
# Install MCP CLI tools if needed
pip install "mcp[cli]"

# Install the server
mcp install mcp_vector_server.py --name "Vector Database"
```

## Available MCP Tools

The server exposes the following tools:

1. **`insert_vector`**: Insert a vector with a key
   - Parameters: `key` (string), `vector` (list of floats)
   - Returns: Confirmation message

2. **`delete_vector`**: Delete a vector by key
   - Parameters: `key` (string)
   - Returns: Confirmation message

3. **`get_vector`**: Retrieve a vector by key
   - Parameters: `key` (string)
   - Returns: Vector data

4. **`vector_search`**: Search for similar vectors
   - Parameters: 
     - `query_vector` (list of floats) or `query_key` (string)
     - `method` (string): "exact", "hnsw", or "random"
     - `similarity` (string): "cosine", "euclidean", or "dot_product"
     - `k` (int): number of results
   - Returns: Similar vectors with similarity scores

5. **`get_metrics`**: Get database performance metrics
   - Returns: Current metrics

## Advanced Configuration

The MCP server supports several environment variables:

- `VECTOR_DB_PATH`: Path to a persistent database file (default: in-memory)
- `INDEX_METHOD`: Default indexing method (default: "hnsw")
- `DEFAULT_SIMILARITY`: Default similarity metric (default: "cosine")
- `VECTOR_DIMENSION`: Default dimension for vectors (default: 1536)

Set these when installing the server:

```bash
mcp install mcp_vector_server.py -e VECTOR_DB_PATH=/path/to/vectors.db
```

## Development Notes

### Contributing

To extend the functionality:

1. Update `duckdb_vec.py` with new database features
2. Add corresponding methods to `mcp_vector_server.py`
3. Update the demo scripts to showcase new functionality
4. Update documentation

### Troubleshooting MCP Integration

- Ensure proper error handling of `CallToolResult` objects
- Check the type of objects returned by MCP tools
- Verify vector formats are consistent (normalized if using cosine similarity)
- Use proper URL encoding for keys with special characters

### Performance Considerations

For large vector collections:
- Use HNSW indexing for faster approximate search
- Consider using a persistent database file
- Pre-normalize vectors if using cosine similarity frequently 