#include <stdint.h>

extern void coroutine_init(void);
extern void* coroutine_yield(void);
extern void coroutine_restore_context(void* context);
extern void coroutine_go(void (*func)(void*), void* stack);

void python_coroutine_init() {
    coroutine_init();
}

void* python_coroutine_yield() {
    return coroutine_yield();
}

void python_coroutine_restore_context(void* context) {
    coroutine_restore_context(context);
}

void python_coroutine_go(void (*func)(void*), void* stack) {
    coroutine_go(func, stack);
}