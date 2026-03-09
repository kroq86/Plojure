#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <unistd.h>

struct Generator {
  uint8_t fresh;
  uint8_t dead;
  uint8_t pad[6];
  void* rsp;
  void* stack_base;
  void* func;
};

extern "C" void python_generator_init(void);
extern "C" void* python_generator_next(void* g, void* arg);
extern "C" void bench_coroutine_func(void* arg);

static uint64_t monotonic_ns() {
  timespec ts{};
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

int main() {
  const size_t stack_capacity = 1024 * (size_t)sysconf(_SC_PAGE_SIZE);
  python_generator_init();

  void* stack_mem = std::malloc(stack_capacity);
  if (!stack_mem) return 3;

  Generator g{};
  g.fresh = 1;
  g.stack_base = stack_mem;
  g.func = (void*)bench_coroutine_func;

  uint64_t t0 = monotonic_ns();
  void* r1 = python_generator_next(&g, nullptr);
  void* r2 = python_generator_next(&g, (void*)42);
  void* r3 = python_generator_next(&g, (void*)84);
  uint64_t t1 = monotonic_ns();

  if (r1 == nullptr || r2 == nullptr || r3 != nullptr) {
    std::fprintf(stderr, "unexpected sequence: r1=%p r2=%p r3=%p\n", r1, r2, r3);
    return 4;
  }

  double sec = (double)(t1 - t0) / 1e9;
  double ops = 1.0 / sec;
  std::printf("lang=cpp,iters=1,total_sec=%.6f,ops_per_sec=%.2f\n", sec, ops);
  return 0;
}
