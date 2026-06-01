Linux:

```sh
fasm --emit=elf add.asm add.o
gcc -c wrapper.c -o wrapper.o
gcc -shared -o mylib.so add.o wrapper.o
python3 add.py
```

macOS x86_64/Rosetta:

```sh
fasm --emit=macho-obj add.asm add.o
clang -arch x86_64 -c wrapper.c -o wrapper.o
clang -arch x86_64 -dynamiclib wrapper.o add.o -o mylib.dylib
arch -x86_64 python3 add.py
```

Or use:

```sh
./run.sh
```
