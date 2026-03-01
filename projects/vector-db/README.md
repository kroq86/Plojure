# Vector DB MCP

Assembly-accelerated MCP server for vector search, repository indexing, symbol lookup, and semantic code retrieval.

The project packages a Linux-only DuckDB-backed vector database with native similarity kernels built inside the container from `dot_product.asm` and `wrapper.c`. It can run as:

- a local `stdio` MCP server inside an OCI image
- a persistent `streamable-http` MCP server for Codex and other MCP clients

## What It Does

- indexes repositories into searchable code/document chunks
- supports `refresh_path` for fast incremental updates
- exposes `search_symbols`, `semantic_search_code`, `search_docs`, and `ask_repository_context`
- keeps vector data in DuckDB and can persist data under `/data`
- loads assembly-backed native scoring when `USE_ASM=1`

## Runtime Notes

- default OCI transport is `stdio`
- persistent local server mode uses `streamable-http`
- default persistent DB path is `/data/vectors.duckdb`
- embedding cache is stored under `/models`

## Local Build

```bash
docker build --platform linux/amd64 -t vector-db-mcp-batch .
```

## Persistent Local Server

```bash
./scripts/restart_mcp_server.sh
```

This starts the container from `docker-compose.mcp.yml` and waits until `http://127.0.0.1:8765/ready` reports `ready: true`.

## Codex MCP

Current local Codex setup points at:

```toml
[mcp_servers.vector-db]
url = "http://127.0.0.1:8765/mcp"
```

## OCI / Registry

The intended public OCI package is:

```text
ghcr.io/kroq86/vector-db-mcp:0.1.0
```

Registry metadata is defined in `server.json`.

## Publishing Outline

1. Build and push the OCI image to GHCR.
2. Authenticate with `mcp-publisher`.
3. Publish `server.json` to the MCP Registry.

## Status

The current implementation has real assembly-backed native scoring enabled in the running container, but the full end-to-end system is still a hybrid of Python, DuckDB, embeddings, and native similarity kernels.
