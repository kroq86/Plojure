# MCP Vector Database Integration

This integration allows you to expose your DuckDBVectorDatabase through the Model Context Protocol (MCP), making it available to LLM applications like Claude Desktop.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. It standardizes how applications provide context to LLMs.

## Files in this Integration

- `mcp_vector_server.py` - The MCP server that wraps DuckDBVectorDatabase
- `demo_mcp_vector.py` - A demonstration script showing how to use the MCP server

## Features

This MCP server exposes the following capabilities:

### Tools (for LLMs to use)
- `vector_search` - Search for similar vectors in the database
- `insert_vector` - Insert a vector into the database
- `delete_vector` - Delete a vector from the database
- `get_metrics` - Get performance metrics from the database

### Resources (for context)
- `vector://{key}` - Get specific vector data by key
- `metrics://performance` - Get database performance metrics

### Prompts (for users)
- `search_vectors_prompt` - Creates a prompt template for vector search

## Getting Started

1. Install the MCP SDK:
   ```
   pip install mcp
   ```

2. Run the demo to see it in action:
   ```
   python demo_mcp_vector.py
   ```

3. Use with Claude Desktop:
   ```
   mcp install /path/to/mcp_vector_server.py
   ```

## Integration with Applications

This MCP server can be used with any MCP-compatible client, including:

- Claude Desktop
- Custom applications using the MCP client SDK
- Development environments like Zed, Replit, etc.

## Example Use Case: Semantic Search

1. Store document embeddings in the vector database
2. Connect Claude Desktop to your MCP server
3. Ask Claude to find semantically similar documents
4. Claude will use the vector_search tool to find matches

## Extending the Integration

You can extend this integration by:

1. Adding more tools for additional vector operations
2. Supporting more complex vector operations (clustering, etc.)
3. Creating specialized prompts for specific use cases
4. Adding authentication and access control

## Requirements

- Python 3.7+
- MCP SDK (`pip install mcp`)
- NumPy 