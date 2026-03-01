import argparse
import json
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from duckdb_vec import DuckDBVectorDatabase


def generate_vectors(num_vectors: int, dimensions: int):
    random.seed(42)
    vectors = []
    for index in range(num_vectors):
        vector = [random.random() for _ in range(dimensions)]
        vectors.append((f"vec_{index}", vector))
    return vectors


def benchmark_search(use_asm: bool, similarity_metric: str, num_vectors: int, dimensions: int, iterations: int):
    db = DuckDBVectorDatabase(
        ":memory:",
        similarity_metric=similarity_metric,
        use_asm=use_asm,
    )
    vectors = generate_vectors(num_vectors, dimensions)
    db.batch_insert(vectors)
    query = vectors[0][1]

    start = time.perf_counter()
    for _ in range(iterations):
        db.search(query, k=10, method="exact")
    elapsed = time.perf_counter() - start

    runtime = db.get_runtime_info()
    db.close()
    return {
        "elapsed_seconds": elapsed,
        "iterations": iterations,
        "num_vectors": num_vectors,
        "dimensions": dimensions,
        "similarity_metric": similarity_metric,
        "runtime": runtime,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark asm on vs off for vector search.")
    parser.add_argument("--num-vectors", type=int, default=2000)
    parser.add_argument("--dimensions", type=int, default=256)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--metric", default="cosine", choices=["cosine", "euclidean", "dot_product"])
    args = parser.parse_args()

    asm_result = benchmark_search(
        use_asm=True,
        similarity_metric=args.metric,
        num_vectors=args.num_vectors,
        dimensions=args.dimensions,
        iterations=args.iterations,
    )
    python_result = benchmark_search(
        use_asm=False,
        similarity_metric=args.metric,
        num_vectors=args.num_vectors,
        dimensions=args.dimensions,
        iterations=args.iterations,
    )

    speedup = None
    if asm_result["elapsed_seconds"] > 0:
        speedup = python_result["elapsed_seconds"] / asm_result["elapsed_seconds"]

    print(json.dumps({
        "asm": asm_result,
        "python": python_result,
        "speedup_vs_python": speedup,
    }, indent=2))


if __name__ == "__main__":
    main()
