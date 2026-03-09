package main

/*
#cgo LDFLAGS: -L.. -lcoroutines
#include <stdint.h>

typedef struct {
    uint8_t fresh;
    uint8_t dead;
    uint8_t pad[6];
    void* rsp;
    void* stack_base;
    void* func;
} Generator;

extern void python_generator_init(void);
extern void* python_generator_next(void* g, void* arg);
extern void bench_coroutine_func(void* arg);
*/
import "C"
import (
	"fmt"
	"os"
	"time"
	"unsafe"
)

func main() {
	stackCap := 1024 * 4096
	C.python_generator_init()

	stack := C.malloc(C.size_t(stackCap))
	if stack == nil {
		os.Exit(3)
	}

	var g C.Generator
	g.fresh = 1
	g.stack_base = stack
	g.func = unsafe.Pointer(C.bench_coroutine_func)

	t0 := time.Now()
	r1 := C.python_generator_next(unsafe.Pointer(&g), nil)
	r2 := C.python_generator_next(unsafe.Pointer(&g), unsafe.Pointer(uintptr(42)))
	r3 := C.python_generator_next(unsafe.Pointer(&g), unsafe.Pointer(uintptr(84)))
	sec := time.Since(t0).Seconds()

	if r1 == nil || r2 == nil || r3 != nil {
		fmt.Fprintf(os.Stderr, "unexpected sequence: r1=%v r2=%v r3=%v\n", r1, r2, r3)
		os.Exit(4)
	}

	op := 1.0 / sec
	fmt.Printf("lang=go,iters=1,total_sec=%.6f,ops_per_sec=%.2f\n", sec, op)
}
