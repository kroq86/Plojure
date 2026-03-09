#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ITERATIONS="${1:-200000}"

echo "[haskell] building shared ASM/C library..."
bash "$ROOT/build_lib.sh" >/dev/null

echo "[haskell] compiling Main.hs in haskell:9.6-bookworm ..."
docker run --rm --platform linux/amd64 \
  -v "$ROOT:/workspace/coroutines" \
  -w /workspace/coroutines/haskell \
  haskell:9.6 \
  bash -lc 'set -e; ghc -O2 Main.hs -L../ -lcoroutines -o hs_bench; echo "[haskell] running benchmark..."; LD_LIBRARY_PATH=.. ./hs_bench '"$ITERATIONS"''
