#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ITERATIONS="${1:-200000}"

echo "[rust] building shared ASM/C library..."
bash "$ROOT/build_lib.sh" >/dev/null

echo "[rust] compiling benchmark.rs in rust:1-bookworm ..."
docker run --rm --platform linux/amd64 \
  -v "$ROOT:/workspace/coroutines" \
  -w /workspace/coroutines/rust \
  rust:1-bookworm \
  bash -lc 'set -e; export PATH=/usr/local/cargo/bin:$PATH; rustc -O benchmark.rs -L ../ -l dylib=coroutines -o rust_bench; echo "[rust] running benchmark..."; LD_LIBRARY_PATH=.. ./rust_bench '"$ITERATIONS"''
