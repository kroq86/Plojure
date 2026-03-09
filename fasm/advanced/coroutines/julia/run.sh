#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
bash "$ROOT/build_lib.sh" >/dev/null
echo "[julia] building shared ASM/C library..."
echo "[julia] running benchmark.jl in julia:1.11-bookworm ..."
docker run --rm --platform linux/amd64 -v "$ROOT:/workspace/coroutines" -w /workspace/coroutines/julia julia:1.11-bookworm \
  bash -lc 'set -e; echo "[julia] running benchmark..."; LD_LIBRARY_PATH=.. julia benchmark.jl'
