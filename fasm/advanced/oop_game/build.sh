#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

case "$(uname -s)" in
  Darwin)
    fasm --emit=macho-obj game.asm game.o
    clang -arch x86_64 -c wrapper.c -o wrapper.o
    clang -arch x86_64 -dynamiclib wrapper.o game.o -o mylib.dylib
    echo "Built mylib.dylib"
    ;;
  *)
    fasm game.asm game.o
    gcc -c wrapper.c -o wrapper.o -fPIC
    gcc -shared -o mylib.so game.o wrapper.o
    echo "Built mylib.so"
    ;;
esac
