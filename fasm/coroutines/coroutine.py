import ctypes

try:
    lib = ctypes.CDLL('./coroutines.so')
except OSError as e:
    print(f"Error loading library: {e}")
    exit(1)

lib.python_coroutine_init.argtypes = []
lib.python_coroutine_init.restype = None

lib.python_coroutine_yield.argtypes = []
lib.python_coroutine_yield.restype = ctypes.c_void_p

lib.python_coroutine_restore_context.argtypes = [ctypes.c_void_p]
lib.python_coroutine_restore_context.restype = None

lib.python_coroutine_go.argtypes = [ctypes.CFUNCTYPE(None, ctypes.c_void_p), ctypes.c_void_p]
lib.python_coroutine_go.restype = None

COROUTINE_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_void_p)

STACK_CAPACITY = 1024 * 1024

def coroutine1(arg):
    print("Coroutine 1 started")
    lib.python_coroutine_yield()
    print("Coroutine 1 resumed")

def coroutine2(arg):
    print("Coroutine 2 started")
    lib.python_coroutine_yield()
    print("Coroutine 2 resumed")

lib.python_coroutine_init()

# Allocate stacks
stack1 = (ctypes.c_uint8 * STACK_CAPACITY)()
stack2 = (ctypes.c_uint8 * STACK_CAPACITY)()

# Align stack pointers to 16 bytes
def align_stack_pointer(stack_ptr, alignment=16):
    return stack_ptr - (stack_ptr % alignment)

stack1_ptr = ctypes.addressof(stack1) + STACK_CAPACITY - 16
aligned_stack1_ptr = align_stack_pointer(stack1_ptr)
context1 = ctypes.c_void_p(aligned_stack1_ptr)

stack2_ptr = ctypes.addressof(stack2) + STACK_CAPACITY - 16
aligned_stack2_ptr = align_stack_pointer(stack2_ptr)
context2 = ctypes.c_void_p(aligned_stack2_ptr)

print(f"Stack 1 pointer: {hex(stack1_ptr)}")
print(f"Aligned Stack 1 pointer: {hex(aligned_stack1_ptr)}")
print(f"Stack 2 pointer: {hex(stack2_ptr)}")
print(f"Aligned Stack 2 pointer: {hex(aligned_stack2_ptr)}")

print("Starting coroutine 1")
lib.python_coroutine_go(COROUTINE_FUNC(coroutine1), context1)

print("Starting coroutine 2")
lib.python_coroutine_go(COROUTINE_FUNC(coroutine2), context2)

print("Yielding from main coroutine")
context_main = lib.python_coroutine_yield()

print("Restoring coroutine 1")
lib.python_coroutine_restore_context(context1)

print("Restoring coroutine 2")
lib.python_coroutine_restore_context(context2)