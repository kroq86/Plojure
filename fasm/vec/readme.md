fasm dot_product.asm dot_product.o
gcc -c wrapper.c -o wrapper.o
gcc -shared -o mylib.so dot_product.o wrapper.o
python vec.py

python example_duckdb.py

Persistent storage (DuckDB)
Multiple search algorithms
Different similarity metrics
Memory management
Parallel processing
Transaction support