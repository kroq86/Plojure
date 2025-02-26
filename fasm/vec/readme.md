fasm dot_product.asm dot_product.o
gcc -c wrapper.c -o wrapper.o
gcc -shared -o mylib.so dot_product.o wrapper.o
python vec.py