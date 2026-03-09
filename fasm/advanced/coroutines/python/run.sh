#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
bash "$ROOT/build_lib.sh" >/dev/null
IMAGE="${DOTFASM_IMAGE:-plojure-fasm-amd64:latest}"
echo "[python] building shared ASM/C library..."
echo "[python] running benchmark.py in $IMAGE ..."
docker run --rm --platform linux/amd64 -v "$ROOT:/workspace/coroutines" -w /workspace/coroutines/python "$IMAGE" \
  bash -lc 'set -e; echo "[python] running benchmark..."; LD_LIBRARY_PATH=.. python3 benchmark.py'
