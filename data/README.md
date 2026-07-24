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
| `news/*.jsonl` | ⚠️ **SYNTHETIC** | `python -m scripts.make_sample_data` (`source: "SYNTHETIC_SAMPLE"`) — placeholder pending real ingestion. |

**What this means for results right now.** The price-only baselines
(always-up, buy-and-hold, momentum, random) run on **real market data** and
their numbers are meaningful. The **sentiment** baseline reads the synthetic
news and is **not** meaningful yet, and the LLM predictors (Phase 3) need the
real news corpus before their results count.

**Real news is the next step** and the crux of the whole study: every item must
carry a trustworthy `published_at` and the clean-window dates must fall **after**
the model's training cutoff (PRD §6.2, §7.2). Planned feeds: GDELT (reachable,
rate-limited) + Alpha Vantage / CryptoPanic for the clean window; FNSPID for the
historical (contaminated) window.
