#!/usr/bin/env bash
# Autonomous, self-pacing driver for jobs A (prompt x condition sweep) and
# B (memorization probes) against the Claude Max subscription.
#
# Each batch runs until it hits the usage budget (config: llm.budget_calls, the
# "90%" ceiling) OR the real subscription limit; then it prints a stop marker.
# On any stop we WAIT 5h (rolling-window reset) and retry. The response cache
# makes every retry resume exactly where it left off — no call is re-spent.
#
# To change the per-batch call count at any time: edit `llm.budget_calls` in
# config/experiment.yaml. Each batch re-reads config, so the change takes effect
# on the very next batch. Override the wait with AB_WAIT (seconds).
#
#   nohup bash scripts/run_ab_auto.sh > <log> 2>&1 &
set -u
cd /home/jowettc/projects/llm-trading
PY=.venv/bin/python
WAIT="${AB_WAIT:-18000}"   # 5 hours
BATCHLOG="/tmp/claude-1000/-home-jowettc-projects-llm-trading/ce6f7f53-828a-488d-b27c-e185ba3b48d2/scratchpad/ab_batch.log"
WINDOW_STATE="/home/jowettc/projects/llm-trading/cache/llm/.window_calls"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Run one command as a batch; loop with 5h waits until it completes cleanly.
# Returns 0 when the stage finished, 1 on a genuine (non-budget) error.
run_stage() {
  local name="$1"; shift
  while true; do
    echo "[$(ts)] STAGE $name: starting batch"
    "$@" > "$BATCHLOG" 2>&1; local rc=$?
    if grep -q "stopping LLM runs" "$BATCHLOG"; then
      local spent; spent=$(grep -oE "[0-9]+ new Claude calls" "$BATCHLOG" | tail -1)
      echo "[$(ts)] STAGE $name: budget/limit hit ($spent) — waiting ${WAIT}s then continuing"
      sleep "$WAIT"
      echo 0 > "$WINDOW_STATE"   # rolling window has reset — clear the window meter
      echo "[$(ts)] STAGE $name: window meter reset; resuming"
      continue
    fi
    if [ $rc -ne 0 ]; then
      echo "[$(ts)] STAGE $name: ERROR rc=$rc"; tail -8 "$BATCHLOG"; return 1
    fi
    echo "[$(ts)] STAGE $name: COMPLETE"; return 0
  done
}

SWEEP=("$PY" -m src.run --llm --llm-model claude_opus --smoke --llm-max-news 40)

echo "[$(ts)] === A+B auto-driver started (wait=${WAIT}s) ==="

# ---- Job A: prompt x condition sweep (daily, all assets) ----
run_stage "A/news_only"  "${SWEEP[@]}" --prompts P0 P1 P2 P3 --conditions news_only \
  --output-dir /home/jowettc/projects/llm-trading/results/llm_sweep || exit 1
run_stage "A/news_price" "${SWEEP[@]}" --prompts P0 P1 P2 P3 --conditions news_plus_price \
  --output-dir /home/jowettc/projects/llm-trading/results/llm_sweep_price || exit 1

# ---- Job B: memorization probes at scale (40 samples/asset) ----
for A in SPY BTC ETH; do
  run_stage "B/probe_$A" "$PY" -m scripts.run_probes --asset "$A" --limit 40 || exit 1
done

echo "[$(ts)] === A_AND_B_COMPLETE ==="
