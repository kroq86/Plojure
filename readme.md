# Plojure

Plojure is a playground for Lisp, Python, and x86_64 assembly experiments. The
current `hybrid` branch also contains a macOS porting path for the FASM
examples.

The target workflow on macOS is intentionally boring:

```sh
fasm fasm/basic/fib.asm
./fasm/basic/fib
```

No Docker command in the hot path, no `exec format error`, no Linux ELF binary
pretending to be a macOS program.

## macOS FASM Setup

Install the companion fasm shim from `kroq86/fasm-mac`:

```sh
git clone https://github.com/kroq86/fasm-mac
cd fasm-mac
./install.sh
export PATH="$HOME/.local/bin:$PATH"
```

The installed command is named `fasm`.

On Apple Silicon it produces x86_64 Mach-O binaries, so Rosetta is required:

```sh
arch -x86_64 /usr/bin/true
```

If that fails:

```sh
softwareupdate --install-rosetta
```

## Standalone Examples

These examples now use `fasm/core/platform.inc` instead of hardcoded Linux
syscall numbers:

```sh
fasm fasm/basic/fib.asm
./fasm/basic/fib

fasm fasm/basic/arg.asm
./fasm/basic/arg fasm/basic/lol.txt

cd fasm/basic
fasm mycat.asm
./mycat

cd ../advanced/binary_search
fasm bin_s.asm
./bin_s
```

Expected behavior:

- `fib.asm` prints Fibonacci values.
- `arg.asm` prints the file passed as argv[1].
- `mycat.asm` prints `fasm/basic/lol.txt`.
- `bin_s.asm` prints the found index.

## Shared Library Examples

Simple C/Python native-library examples can now build `.dylib` files on macOS:

```sh
cd fasm/advanced/add
./run.sh

cd ../binary_search/wrapper
./run.sh

cd ../../oop_game
./build.sh
```

The build path is:

```sh
fasm --emit=macho-obj add.asm add.o
clang -arch x86_64 -dynamiclib wrapper.c add.o -o mylib.dylib
```

On Apple Silicon, Python `ctypes` needs an x86_64/Rosetta Python to load these
libraries. The default Homebrew Python is usually arm64 and cannot load an
x86_64 `.dylib`.

## Vector DB

`projects/vector-db` now looks for `.dylib` on Darwin and `.so` on Linux. The
macOS build path is:

```sh
cd projects/vector-db
fasm --emit=macho-obj assembly/dot_product.asm dot_product.o
clang -arch x86_64 -dynamiclib dot_product.o assembly/wrapper.c -o dot_product.dylib
```

If the native library cannot be loaded, the Python code keeps the existing
fallback behavior where available.

## What Still Is Not Done

- fasm classic itself still has no upstream-style `format Mach-O` formatter.
- Native arm64 assembly output is not part of this port.
- The Mach-O object converter rejects ELF relocations for now.
- Coroutines are intentionally left for a later pass because they switch stacks
  manually and cross Python callback boundaries.
- Python examples on Apple Silicon need an x86_64 Python runtime if they load
  x86_64 `.dylib` files.

## Original Lisp Interpreter

The repository also contains a small Lisp interpreter:

```sh
python projects/lisp-interpreter/main.py projects/lisp-interpreter/program.lisp
```

It supports recursive functions, lambda expressions, arithmetic, conditionals,
and function calls.
