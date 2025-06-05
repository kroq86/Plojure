# Hybrid Analytics Platform

**Brief Description**

The Hybrid Analytics Platform combines vector search (semantic search using embeddings) and classic SQL analytics within a single solution. This enables users to quickly find similar objects (such as texts, images, or products) and simultaneously analyze metadata using a familiar SQL interface.

**Who Needs This Platform**

- Data Analysts: For pattern detection, report generation, trend analysis, and data filtering.
- Data Scientists: To integrate vector search into ML pipelines, recommendation systems, and cluster analysis.
- Researchers: For semantic search across large datasets.

**Key Features**

- Hybrid Queries: Perform semantic similarity search and metadata filtering (e.g., by category, date) within a single SQL query.
- Assembler Optimization: Critical vector operations (similarity, dot product, Euclidean distance) are implemented in assembler for maximum speed.
- Multiprocessing: Automatic parallel processing of large datasets.
- DuckDB Integration: Uses an analytical database for storing vectors and running analytical queries.
- Automatic Fallback: If assembler code is unavailable, an optimized Python implementation is used.

**Usage Examples**

- For Analysts:
  - News Data Analysis: Search for articles similar to a given text, filter by category and date, and analyze semantic similarity trends over time.
  - Category Statistics: Compare average and maximum similarity across different topics.
- For Data Scientists:
  - Recommendation Systems: Find similar products or documents using vector queries.
  - Cluster Analysis: Group objects by semantic similarity.
  - A/B Testing: Compare different similarity metrics (cosine, Euclidean).

**Performance**

- Full demo (1,865 documents) completes in 8 seconds.
- Overall throughput: 233 documents per second.
- 100% accuracy in parallel computations.
- Automatic scaling based on load and data size.

**Technical Features**

- Unified SQL interface for both vectors and metadata.
- Multiple similarity metrics: cosine, Euclidean, dot product.
- Automatic chunk size optimization for multiprocessing.
- Simple integration with existing ML pipelines.

**Quick Start**

- `./install.sh`: Install dependencies
- `./run.sh`: Main demonstration
- `./run.sh parallel`: Multiprocessing demonstration
- `./run.sh benchmark`: Performance benchmarking

**Demonstration for Analysts**

- 500 news articles created, distributed across categories: politics, science, economy, technology, sports.
- Semantic search with filtering identifies 10 relevant technology articles from the last 6 months.
- Top 5 most similar articles are listed with similarity scores.

**Analytics by Categories**

| Category    | Number of Articles | Average Similarity |
|-------------|-------------------|-------------------|
| Technology  | 97                | 0.766             |
| Science     | 107               | 0.765             |
| Economy     | 103               | 0.762             |
| Sports      | 84                | 0.761             |
| Politics    | 109               | 0.760             |

**Demonstration for Data Scientists**

- 1,000 products created; 15 recommendations found.
- Top 5 recommended products are listed with price, rating, and similarity.
- Cluster analysis and A/B testing of algorithms (cosine vs. Euclidean metrics) provided.

**Advanced Analytics**

- Time trends of similarity by month.
- SQL analytics with grouping by month and category.

**Multiprocessing Testing**

- Performance metrics for sequential and parallel processing.
- Batch search processing times and throughput comparisons.

**Real Use Cases**

- Corporate knowledge base search (e.g., 25,000 documents, technical documentation search in 0.315s).
- Scalability analysis for datasets from 1,000 to 20,000+ vectors.

**Main Advantages**

- Unified SQL interface for vectors and metadata.
- Assembler optimization of critical computations.
- Automatic scaling under load.
- Flexible similarity metrics for diverse tasks.

**Business Value**

- Speeds up analytics processes by 2–10 times.
- Unifies tools for working with vectors and SQL.
- Easy integration with existing ML pipelines.
- Scalable from thousands to millions of vectors.

**Installation and Running**

- System requirements: Python 3.8+, FASM (Flat Assembler), GCC, multi-core processor.

**Testing Results**

- Full demo time: 8 seconds (1,865 documents).
- Multiprocessing demo: times vary by dataset and method.
- Vector computation benchmarks confirm high throughput and accuracy.

**Conclusion**

The Hybrid Analytics Platform demonstrates:

- Integration of vector search and SQL analytics in a single solution.
- High performance via assembler optimization.
- Scalability with automatic multiprocessing.
- Ease of use for analysts and data scientists.
- Production readiness with fallback mechanisms.

The platform is ready for enterprise deployment and can significantly accelerate 
analytics involving vector data. 
Performance scales proportionally with more powerful hardware.
