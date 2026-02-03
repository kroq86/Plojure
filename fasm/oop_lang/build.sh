#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Compiling game.oop -> generated/game.asm, generated/wrapper.c ..."
python3 compiler.py
fasm generated/game.asm generated/game.o
gcc -c generated/wrapper.c -o generated/wrapper.o -fPIC
gcc -shared -o mylib.so generated/game.o generated/wrapper.o
echo "Built mylib.so"
