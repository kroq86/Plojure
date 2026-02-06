# DuckDB Vector Database with MCP

Vector database implementation using DuckDB with a simple Gradio interface for interaction.

## Features

- **Fast Vector Storage**: Efficiently store and retrieve embedding vectors using DuckDB as the backend
- **Multiple Search Methods**: 
  - Exact search (brute force)
  - Approximate search (random sampling)
  - LSH (Locality Sensitive Hashing) for faster approximate search
- **Interactive UI**: Simple Gradio interface to:
  - Search for similar documents
  - Add new documents
  - Manage and view existing documents
  - Monitor database statistics
- **Simple URL-based API**: Easily search using just a URL parameter
- **Agent-Ready**: Simple HTTP endpoints make it easy to integrate with AI agents and tools

## About the Database

The DuckDB Vector Database provides:

- Fast in-memory vector storage with disk persistence
- Efficient caching system
- Multiple similarity metrics (cosine, euclidean, dot product)
- Partition-based storage for scalability
- LSH indexing for faster approximate searches

## Related MCP Implementation

The full project includes a separate MCP integration that allows AI systems like Claude to:

1. Store and retrieve embeddings
2. Perform semantic searches
3. Manage knowledge bases
4. Track performance metrics

The MCP implementation is available in the GitHub repository and can be installed in Claude Desktop using the MCP CLI tools.

## Usage

### Web Interface

The interface provides several tabs:

1. **Search Documents**: Enter text to find semantically similar documents
2. **Manage Documents**: Add new documents or delete existing ones
3. **View Documents**: See all documents currently stored in the database
4. **Database Stats**: View performance metrics of the vector database

### Simple URL-based Search

For easy integration with other tools, you can use the following URL pattern:

```
http://localhost:7860/search_text?query=your_search_text
```

Example:
```
http://localhost:7860/search_text?query=python
```

Additional parameters:
- `k`: Number of results to return (default: 3)
- `method`: Search method to use (default: "hnsw", options: "exact", "approximate", "lsh", "hnsw")

Example with all parameters:
```
http://localhost:7860/search_text?query=python&k=5&method=exact
```

### REST API

The application also provides a full REST API for more advanced interactions:

- `GET /vectors`: List all vectors
- `POST /vectors/{key}`: Insert a vector with the given key
- `DELETE /vectors/{key}`: Delete a vector
- `POST /search`: Perform a search with a vector payload
- `GET /metrics`: Get database metrics

## Integration with AI Agents

This vector database is ideal for use with AI agents thanks to its simple REST API and URL-based search.

### For Agent Tools

The system can be integrated with AI agents in various ways:

1. **Knowledge Retrieval**: Agents can store and retrieve information using semantic search
   ```python
   import requests
   
   def search_knowledge(query, k=3):
       response = requests.get(f"http://localhost:7860/search_text?query={query}&k={k}")
       return response.json()
   ```

2. **Memory Systems**: Agents can maintain context and recall relevant information
   ```python
   def store_memory(key, text_content):
       requests.post(f"http://localhost:7860/vectors/{key}", json={"text": text_content})
       
   def recall_relevant_memories(query):
       return requests.get(f"http://localhost:7860/search_text?query={query}&k=5").json()
   ```

3. **Document QA**: Using the vector DB for document retrieval in RAG systems
   ```python
   def retrieve_documents(query):
       results = requests.get(f"http://localhost:7860/search_text?query={query}").json()
       return [doc["document"] for doc in results["results"]]
   ```

The simple URL-based search makes it particularly easy to call from any programming language, so agents written in JavaScript, Python, or any other language can use the database without any special libraries.

## Running Locally

### With Docker

Build the Docker image:
```bash
docker build -t mcpvectordb .
```

Run the container:
```bash
docker run -p 7860:7860 mcpvectordb
```

Then access the UI at http://localhost:7860 or use the API endpoints.

## Technical Details

The implementation uses:

- **DuckDB**: Embedded database optimized for analytics
- **NumPy**: For efficient vector operations
- **Gradio**: For the user interface
- **FastAPI**: For the API backend
- **Python Threading**: For parallel search operations

## Source Code

The full source code is available on GitHub with extensive documentation. This demo is part of a larger project that includes MCP server implementations for integrating with AI systems.

## Acknowledgements

This project builds on research in vector databases, nearest neighbor search algorithms, and the Model Context Protocol.

---

Created by [Kirill Ostapenko](https://github.com/kroq-gar78) 
