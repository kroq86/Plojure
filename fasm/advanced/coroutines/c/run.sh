#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ITERATIONS="${1:-200000}"

echo "[c] building shared ASM/C library..."
bash "$ROOT/build_lib.sh" >/dev/null

IMAGE="${DOTFASM_IMAGE:-plojure-fasm-amd64:latest}"

echo "[c] compiling benchmark.c in $IMAGE ..."
docker run --rm --platform linux/amd64 \
  -v "$ROOT:/workspace/coroutines" \
  -w /workspace/coroutines/c \
  "$IMAGE" \
  bash -lc 'set -e; gcc -O3 -o c_bench benchmark.c -L.. -lcoroutines; echo "[c] running benchmark..."; LD_LIBRARY_PATH=.. ./c_bench '"$ITERATIONS"''
