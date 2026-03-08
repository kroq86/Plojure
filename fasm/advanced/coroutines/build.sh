#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
IMAGE="${DOTFASM_IMAGE:-plojure-fasm-amd64:latest}"

ensure_image() {
  if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    return
  fi

  echo "[coroutines] Building local image $IMAGE (one-time setup)..."
  docker rm -f plojure-fasm-bootstrap >/dev/null 2>&1 || true
  docker run --name plojure-fasm-bootstrap --platform linux/amd64 debian:bookworm-slim \
    bash -lc 'set -e; apt-get update >/dev/null; DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends fasm gcc libc6-dev python3 make bash ca-certificates >/dev/null'
  docker commit plojure-fasm-bootstrap "$IMAGE" >/dev/null
  docker rm -f plojure-fasm-bootstrap >/dev/null
}

if [[ "$(uname -s)" == "Darwin" ]] || ! command -v fasm >/dev/null 2>&1; then
  ensure_image
  docker run --rm --platform linux/amd64 \
    -v "$REPO_ROOT:/workspace" \
    -w /workspace/fasm/advanced/coroutines \
    "$IMAGE" \
    bash -lc 'set -e; fasm switch.asm switch.o; gcc -fPIC -c wrapper.c -o wrapper.o; gcc -shared -Wl,-z,noexecstack -o libcoroutines.so switch.o wrapper.o -lc; python3 coroutine.py'
  exit 0
fi

# Linux/local toolchain path
fasm switch.asm switch.o
gcc -fPIC -c wrapper.c -o wrapper.o
gcc -shared -Wl,-z,noexecstack -o libcoroutines.so switch.o wrapper.o -lc

python3 coroutine.py
