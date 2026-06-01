import ctypes
import os
import platform
import numpy as np

lib_name = "mylib.dylib" if platform.system() == "Darwin" else "mylib.so"
lib_path = os.path.join(os.path.dirname(__file__), lib_name)

try:
    mylib = ctypes.CDLL(lib_path)
except OSError as exc:
    raise SystemExit(
        f"Could not load {lib_name}. On Apple Silicon, run this with an "
        f"x86_64/Rosetta Python because the FASM library is x86_64: {exc}"
    ) from exc

mylib.py_binary_search.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_size_t, ctypes.c_int]
mylib.py_binary_search.restype = ctypes.c_int

arr_np = np.array([1, 3, 5, 7, 9, 11, 13, 15], dtype=np.int32)
arr_ptr = arr_np.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
arr_size = len(arr_np)
search_value = 7

result = mylib.py_binary_search(arr_ptr, arr_size, search_value)
print("Result:", result)
