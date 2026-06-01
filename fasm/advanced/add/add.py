import ctypes
import os
import platform

lib_name = "mylib.dylib" if platform.system() == "Darwin" else "mylib.so"
lib_path = os.path.join(os.path.dirname(__file__), lib_name)

try:
    mylib = ctypes.CDLL(lib_path)
except OSError as exc:
    raise SystemExit(
        f"Could not load {lib_name}. On Apple Silicon, run this with an "
        f"x86_64/Rosetta Python because the FASM library is x86_64: {exc}"
    ) from exc
mylib.py_add.argtypes = [ctypes.c_int, ctypes.c_int]
mylib.py_add.restype = ctypes.c_int

result = mylib.py_add(5, 7)
print("Result:", result)
