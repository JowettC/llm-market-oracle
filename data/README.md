# `data/` — committed, reproducible snapshots

Two subtrees, both point-in-time and frozen once written (PRD §6.1).

## `prices/<ASSET>.csv`
Daily OHLCV, `date` column in ISO-8601 UTC. Read by `CSVMarketProvider`.

## `news/<ASSET>.jsonl`
One JSON object per line. Required fields: `news_id`, `published_at` (UTC),
`headline`. Optional: `body`, `source`, `assets`. Read by `JSONLNewsProvider`.
Every item **must** carry a trustworthy `published_at` — untrusted timestamps
are dropped (PRD §6.2), the single biggest guard against accidental lookahead.

## Current state of the committed snapshots

| Subtree | Status | Source |
|---|---|---|
| `prices/*.csv` | ✅ **REAL** | `python -m scripts.fetch_real_prices` — SPY via Yahoo Finance, BTC/ETH via Binance klines. No API key. |
| `news/*.jsonl` | ✅ **REAL** | `python -m scripts.fetch_real_news` — GDELT DOC 2.0, `seendate` as leakage-safe `published_at`. No API key. Provenance in `MANIFEST.json`. |

**Corpus coverage (clean window 2026-01-01 → 2026-07-23, headlines only):**
~1,700 items per asset over ~175–199 distinct days — near-complete daily
coverage. English-only, relevance-sorted, per-asset queries (see `MANIFEST.json`).
All items are post-cutoff (clean); `scripts/verify_fairness.py` confirms zero
gate leakage and zero future-dated items.

**Both baselines and the (future) LLM now run on real data.** The scored window
is aligned to the news corpus, with θ/class-frequency calibration on the
disjoint earlier price history.

**Refreshing / extending:** `fetch_real_news` is resumable (chunk cache under
`.cache/`, git-ignored) — re-run to widen the window or densify coverage. The
historical (contaminated) window via FNSPID (PRD §6.2) remains future work.
