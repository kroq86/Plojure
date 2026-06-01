#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

case "$(uname -s)" in
  Darwin)
    fasm --emit=macho-obj add.asm add.o
    clang -arch x86_64 -c wrapper.c -o wrapper.o
    clang -arch x86_64 -dynamiclib wrapper.o add.o -o mylib.dylib
    if [ "$(python3 -c 'import platform; print(platform.machine())')" != "x86_64" ]; then
      echo "Built mylib.dylib. Run add.py with an x86_64/Rosetta Python to load it."
      exit 0
    fi
    ;;
  *)
    fasm add.asm add.o
    gcc -c wrapper.c -o wrapper.o
    gcc -shared -o mylib.so add.o wrapper.o
    ;;
esac

python3 add.py
