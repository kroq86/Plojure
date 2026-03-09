#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/stats"
CSV="$OUT_DIR/top10_results.csv"
MD="$OUT_DIR/top10_analysis.md"
RAW="$OUT_DIR/top10_raw.log"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TIMEOUT_SEC="${BENCH_TIMEOUT_SEC:-45}"

mkdir -p "$OUT_DIR"

echo "timestamp,language,status,exit_code,wall_sec,ops_per_sec,notes" > "$CSV"
: > "$RAW"

run_one() {
  local lang="$1"
  local script="$2"
  local tmp
  local start_epoch
  local end_epoch
  local wall_sec
  local code

  echo "[$(date +%H:%M:%S)] START $lang"
  echo "[$(date +%H:%M:%S)] CMD: bash $script"
  echo "[$(date +%H:%M:%S)] TIMEOUT: ${TIMEOUT_SEC}s"

  tmp="$(mktemp)"
  start_epoch="$(date +%s)"

  set +e
  (
    set -o pipefail
    bash "$script" 2>&1 | tee "$tmp"
  ) &
  local pid=$!
  code=0
  local elapsed=0
  while kill -0 "$pid" >/dev/null 2>&1; do
    sleep 1
    elapsed=$((elapsed + 1))
    if [[ $elapsed -ge $TIMEOUT_SEC ]]; then
      echo "[$(date +%H:%M:%S)] TIMEOUT $lang after ${TIMEOUT_SEC}s"
      kill "$pid" >/dev/null 2>&1 || true
      code=124
      break
    fi
  done

  if [[ $code -eq 0 ]]; then
    wait "$pid"
    code=$?
  else
    wait "$pid" >/dev/null 2>&1 || true
  fi
  set -e

  end_epoch="$(date +%s)"
  wall_sec="$((end_epoch - start_epoch))"
  if [[ "$wall_sec" -le 0 ]]; then
    wall_sec=1
  fi

  local output
  output="$(cat "$tmp")"
  rm -f "$tmp"

  {
    echo "[$lang]"
    echo "$output"
    echo "---"
  } >> "$RAW"

  if [[ $code -eq 0 ]]; then
    local parsed
    parsed="$(echo "$output" | rg '^lang=' | tail -n1 || true)"
    if [[ -n "$parsed" ]]; then
      local ops
      ops="$(awk -v s="$wall_sec" 'BEGIN { printf "%.2f", 1/s }')"
      echo "$TS,$lang,ok,0,$wall_sec,$ops,completed" >> "$CSV"
      echo "[$(date +%H:%M:%S)] DONE $lang (wall=${wall_sec}s)"
      return
    fi
    echo "$TS,$lang,failed,2,$wall_sec,,no-benchmark-line" >> "$CSV"
    echo "[$(date +%H:%M:%S)] FAIL $lang (no benchmark line)"
    return
  fi

  local notes="failed"
  if [[ $code -eq 124 ]]; then
    notes="timeout"
  elif [[ $code -eq 125 ]]; then
    notes="stub"
  fi
  echo "$TS,$lang,failed,$code,$wall_sec,,$notes" >> "$CSV"
  echo "[$(date +%H:%M:%S)] FAIL $lang (exit=$code, note=$notes)"
}

run_one "c" "$SCRIPT_DIR/c/run.sh"
run_one "cpp" "$SCRIPT_DIR/cpp/run.sh"
run_one "go" "$SCRIPT_DIR/go/run.sh"
run_one "rust" "$SCRIPT_DIR/rust/run.sh"
run_one "python" "$SCRIPT_DIR/python/run.sh"
run_one "julia" "$SCRIPT_DIR/julia/run.sh"
run_one "haskell" "$SCRIPT_DIR/haskell/run.sh"
run_one "ruby" "$SCRIPT_DIR/ruby/run.sh"
run_one "lua" "$SCRIPT_DIR/lua/run.sh"
run_one "zig" "$SCRIPT_DIR/zig/run.sh"

# Build ranking for successful languages
ranking_tmp="$(mktemp)"
awk -F, 'NR>1 && $3=="ok" { print $2 "," $6 "," $5 }' "$CSV" | sort -t, -k2,2nr > "$ranking_tmp"

{
  echo "# Top-10 Controller Languages Analysis"
  echo
  echo "- Timestamp (UTC): $TS"
  echo "- Timeout per language: ${TIMEOUT_SEC}s"
  echo "- Source CSV: [top10_results.csv](./top10_results.csv)"
  echo
  echo "## Full Results"
  echo
  echo "| Language | Status | Exit | Wall sec | Ops/sec | Notes |"
  echo "|---|---|---:|---:|---:|---|"
  tail -n +2 "$CSV" | while IFS=, read -r ts lang status exit_code wall_sec ops notes; do
    echo "| $lang | $status | $exit_code | $wall_sec | ${ops:-n/a} | $notes |"
  done
  echo
  echo "## Ranking (Successful Only)"
  echo
  echo "| Rank | Language | Ops/sec | Wall sec |"
  echo "|---:|---|---:|---:|"
  if [[ -s "$ranking_tmp" ]]; then
    rank=1
    while IFS=, read -r lang ops wall; do
      echo "| $rank | $lang | $ops | $wall |"
      rank=$((rank + 1))
    done < "$ranking_tmp"
  else
    echo "| - | none | n/a | n/a |"
  fi
} > "$MD"

rm -f "$ranking_tmp"

echo "Saved: $CSV"
echo "Saved: $MD"
echo "Saved: $RAW"
