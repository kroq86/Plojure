#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/stats"
CSV="$OUT_DIR/results.csv"
MD="$OUT_DIR/summary.md"
ITERATIONS="${1:-100000}"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TIMEOUT_SEC="${BENCH_TIMEOUT_SEC:-45}"

mkdir -p "$OUT_DIR"

echo "timestamp,language,iterations,total_sec,ops_per_sec,status" > "$CSV"

run_one() {
  local lang="$1"
  local script="$2"
  local output
  local tmp

  echo "[$(date +%H:%M:%S)] START $lang (iters=$ITERATIONS)"
  echo "[$(date +%H:%M:%S)] CMD: bash $script $ITERATIONS"
  echo "[$(date +%H:%M:%S)] TIMEOUT: ${TIMEOUT_SEC}s"
  tmp="$(mktemp)"
  local start_epoch
  local end_epoch
  local run_sec
  start_epoch="$(date +%s)"
  set +e
  (
    set -o pipefail
    bash "$script" "$ITERATIONS" 2>&1 | tee "$tmp"
  ) &
  local runner_pid=$!
  local code=0
  local elapsed=0
  while kill -0 "$runner_pid" >/dev/null 2>&1; do
    sleep 1
    elapsed=$((elapsed + 1))
    if [[ $elapsed -ge $TIMEOUT_SEC ]]; then
      echo "[$(date +%H:%M:%S)] TIMEOUT $lang after ${TIMEOUT_SEC}s"
      kill "$runner_pid" >/dev/null 2>&1 || true
      code=124
      break
    fi
  done
  if [[ $code -eq 0 ]]; then
    wait "$runner_pid"
    code=$?
  else
    wait "$runner_pid" >/dev/null 2>&1 || true
  fi
  set -e
  end_epoch="$(date +%s)"
  run_sec="$((end_epoch - start_epoch))"
  if [[ "$run_sec" -le 0 ]]; then
    run_sec=1
  fi
  output="$(cat "$tmp")"
  rm -f "$tmp"

  if [[ $code -ne 0 ]]; then
    echo "$TS,$lang,$ITERATIONS,,,failed" >> "$CSV"
    {
      echo "[$lang] failed"
      echo "$output"
      echo "---"
    } >> "$OUT_DIR/raw.log"
    echo "[$(date +%H:%M:%S)] FAIL  $lang (exit=$code)"
    return
  fi

  local line
  line="$(echo "$output" | rg '^lang=' | tail -n1 || true)"
  if [[ -z "$line" ]]; then
    echo "$TS,$lang,$ITERATIONS,,,failed" >> "$CSV"
    {
      echo "[$lang] no benchmark line"
      echo "$output"
      echo "---"
    } >> "$OUT_DIR/raw.log"
    echo "[$(date +%H:%M:%S)] FAIL  $lang (no parsable benchmark line)"
    return
  fi

  local total_sec ops
  total_sec="$run_sec"
  ops="$(awk -v i="$ITERATIONS" -v s="$run_sec" 'BEGIN { printf "%.2f", i/s }')"
  echo "$TS,$lang,$ITERATIONS,$total_sec,$ops,ok" >> "$CSV"
  echo "[$(date +%H:%M:%S)] DONE  $lang (sec=$total_sec, ops/s=$ops)"
}

: > "$OUT_DIR/raw.log"
run_one "c" "$SCRIPT_DIR/c/run.sh"
run_one "rust" "$SCRIPT_DIR/rust/run.sh"
if [[ "${RUN_HASKELL:-0}" == "1" ]]; then
  run_one "haskell" "$SCRIPT_DIR/haskell/run.sh"
else
  echo "$TS,haskell,$ITERATIONS,,,skipped" >> "$CSV"
  echo "[$(date +%H:%M:%S)] SKIP  haskell (set RUN_HASKELL=1 to enable)"
fi

{
  echo "# Coroutine Benchmark Stats"
  echo
  echo "- Timestamp (UTC): $TS"
  echo "- Iterations per language: $ITERATIONS"
  echo
  echo "| Language | Iterations | Total sec | Ops/sec | Status |"
  echo "|---|---:|---:|---:|---|"
  tail -n +2 "$CSV" | while IFS=, read -r ts lang it sec ops status; do
    echo "| $lang | $it | ${sec:-n/a} | ${ops:-n/a} | $status |"
  done
  echo
  echo "Raw logs: [raw.log](./raw.log)"
} > "$MD"

echo "Saved: $CSV"
echo "Saved: $MD"
