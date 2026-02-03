Slide 1 — Title
From Assembly to Answers: Vector DB Internals and Why Choice Still Matters

Slide 2 — The pipeline
Vectors go from embeddings (e.g. sentence-transformers, OpenAI) into a vector store, then into indexed graphs or LSH for approximate search, and finally into RAG or semantic search. Every step—embedding model, index type, and similarity metric—changes speed, recall, and cost.

Slide 3 — Assembly-level guts
Critical hot path: dot product and vector norm. I implement them in x86-64 assembly (FASM), expose them via a C wrapper, and call from Python with ctypes. That’s the asm→C→Python chain. Same idea applies when you add SIMD: you own the inner loop that runs billions of times.

Slide 4 — Why go that low?
Python/NumPy hide the cost. One similarity call is cheap; millions aren’t. Hand-written asm (and SIMD) gives predictable latency and throughput when you scale. Trade-off: portability and maintenance. I use a fallback to pure Python when the compiled library isn’t available.

Slide 5 — Index choice: exact vs approximate
Exact search: scan all vectors, sort by similarity. Correct but O(n). Approximate: LSH buckets or HNSW-style graphs reduce comparisons. I use LSH (banded hashes) for approximate and DuckDB for storage. Trade-off: recall and tuning effort vs query speed and RAM.

Slide 6 — Similarity metrics: cosine, Euclidean, dot product
Cosine: normalized, good for text. Euclidean: geometric distance. Dot product: unbounded, good when norms matter (e.g. relevance). The same assembly primitives (dot, norm) feed all of them. Choice of metric changes ranking and system behavior—no single default fits every use case.

Slide 7 — Hybrid search: vectors + SQL
Vectors live in DuckDB; metadata (category, date) in tables. Hybrid query: filter by metadata in SQL, then run similarity search on the filtered set. One interface for “similar to this + category = X + date &gt; Y”. That’s what the hybrid-analytics layer does: VectorDB + DuckDB + optional parallel batch search.

Slide 8 — Real outcomes: speed, RAM, recall
Query speed: exact scales with dataset size; LSH/approximate stays flatter. RAM: caching vectors in-process vs reading from DuckDB; we use an LRU cache with eviction. Recall: approximate methods can miss neighbors; exact doesn’t. I benchmark sequential vs parallel and document throughput (e.g. documents per second) so you can reason about latency and cost.

Slide 9 — RAG and integration
Vector DB backs RAG: retrieve top-k by similarity, then pass chunks to the LLM. Limits nobody likes to spell out: bad retrieval → hallucination; wrong metric → wrong ranking; no metadata filters → irrelevant context. Fits into LangChain (retrievers), MCP (tools/resources), or AWS (embeddings + your index). Choice of DB and index affects reliability as much as it affects speed.

Slide 10 — Why choice still matters
No single vector DB or index is best for every case. Assembly/SIMD vs Python, exact vs LSH/HNSW, cosine vs Euclidean vs dot, hybrid vs pure vector—each choice trades off speed, recall, RAM, and integration cost. Understanding the stack from asm to API is what lets you pick the right trade-offs your AI meeting product.
