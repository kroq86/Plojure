# Language Variants (Controller Languages)

Baseline Python already exists in:
- `coroutine.py`

Additional variants added in this folder:
- `c/` - C controller benchmark (`c/run.sh`)
- `cpp/` - C++ controller benchmark (`cpp/run.sh`)
- `go/` - Go controller benchmark (`go/run.sh`)
- `rust/` - Rust controller benchmark (`rust/run.sh`)
- `python/` - Python controller benchmark (`python/run.sh`)
- `julia/` - Julia controller benchmark (`julia/run.sh`)
- `haskell/` - Haskell controller benchmark (`haskell/run.sh`)
- `ruby/` - Ruby controller placeholder (`ruby/run.sh`)
- `lua/` - Lua controller placeholder (`lua/run.sh`)
- `zig/` - Zig controller placeholder (`zig/run.sh`)

Shared build:
- `build_lib.sh` - builds `libcoroutines.so` from ASM + C wrapper

Unified stats:
- `run_stats.sh` - runs variants with live logging and timeout
- `run_top10.sh` - runs top-10 language matrix with live logging, timeout, and ranking
- `stats/results.csv`
- `stats/summary.md`
- `stats/raw.log`
- `stats/top10_results.csv`
- `stats/top10_analysis.md`
- `stats/top10_raw.log`

## Run

From `fasm/advanced/coroutines`:

```bash
./run_stats.sh 1
```

Optional Haskell run:

```bash
RUN_HASKELL=1 ./run_stats.sh 1
```

Top-10 matrix:

```bash
BENCH_TIMEOUT_SEC=45 ./run_top10.sh
```

## Notes

- Runtime context-switch semantics are stable for Python baseline and C smoke cycle.
- Rust run currently times out in this environment (captured in `stats/raw.log`).
- Haskell is skipped by default to avoid heavy image pull/compile unless explicitly enabled.
