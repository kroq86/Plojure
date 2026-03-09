#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
bash "$ROOT/build_lib.sh" >/dev/null
echo "[cpp] building shared ASM/C library..."
echo "[cpp] compiling benchmark.cpp in gcc:14-bookworm ..."
docker run --rm --platform linux/amd64 -v "$ROOT:/workspace/coroutines" -w /workspace/coroutines/cpp gcc:14-bookworm \
  bash -lc 'set -e; g++ -O3 -o cpp_bench benchmark.cpp -L.. -lcoroutines; echo "[cpp] running benchmark..."; LD_LIBRARY_PATH=.. ./cpp_bench'
