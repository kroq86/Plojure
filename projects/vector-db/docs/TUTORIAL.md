# DuckDBVectorDatabase Tutorial

This tutorial guides you through setting up and using the DuckDBVectorDatabase with Claude Desktop for semantic search and vector operations.

## Setup Instructions

### Step 1: Install Dependencies

```bash
# Install required Python packages
pip install numpy duckdb pydantic

# Install MCP CLI tools
pip install "mcp[cli]"
```

### Step 2: Install the MCP Server

```bash
# Navigate to the directory containing the MCP server
cd /path/to/

# Install the server in Claude Desktop
mcp install mcp_vector_server.py --name "Vector Database"
```

### Step 3: Verify the Installation

1. Open Claude Desktop
2. Click on the "Servers" icon in the sidebar
3. Confirm that "Vector Database" appears in the list of servers

## Basic Usage Tutorial

### Example 1: Creating a Knowledge Base

In this example, we'll create a simple knowledge base by storing document embeddings:

1. Open Claude Desktop and start a new conversation
2. Ask Claude to help you create document embeddings:

```
I want to create a knowledge base using the Vector Database. I have these three short documents:

1. "Python is a high-level programming language known for its readability and versatility."
2. "Machine learning models require training data to learn patterns and make predictions."
3. "Database indexing improves query performance by creating data structures that speed up data retrieval."

Can you create embeddings for these documents and store them in the Vector Database?
```

Claude will:
- Generate embeddings for each document
- Use the `insert_vector` tool to store them with appropriate keys
- Confirm when the documents have been stored

### Example 2: Semantic Search

Now, search for documents related to a concept:

```
Using the Vector Database, can you find documents in my knowledge base that are most related to "computer programming"?
```

Claude will:
- Create an embedding for "computer programming"
- Use the `vector_search` tool to find similar vectors
- Return the matching documents, ranked by relevance

### Example 3: Managing Vectors

You can also manage your vectors directly:

```
Can you show me all the vectors currently stored in the Vector Database and then delete the one about databases?
```

Claude will:
- Use tools to list the available vectors
- Delete the specified vector
- Confirm the deletion

## Advanced Usage

### Creating a Persistent Database

By default, the database is stored in memory. To create a persistent database:

```bash
# Uninstall the existing server
mcp uninstall "Vector Database"

# Reinstall with a persistent database path
mcp install mcp_vector_server.py --name "Vector Database" -e VECTOR_DB_PATH=/path/to/your/vectors.db
```

### Customizing Search Parameters

You can customize your searches with different parameters:

```
Using the Vector Database, find documents similar to "artificial intelligence" using Euclidean distance instead of cosine similarity, and return the top 2 results.
```

Claude will use the appropriate parameters for the vector_search tool.

### Working with Custom Vectors

You can work with your own custom vectors:

```
I have a custom embedding vector [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]. Can you store this in the Vector Database with the key "custom_vector_1"?
```

## Troubleshooting

### Common Issues

1. **Server Not Found**: If Claude can't find the Vector Database server, try reinstalling it.

2. **Dimension Mismatch**: Ensure all vectors have the same dimension. The default is 1536.

3. **Key Errors**: If you get errors about keys not found, check that you're using the correct key names.

4. **Performance Issues**: For large databases, try using the HNSW indexing method for faster search.

### Getting Help

For more detailed information:

1. Refer to the `README_MCP.md` file for comprehensive documentation
2. Try the demo script to see examples of all operations:
   ```bash
   python demo_mcp_vector.py
   ```