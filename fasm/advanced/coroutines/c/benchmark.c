#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

typedef struct {
    uint8_t fresh;
    uint8_t dead;
    uint8_t _padding[6];
    void* rsp;
    void* stack_base;
    void* func;
} Generator;

void python_generator_init(void);
void* python_generator_next(void* g, void* arg);
void bench_coroutine_func(void* arg);

static uint64_t monotonic_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

int main(int argc, char** argv) {
    long iters = 200000;
    if (argc > 1) {
        iters = atol(argv[1]);
        if (iters <= 0) {
            fprintf(stderr, "iterations must be > 0\n");
            return 2;
        }
    }

    size_t stack_capacity = 1024 * (size_t)sysconf(_SC_PAGE_SIZE);
    python_generator_init();

    void* stack_mem = malloc(stack_capacity);
    if (!stack_mem) {
        fprintf(stderr, "malloc failed\n");
        return 3;
    }

    uint64_t t0 = monotonic_ns();

    Generator g = {0};
    g.fresh = 1;
    g.dead = 0;
    g.rsp = 0;
    g.stack_base = stack_mem;
    g.func = (void*)bench_coroutine_func;

    void* r1 = python_generator_next(&g, NULL);
    void* r2 = python_generator_next(&g, (void*)42);
    void* r3 = python_generator_next(&g, (void*)84);

    if (r1 == NULL || r2 == NULL || r3 != NULL) {
        fprintf(stderr, "unexpected sequence: r1=%p r2=%p r3=%p\n", r1, r2, r3);
        return 4;
    }

    uint64_t t1 = monotonic_ns();

    (void)stack_mem;

    double sec = (double)(t1 - t0) / 1e9;
    double ops = 1.0 / sec;
    printf("lang=c,iters=1,total_sec=%.6f,ops_per_sec=%.2f\n", sec, ops);
    return 0;
}
