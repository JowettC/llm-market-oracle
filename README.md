# llm-market-oracle

**Can an LLM read the news and predict the market?** A rigorous, backtested
experiment measuring LLM directional-prediction skill (up / down / stay) against
the market itself, across daily, weekly, and monthly horizons — for SPY, BTC,
and ETH.

The full design lives in [`PRD.md`](PRD.md). This README is the short version
and the reproduction guide.

---

## The question, honestly asked

Does an LLM, given **only the news that was actually available at a point in
time**, have real skill at predicting whether a market goes up, down, or stays
flat over the next day / week / month — and is that skill good enough to beat
the market itself, after costs?

Most "ChatGPT beats the market" content fails on one of three counts, and this
repo is built to avoid all three:

1. **Lookahead / leakage** — testing on a period the model already saw in
   training. → We test on **post-training-cutoff** news and enforce a central
   point-in-time gate (`published_at < as_of`), guarded by a leakage test that
   fails the build if any future data leaks in.
2. **No honest baseline** — 55% accuracy sounds great until you learn the market
   rises ~53% of days. → We measure against **strong baselines** (always-up,
   stratified-random, momentum, buy-and-hold, off-the-shelf sentiment) and the
   **Pesaran–Timmermann** skill test, never raw accuracy.
3. **No costs / no risk adjustment** — paper profits that vanish after fees. →
   Every economic number is **net of transaction costs**, risk-adjusted
   (Sharpe / Sortino / max drawdown), vs. buy-and-hold.

The honest result may well be humbling — and that's a valid, publishable outcome.

---

## Status

| Phase | State |
|---|---|
| 0. Design sign-off (`PRD.md`) | ✅ |
| **1. Scaffold + data pipeline + leakage test** | ✅ **done** |
| **2. Baselines + backtest engine + committed baseline results** | ✅ **done** |
| 3. LLM harness (Claude Max subscription, no API key) | ⏳ next |
| 4. Full sweep + robustness + probes | ▫️ |
| 5. Analysis + write-up | ▫️ |
| 6. Public-readiness | ▫️ |

Phase 1 ships: the source-agnostic market/news providers, the point-in-time
gate, up/down/stay labeling, the shared prediction schema, all five baselines,
and a leakage test that goes red if future data ever leaks.

Phase 2 ships: the walk-forward engine, the portfolio / costs / execution-lag
economic lens, the full metrics suite (Pesaran-Timmermann, Diebold-Mariano,
Brier, Sharpe / Sortino / max-drawdown, Newey-West HAC), and a one-command run
that produces **committed baseline results** — the market bar the LLM must beat.
See [`results/baseline_results.md`](results/baseline_results.md) and
`results/figures/`. The same-interface Claude predictors slot into the identical
loop in Phase 3.

> ⚠️ The committed `data/` files are **synthetic samples** (deterministic, from
> `scripts/make_sample_data.py`) so everything runs offline with no network.
> They carry no real predictive signal. Real snapshots replace them via the live
> providers in later phases — see [`data/README.md`](data/README.md).

---

## Reproduce (Phases 1–2)

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"        # or: pip install -r requirements.lock.txt

python -m pytest -q                       # 50 tests incl. leakage + ingestion suites
python -m scripts.verify_fairness         # audit the committed news corpus for leakage
python -m src.run                         # baseline sweep -> results/ (md, csv, figures)
#   python -m src.run --smoke             # daily horizon only (quick)

# refresh the committed real snapshots (network; optional):
#   python -m scripts.fetch_real_prices   # SPY (Yahoo) + BTC/ETH (Binance), no key
#   python -m scripts.fetch_real_news     # GDELT corpus, paced (~9 min), no key
```

No secrets, no API keys, no network required. The LLM path (Phase 3) runs on a
**Claude Max subscription via Claude Code** — still no API key (PRD §13.4).

---

## Layout

```
config/experiment.yaml   every knob: assets, horizons, θ band, costs, models, windows
src/
  data/                  market + news providers, and assemble_context.py (THE gate)
  predictors/            shared Prediction schema + the five baselines
  labeling.py            up/down/stay neutral-band logic
  data/gdelt.py          real GDELT news ingestion (leakage-safe seendate)
  data/quality.py        corpus quality gates: dedup, UTC, future-ts guard
  backtest/              walk-forward engine, portfolio, metrics   (Phase 2)
  probes/                lookahead / memorization probes            (Phase 4)
  report/                tables + plots + results markdown          (Phase 5)
data/prices              committed REAL snapshots (Yahoo / Binance)
data/news                committed REAL GDELT corpus + MANIFEST.json provenance
scripts/                 fetch_real_prices, fetch_real_news, verify_fairness
tests/                   unit tests, incl. the leakage test that FAILS on leakage
```

---

## Fairness safeguards (why you can trust the numbers)

- **One gate for all news.** `src/data/assemble_context.py` is the only path
  news reaches a predictor; it enforces `published_at < as_of` centrally and
  records the exact `news_ids` used, so every prediction is auditable.
- **Leakage-safe news timestamps.** Real news comes from GDELT, and we use its
  `seendate` (when GDELT first *observed* the article) as `published_at`. That
  is always **at or after** real publication, so it can only withhold an article
  longer than reality — never reveal it early. See `src/data/gdelt.py`.
- **Quality-gated corpus.** Every fetched item is de-duplicated, forced to UTC,
  and dropped if its timestamp is after the fetch instant (a physically
  impossible article). See `src/data/quality.py` and `data/news/MANIFEST.json`.
- **Auditable in one command.** `python -m scripts.verify_fairness` re-checks the
  committed corpus for future timestamps, gate leakage, and the clean
  (post-cutoff) vs. contaminated split — and exits non-zero on any violation.
- **Post-cutoff clean window** is the only headline. Pre-cutoff runs are labeled
  "contaminated — upper bound" and never blended in.
- **Strong baselines + significance tests**, not raw accuracy.
- **Net-of-cost economics** as the only headline P&L number.

See PRD §7 for the full list.

---

## License & disclaimer

MIT (see `LICENSE`). This is a **research measurement, not financial advice** and
not a trading system. Results are a time-stamped snapshot of a capability, not a
law about markets.
