import ctypes
import os
import time

lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "..", "libcoroutines.so"))

class GeneratorStruct(ctypes.Structure):
    _fields_ = [
        ("fresh", ctypes.c_bool),
        ("dead", ctypes.c_bool),
        ("_padding", ctypes.c_char * 6),
        ("rsp", ctypes.c_void_p),
        ("stack_base", ctypes.c_void_p),
        ("func", ctypes.c_void_p),
    ]

lib.python_generator_init.argtypes = []
lib.python_generator_init.restype = None
lib.python_generator_next.argtypes = [ctypes.POINTER(GeneratorStruct), ctypes.c_void_p]
lib.python_generator_next.restype = ctypes.c_void_p

stack_capacity = 1024 * os.sysconf("SC_PAGE_SIZE")
stack_mem = (ctypes.c_uint8 * stack_capacity)()

bench_func = ctypes.cast(lib.bench_coroutine_func, ctypes.c_void_p).value

lib.python_generator_init()

g = GeneratorStruct()
g.fresh = True
g.dead = False
g.stack_base = ctypes.addressof(stack_mem)
g.func = bench_func

start = time.perf_counter()
r1 = lib.python_generator_next(ctypes.byref(g), None)
r2 = lib.python_generator_next(ctypes.byref(g), ctypes.c_void_p(42))
r3 = lib.python_generator_next(ctypes.byref(g), ctypes.c_void_p(84))
sec = time.perf_counter() - start

if (not r1) or (not r2) or r3:
    raise SystemExit(f"unexpected sequence: r1={r1} r2={r2} r3={r3}")

ops = 1.0 / sec
print(f"lang=python,iters=1,total_sec={sec:.6f},ops_per_sec={ops:.2f}")
