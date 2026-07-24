# `data/` — committed, reproducible snapshots

Two subtrees, both point-in-time and frozen once written (PRD §6.1).

## `prices/<ASSET>.csv`
Daily OHLCV, `date` column in ISO-8601 UTC. Read by `CSVMarketProvider`.

## `news/<ASSET>.jsonl`
One JSON object per line. Required fields: `news_id`, `published_at` (UTC),
`headline`. Optional: `body`, `source`, `assets`. Read by `JSONLNewsProvider`.
Every item **must** carry a trustworthy `published_at` — untrusted timestamps
are dropped (PRD §6.2), the single biggest guard against accidental lookahead.

## ⚠️ Current contents are SYNTHETIC SAMPLES
The committed files are deterministic placeholders from
`python -m scripts.make_sample_data` (`source: "SYNTHETIC_SAMPLE"`), so the
pipeline, baselines, and the leakage test run with zero network. They are **not**
real market data and carry no real predictive signal. Real snapshots replace
them via the live providers (§6.2): GDELT / Alpha Vantage / CryptoPanic for the
clean window, FNSPID for the historical (contaminated) window.
