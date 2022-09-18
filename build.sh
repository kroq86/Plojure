#!/bin/sh

set -xe

nasm -f elf64 -o plojure.o plojure.asm
gcc -o plojure plojure.o