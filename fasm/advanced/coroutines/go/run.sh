#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
bash "$ROOT/build_lib.sh" >/dev/null
echo "[go] building shared ASM/C library..."
echo "[go] compiling main.go in golang:1.24-bookworm ..."
docker run --rm --platform linux/amd64 -v "$ROOT:/workspace/coroutines" -w /workspace/coroutines/go golang:1.24-bookworm \
  bash -lc 'set -e; export PATH=/usr/local/go/bin:$PATH; go version; go build -o go_bench main.go; echo "[go] running benchmark..."; LD_LIBRARY_PATH=.. ./go_bench'
