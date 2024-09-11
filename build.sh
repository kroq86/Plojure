#!/bin/sh

set -xe

# Run the Python script to generate the assembly code
python3 main.py

# Assemble the generated assembly code
nasm -f elf64 -o plojure.o plojure.asm

# Link the object file to create the executable
gcc -o plojure plojure.o
