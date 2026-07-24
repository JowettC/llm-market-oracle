# PRD — Can an LLM Read the News and Predict the Market?

**A rigorous, backtested experiment measuring LLM directional-prediction skill (up / down / stay) against the market itself, across daily, weekly, and monthly horizons.**

| | |
|---|---|
| **Owner** | Jowett Chng (GitHub: `JowettC`) |
| **Status** | Draft v1.2 — for review |
| **Last updated** | 2026-07-24 |
| **Changelog** | v1.1 → subscription execution (Claude Max, no keys). v1.2 → two-window timeline, trading-frequency table, monthly downgraded to exploratory, news re-sourced (GDELT/live feeds for clean window; FNSPID historical-only). |
| **Document type** | Product Requirements Document (design + methodology; no code built yet) |
| **Target repo** | `JowettC/llm-market-oracle` (private, may go public) |
| **Assets in scope** | S&P 500 (SPY) + Bitcoin (BTC) + Ethereum (ETH) |
| **Horizons** | Daily, Weekly, Monthly |

---

## 0. TL;DR

We want to answer one question honestly: **does an LLM, given only the news that was actually available at a point in time, have real skill at predicting whether a market goes up, down, or stays flat over the next day / week / month — and is that skill good enough to beat the market itself?**

This document specifies the full experiment: what we predict, how we define "up/down/stay," which models and baselines compete, how we pull data without cheating, the metrics (with a firm recommendation on which to trust), the statistical tests, the backtest design, and how the whole thing lives in a clean, secret-free GitHub repo that can be flipped from private to public.

The single most important design principle running through this document is **avoiding lookahead bias** — the trap where the LLM appears clairvoyant only because the future was baked into its training data. Recent finance research shows this is the make-or-break issue for any LLM forecasting study, and we design around it deliberately (see §7).

**No code has been written and nothing has been committed yet** — this is the plan. Execution follows once the design is approved.

---

## 1. Problem statement & motivation

Markets react to news. The open question is whether a general-purpose LLM can read that news the way a sharp analyst would and translate it into a correct directional call — consistently enough to matter, and cheaply enough to be practical.

There is a lot of hype and a lot of flawed "ChatGPT beats the market" content online. Most of it fails on at least one of three counts:

1. **Lookahead / leakage** — the model was tested on a period it had already seen during training, so it "predicts" events it effectively memorized.
2. **No honest baseline** — a 55% accuracy sounds impressive until you realize the market goes up ~53% of days, so "always predict up" already scores 53%.
3. **No costs, no risk adjustment** — paper returns that evaporate the moment you subtract trading fees and slippage, or that came from one lucky bet.

This experiment is explicitly designed to be the *fair* version of that test: point-in-time news, strong naive baselines, transaction costs, risk-adjusted returns, and proper statistical significance testing. If the LLM has real skill, we should be able to show it survives all of these. If it doesn't, that's an equally valuable and publishable result.

---

## 2. Goals & non-goals

### 2.1 Goals

- Measure LLM **directional accuracy** (up/down/stay) from news, across three assets and three horizons, with statistical significance testing.
- Compare LLM performance to **the market itself** — both as a statistical skill test and as an economic "would this have made money vs. just holding" test.
- Establish honest **baselines** (always-up, random, momentum, sentiment-classifier, coin-flip) so any LLM edge is measured against a fair bar.
- Build the experiment as **reproducible, config-driven, secret-free code** in a GitHub repo that can be published.
- Produce a clear **write-up / README** explaining methodology and results so a third party can trust and rerun them.
- Rigorously **backtest** the chosen methods over a clean post-cutoff out-of-sample window (~12–18 months), plus a long historical *contaminated* window for context, and report the results (§11).

### 2.2 Non-goals

- This is **not** a live trading system or investment product. No real capital, no brokerage integration.
- We are **not** trying to build a proprietary alpha-generating model to keep secret — the point is a fair, reproducible measurement.
- We are **not** doing intraday / high-frequency prediction (sub-daily). Minimum horizon is one trading day.
- We are **not** claiming to predict magnitude precisely — the core task is direction (with an optional confidence/probability output).
- No financial advice is produced or implied. (This experiment is research; nothing here is a recommendation to trade.)

---

## 3. Prior art — what already exists in the market

Before designing our own test, we surveyed the existing academic and industry work. This shaped every major decision below. The short version: **the methods exist, the seminal results are striking but fragile, and the field has converged on a small set of fairness safeguards that most amateur experiments skip.**

### 3.1 The seminal study — Lopez-Lira & Tang, "Can ChatGPT Forecast Stock Price Movements?" (2023–2024)

The reference paper for this whole area. Their method is almost exactly the template we adopt:

- Prompt GPT to act as a financial expert and label a headline **"YES" (good), "NO" (bad), or "UNKNOWN" (uncertain)** for the stock's short-term move, then map to **+1 / −1 / 0**.
- Aggregate scores into a daily long-short portfolio; measure **hit rate** (directional accuracy) and **returns / Sharpe**.
- **Crucially, they tested on news released *after* the model's training cutoff** to avoid lookahead — the exact discipline we enforce.

Headline findings: high hit rates on the initial reaction and a long-short Sharpe that was very high early (2021) but **decayed over time** (Sharpe fell from ~6.5 to ~1.2 by 2024) as the market adapted, and **transaction costs of 20+ bps eliminated the profits**. GPT-4 clearly beat older/simpler models (GPT-2, BERT). This tells us: an edge may exist, but it is fragile, decays, and must be measured net of costs.

### 3.2 STOCKBENCH (2025) — realistic multi-month trading evaluation

A "contamination-free" benchmark that gives LLM agents daily prices, fundamentals, and news for 20 major stocks and has them buy/sell/hold a \$100k portfolio over ~82 trading days. Metrics: **cumulative return, max drawdown, Sortino ratio**. Key result: **most LLMs underperformed a simple buy-and-hold baseline**, and being good at static financial Q&A did *not* translate into good trading. This is our humility check — it directly motivates our strong baselines and cost modeling.

### 3.3 The lookahead-bias literature — the fairness core

A cluster of 2025 finance papers is entirely about the trap we must avoid:

- **"Chronologically Consistent Large Language Models" (ChronoBERT / ChronoGPT)** — models trained *only* on text available up to each point in time, so no future knowledge leaks in. Demonstrates that lookahead bias is real but can be controlled with strict temporal data discipline.
- **"A Test of Lookahead Bias in LLM Forecasts"** and **"Detecting Lookahead Bias in LLM Forecasts"** — propose explicit tests to detect whether an LLM's edge comes from genuine reasoning or from having memorized the future.

Practical takeaways we bake in: **test on post-training-cutoff data**, run **placebo / memorization probes**, and treat any pre-cutoff results as suspect.

### 3.4 Data resources that exist and are usable

- **FNSPID** (Financial News and Stock Price Integration Dataset) — ~15.7M news records, ~4M time-aligned to prices, 1999–2023, openly hosted on GitHub. A strong candidate news corpus for the equity side.
- Numerous **Bitcoin/crypto news-sentiment prediction** studies (aspect-based sentiment → directional BTC forecasts) confirm the crypto side is well-trodden and that news is more predictive for crypto's higher-volatility, 24/7 regime.

### 3.5 Statistical methods that exist for judging directional forecasts

The forecasting literature already has the right tools, which we adopt rather than reinvent:

- **Pesaran–Timmermann test (1992)** — the canonical test of whether directional predictions have genuine market-timing skill beyond chance.
- **Diebold–Mariano test** — for comparing the forecast accuracy of two models (LLM vs. baseline).
- **Brier score** — for evaluating probabilistic/confidence calibration.

### 3.6 What this means for our design

The gap we are filling is **not** inventing a new method — it is running the *fair, multi-asset, multi-horizon, fully-reproducible* version that most public experiments skip. We take Lopez-Lira's prompting template, STOCKBENCH's realism and honest baselines, the lookahead literature's temporal discipline, and the forecasting field's statistical tests, and combine them into one clean study covering equities **and** crypto across three horizons.

---

## 4. Research questions & hypotheses

### 4.1 Primary research questions

- **RQ1 (Skill):** Given only point-in-time news, does an LLM predict next-period direction (up/down/stay) more accurately than naive baselines, at a statistically significant level?
- **RQ2 (Economic value):** Does acting on the LLM's predictions beat buy-and-hold **after** transaction costs, on a risk-adjusted basis?
- **RQ3 (Horizon):** Does predictive skill differ across daily vs. weekly vs. monthly horizons? (Hypothesis: news is more informative at shorter horizons; longer horizons wash out into drift.)
- **RQ4 (Asset class):** Does skill differ between the broad equity index (SPY) and crypto (BTC/ETH)? (Hypothesis: crypto is more news-driven and volatile, so more prediction opportunities but more noise.)
- **RQ5 (Calibration):** When the LLM expresses confidence, is that confidence well-calibrated (does "70% up" happen ~70% of the time)?

### 4.2 Hypotheses (falsifiable, stated up front to avoid p-hacking)

- **H1:** LLM directional accuracy > best naive baseline on at least the daily horizon for at least one asset, significant at p < 0.05 (Pesaran–Timmermann).
- **H2:** After 10 bps round-trip costs, the LLM strategy's Sharpe does **not** exceed buy-and-hold for SPY (i.e., we expect the honest result to be humbling on the index, per STOCKBENCH).
- **H3:** Any edge is larger for crypto than for SPY.
- **H4:** Skill decays over the out-of-sample period (per Lopez-Lira's decay finding).

Pre-registering hypotheses (§14) is itself part of the fairness design — we commit to reporting all of them, including the ones the LLM loses.

---

## 5. Experimental design

### 5.1 Asset universe

| Asset | Instrument | Market hours | Why included |
|---|---|---|---|
| S&P 500 | `SPY` ETF (or `^GSPC` index) | Mon–Fri, US session | Cleanest, deepest, most-studied broad signal; strong upward drift makes for a *hard* fair test |
| Bitcoin | `BTC-USD` | 24/7 | Highly news-driven, volatile; more directional opportunities |
| Ethereum | `ETH-USD` | 24/7 | Second crypto to test cross-asset generalization within crypto |

*Rationale for this pair:* SPY is the "efficient, hard-to-beat" pole; crypto is the "news-sensitive, beatable-in-theory" pole. Contrasting them is more informative than testing either alone.

### 5.2 Prediction horizons — precise definitions

The "up/down/stay" label is defined by the **forward return** over each horizon relative to a **neutral band** (see §5.3). All horizons use the **close-to-close** convention to avoid ambiguity.

| Horizon | Definition (equities) | Definition (crypto) |
|---|---|---|
| **Daily** | Return from today's close → next trading day's close | Return over next 24h (00:00→00:00 UTC) |
| **Weekly** | Return from Friday close → next Friday close (5 trading days) | Return over next 7 calendar days |
| **Monthly** | Return from month-end close → next month-end close (~21 trading days) | Return over next 30 calendar days |

Predictions are made at a **fixed decision time** (e.g., equity daily prediction is generated after market close using only news timestamped before that close; crypto at 00:00 UTC). This fixed cadence prevents cherry-picking when to predict.

**Trading frequency = the horizon (rebalance equals hold period).** How often a decision is made, and how much data that yields, differs sharply by horizon — and this drives statistical power, so it is stated explicitly:

| Horizon | Decision cadence | Sampling | Approx. decisions / yr | Statistical power |
|---|---|---|---|---|
| **Daily** | Every trading day (SPY) / every day (crypto) | **Non-overlapping** — clean | ~252 (SPY), ~365 (crypto) | **High — the primary test** |
| **Weekly** | Rolling, decided frequently but held 5d/7d | **Overlapping**, corrected with Newey-West/HAC (§8.3) | up to ~252 overlapping (or ~52 non-overlapping) | Medium |
| **Monthly** | Rolling, held ~21d/30d | **Overlapping** + HAC, or ~12 non-overlapping | up to ~252 overlapping (or ~12 non-overlapping) | **Low — exploratory only** |

Two consequences we commit to and report honestly:

- **Daily is the workhorse and the primary, high-power test.** Non-overlapping daily returns give hundreds of clean, independent-ish decisions per asset — enough for the Pesaran–Timmermann test to have teeth.
- **Weekly is medium-power** and uses **overlapping** windows (predict often, hold the horizon) with a **Newey-West/HAC correction** (§8.3) to reclaim data points without letting autocorrelation inflate significance. A non-overlapping variant (~52/yr) is reported as a robustness check.
- **Monthly is explicitly downgraded to exploratory.** Over a ~12–18-month clean window (see §11), non-overlapping monthly cadence yields only ~12–18 predictions — far too few for a credible significance claim. We report it with overlapping+HAC to have *any* power, label it exploratory, and lean on the long historical (contaminated) window (§11) if a real monthly conclusion is wanted. We do **not** headline monthly results as if they carried daily-level confidence.

### 5.3 The label — up / down / stay, and the critical "stay" band

A three-way label needs a defensible definition of "stay/flat," otherwise "stay" is never correct (prices essentially never close *exactly* unchanged). We define a **neutral band** using a volatility-scaled threshold:

- Label = **UP** if forward return > +θ
- Label = **DOWN** if forward return < −θ
- Label = **STAY** if −θ ≤ forward return ≤ +θ

where **θ is set per asset and horizon** using one of two configurable methods:

1. **Fixed band** (simple, interpretable): e.g., θ = 0.25% daily SPY, larger for crypto and longer horizons.
2. **Volatility-scaled band** (recommended): θ = *k* × trailing realized volatility of that asset/horizon (e.g., *k* = 0.5), so the band adapts to each regime. This is fairer across assets — a "flat" day for BTC is a much bigger move than for SPY.

The band width is a **pre-registered hyperparameter**, chosen from the *training* period only, never tuned on the test set. We report a sensitivity analysis across a few θ values so results don't hinge on one arbitrary cutoff.

### 5.4 Model output schema

Every prediction the LLM (or a baseline) makes is a structured JSON object — identical schema for all predictors so scoring is uniform:

```json
{
  "asset": "SPY",
  "horizon": "daily",
  "as_of": "2024-03-14T21:00:00Z",
  "prediction": "UP",              // UP | DOWN | STAY
  "confidence": 0.62,               // 0.0–1.0, model's probability for its chosen class
  "prob_up": 0.62,                  // full distribution (optional but preferred)
  "prob_stay": 0.25,
  "prob_down": 0.13,
  "rationale": "Fed minutes signaled...",  // short free-text, for qualitative audit only
  "model": "claude-x / gpt-y / baseline-momentum",
  "news_ids": ["fnspid_00193", "..."]      // provenance: exactly which news items were seen
}
```

The `prob_*` fields enable calibration scoring (Brier). The `news_ids` field is the audit trail proving no future news leaked in.

### 5.5 Prompt design

We test a small, **pre-registered** set of prompt variants (not an open-ended search, to avoid prompt-overfitting):

- **P0 — Zero-shot direct:** "You are a financial analyst. Based only on the news below (all dated on or before {as_of}), will {asset} close higher, lower, or roughly flat over the next {horizon}? Answer UP/DOWN/STAY with a probability." (Lopez-Lira style.)
- **P1 — Chain-of-thought:** same, but instruct step-by-step reasoning before the final label.
- **P2 — Structured/analyst:** provide a light template (macro, sector, sentiment, positioning) to fill before deciding.
- **P3 — Sentiment-only ablation:** headline sentiment only, no reasoning — isolates how much value the "reasoning" adds over pure sentiment.

The full prompt templates live in Appendix A. The prompt set is frozen before the test window is scored.

### 5.6 What the model is (and isn't) allowed to see

**Allowed inputs:** news articles/headlines timestamped strictly **before** the decision time; optionally, past price history up to the decision time (this is a configurable condition — "news-only" vs. "news + recent price context").

**Forbidden inputs:** anything dated after the decision time; any aggregate that secretly encodes the future; the model's own parametric memory of events after its training cutoff (mitigated by testing on post-cutoff data and by memorization probes, §7).

We run two conditions: **(A) news-only** and **(B) news + trailing price/technical context**, so we can attribute skill to the news reading itself vs. generic momentum the model could infer from prices.

---

## 6. Data pipeline

### 6.1 Market (price) data

Daily (and where needed, hourly for crypto) OHLCV for SPY, BTC-USD, ETH-USD.

**Note on data access:** the standard live APIs (Yahoo Finance / `yfinance`, Stooq, FRED) may be network-restricted in some execution environments. The pipeline is therefore built **source-agnostic** behind a small `MarketDataProvider` interface with multiple interchangeable backends:

- `yfinance` / Stooq / Alpha Vantage / Polygon / Tiingo (when live network is available; some need a free API key set via env var — never committed).
- **Static CSV snapshots** committed to the repo under `data/prices/` (or pulled from public GitHub-hosted datasets), so the backtest is fully reproducible offline and does not depend on a flaky live API. This is the default for reproducibility.

Prices are stored point-in-time and **never** revised look-back (we snapshot once and freeze).

### 6.2 News data

**News sourcing is dictated by the two-window timeline (§11): a corpus is only usable for the *clean* window if it extends past the model's training cutoff.** This rules out FNSPID (ends 2023) for the primary test — a recent-cutoff Claude model would already have seen 2023 news, making it contaminated. FNSPID is therefore reassigned to the historical (contaminated) window and to baseline development, and the **clean window is fed by recent, precisely-timestamped live feeds.**

| Window | Source | Coverage | Role |
|---|---|---|---|
| **Clean (primary)** | **GDELT 2.0** | Global, 15-min granularity, ~2015→present, exact publish timestamps, free | **Backbone** for the post-cutoff clean test |
| **Clean (primary)** | **Alpha Vantage `NEWS_SENTIMENT`** (free tier) or Finnhub / Marketaux / NewsAPI | Finance-focused, ~2022→present, timestamped | Finance-targeted layer on top of GDELT |
| **Clean — crypto** | **CryptoPanic API** + CoinDesk / CoinTelegraph RSS, GDELT crypto slices | ~real-time, timestamped | BTC/ETH news for the clean window |
| **Historical (contaminated)** | **FNSPID** (GitHub, `Zdong104/FNSPID_Financial_News_Dataset`) | ~15.7M records, 1999–2023, price-aligned | Long-history run labeled *"contaminated — upper bound,"* baseline development, chronologically-consistent open-model tests |

**Hard requirement:** every news item must carry a **reliable publication timestamp**. Items without trustworthy timestamps are dropped — a wrong timestamp is the single biggest source of accidental lookahead. All feeds are pulled behind one `NewsDataProvider` interface so the clean-vs-historical corpus is a config switch, not a code change.

**Caveat:** free-tier rate limits and terms on the live feeds (GDELT, Alpha Vantage, CryptoPanic, etc.) change over time and are verified at build time; the repo pins whichever it actually used and snapshots the pulled news to `data/news/` so the backtest stays reproducible even if a feed's terms later change.

### 6.3 Timestamp alignment & market-hours handling

- **Equity overnight vs. intraday:** news released after close is attributed to the *next* session's prediction (the Lopez-Lira overnight/intraday split). Prediction `as_of` is the decision timestamp; only news with `published_at < as_of` is admissible.
- **Crypto 24/7:** no market-hours gap; the 00:00 UTC decision boundary is used consistently.
- **Weekend/holiday gaps (equities):** Friday→Monday news accumulates into the Monday (or next-trading-day) prediction.
- A single **`assemble_context(as_of, asset, horizon)`** function is the *only* way news reaches the model, and it enforces the `published_at < as_of` filter centrally. Every prediction records the `news_ids` it used so leakage is auditable after the fact.

### 6.4 Data-quality checks (run before any scoring)

Corporate actions/splits adjusted; duplicate news deduped; survivorship not an issue (index ETF + top-2 crypto, no delisting); missing days flagged; timezone normalized to UTC everywhere.

---

## 7. Fair-testing safeguards — avoiding lookahead bias (the core of the whole study)

This is the section that separates this experiment from the pile of "ChatGPT beats the market" posts. Every safeguard maps to a specific failure mode.

### 7.1 Point-in-time everything
The `as_of < published_at` filter is enforced centrally (§6.3). No feature, price, or news item dated after the decision time can enter a prediction. Every prediction stores its exact input provenance (`news_ids`, price-as-of) for post-hoc audit.

### 7.2 Post-training-cutoff test window (the two-window design)
The **primary** out-of-sample evaluation window is restricted to dates **after the pinned model's known training cutoff** (the *clean window*). This is the single strongest defense against the model "remembering" outcomes, and it is exactly what the seminal literature does. Because a current frontier Claude model has a recent cutoff, the clean window is realistically **~12–18 months** (cutoff → latest available news), which is ample for the daily horizon and thin for monthly (§5.2, §11). Any run on dates at or before the cutoff (e.g., the long FNSPID history) is the *contaminated window*, reported only as an **"upper bound"** and never mixed into the headline number. See §11 for how the two windows are used together.

### 7.3 Memorization / placebo probes
Borrowed from the "Test of Lookahead Bias" literature:
- **Date-masking probe:** strip explicit dates from the news and see if performance drops (if it drops a lot, the model was keying on remembered dates).
- **Placebo news probe:** feed news from a *different* random date and check the model doesn't still "predict" the real outcome (it shouldn't have skill on mismatched news).
- **Future-event trivia probe:** directly ask the model outcome-revealing questions about the test period to gauge how much it already knows; discount overlapping periods.

### 7.4 Strong, honest baselines (the "market performance general" bar)
The LLM must beat these, not just beat 33% random:

| Baseline | What it is | Why it matters |
|---|---|---|
| **Always-UP** | Predict UP every period | Exploits equities' upward drift; deceptively strong for SPY |
| **Random (stratified)** | Sample from the historical class frequency | Honest chance level given class imbalance |
| **Momentum** | Predict continuation of last period's move | The classic "dumb" technical signal |
| **Buy-and-hold** | Just hold the asset | The economic benchmark for RQ2 — "why not just index?" |
| **Lexicon/FinBERT sentiment** | Classic news-sentiment classifier → direction | Isolates whether the LLM adds value over off-the-shelf sentiment |

### 7.5 No test-set tuning
Band width θ, prompt choice, and any hyperparameters are fixed using only the **training/validation** period. The test window is scored **once** at the end. Walk-forward design (§8) enforces this structurally.

### 7.6 Multiple-comparisons discipline
We test many asset × horizon × prompt × condition cells. To avoid "something will look significant by chance," we (a) pre-register the primary cells (H1–H4), and (b) apply a Benjamini–Hochberg false-discovery-rate correction across the secondary cells.

### 7.7 Costs & realism
All economic results are reported **net of transaction costs** (configurable, default 10 bps round-trip for SPY, higher for crypto) and with a realistic execution lag (act on the prediction at the next available price, not the same close it was computed from). Per Lopez-Lira, costs alone can erase the entire edge — so gross-only numbers are considered misleading and are never headlined.

---

## 8. Backtesting methodology

### 8.1 Walk-forward, out-of-sample
The backtest is **walk-forward**: predictions are generated sequentially through time; nothing downstream of a decision date informs it. There is no in-sample fitting of the LLM (it's used zero/few-shot); the only "training" is baseline calibration and θ selection, done on an earlier, disjoint window.

```
|<---- calibration window ---->|<-------- out-of-sample test window -------->|
   (set θ, pick prompt,           (score every prediction once, walk-forward,
    calibrate baselines)           post-training-cutoff dates only)
```

### 8.2 Two evaluation lenses (both reported)

**Lens 1 — Statistical skill (answers RQ1/RQ3/RQ4/RQ5):** treat each prediction as a classification; score accuracy, per-class precision/recall, confusion matrices, Brier score; test significance with Pesaran–Timmermann and compare models with Diebold–Mariano.

**Lens 2 — Economic value (answers RQ2):** convert predictions into positions (UP → long, DOWN → short or flat, STAY → flat), size them (equal-weight or confidence-weighted, configurable), apply costs and execution lag, and compute the equity curve. Compare to buy-and-hold.

### 8.3 Position/return construction
- UP → +1 unit long; DOWN → −1 (or 0 in a long-only variant); STAY → 0.
- Optional **confidence weighting**: position ∝ (confidence − 0.5).
- Returns compounded over the horizon. **Sampling follows §5.2:** the **daily** horizon is non-overlapping (clean); **weekly and monthly** use overlapping windows with **Newey-West/HAC-adjusted** standard errors so the induced autocorrelation cannot inflate significance. Each horizon also reports its non-overlapping variant as a robustness check, and monthly is flagged **exploratory / low-power** in every table (§5.2).

### 8.4 What "backtest results" will report
For every asset × horizon × model, a results table + plots:
- Directional accuracy vs. each baseline (with PT test p-value)
- Confusion matrix and per-class F1
- Brier score / calibration curve
- Net-of-cost cumulative return, CAGR, **Sharpe**, **Sortino**, **max drawdown**, hit rate, turnover
- Equity curve vs. buy-and-hold
- Rolling-window skill (to detect decay, H4)

> **On actually running the backtest:** the full LLM-in-the-loop backtest requires (a) LLM access and (b) the news corpus, and is run by the user in their own environment. **LLM access here is the Claude Max subscription — no API key** (§13.4): the harness calls Claude through Claude Code's headless mode / the Agent SDK, authenticated by the user's Claude login. The repo ships the complete runnable harness plus the **baseline backtests**, which need no LLM access at all and produce real, committed results that establish the "market performance general" bar the LLM is measured against. In other words, the benchmark half of the backtest runs out-of-the-box; the LLM half runs against the Max subscription, paced within its usage limits (§13.4).

---

## 9. Models under test

Configured via a provider-agnostic `Predictor` interface so any model can be slotted in.

**Execution decision: this study runs on a Claude Max subscription, not API keys** (see §13.4 for the mechanics). That has one important scoping consequence:

- **Primary models = Claude family** (e.g., Opus / Sonnet variants), driven through the subscription via Claude Code headless mode / the Claude Agent SDK. No API key, no per-token billing — usage draws from the Max plan's limits.
- **Cross-vendor models (GPT-class, Gemini-class) become optional/out-of-scope** unless separate access is added later, because a Claude subscription only authenticates Claude models. This is fine: the core research questions (does an LLM read news into a correct directional call?) are fully answerable with Claude model variants, and comparing *across Claude tiers* (e.g., a smaller vs. larger model) is itself a useful axis.
- **Open models (optional):** a Llama/Qwen-class model run locally remains available for a fully-offline comparison and for *chronologically-consistent* (ChronoGPT-style) variants — these need no subscription and no key.
- **Baselines:** all of §7.4 (need no LLM access at all).

Each model is pinned to a **specific version string** and its **training cutoff** is recorded, because the post-cutoff test window (§7.2) depends on it. For the Claude models this is read from the model card at run time and logged with every prediction.

---

## 10. Metrics — and my recommendation

You asked which success metric is best. **Recommendation: use all three tiers below, but treat them as answering different questions — do not collapse them into one number.** Here's the reasoning and the priority order.

### 10.1 Recommended primary metric — directional accuracy with a significance test
**Use directional accuracy as the primary *scientific* metric, but always judged against the best naive baseline and tested with Pesaran–Timmermann, not reported raw.** Raw accuracy is misleading because of class imbalance (markets drift up, so "always-UP" is a strong bar). The honest question isn't "what % correct" but "**is it significantly more correct than the best dumb rule?**" This directly answers "does the LLM have real skill."

### 10.2 Recommended primary metric — net-of-cost, risk-adjusted return vs. buy-and-hold
**Use cumulative return + Sharpe/Sortino, net of costs, vs. buy-and-hold, as the primary *economic* metric.** This is the literal "beat the market" test (RQ2). Accuracy can be high while returns are poor (many tiny correct calls, a few huge wrong ones) — so P&L is a necessary second lens. Report **Sharpe and Sortino** (risk-adjusted), **max drawdown** (tail risk), and the equity curve, because a raw return number hides how much risk bought it. This is exactly the STOCKBENCH lens, and STOCKBENCH's finding — most LLMs lose to buy-and-hold — is why we insist on it.

### 10.3 Recommended supporting metric — calibration (Brier score)
**Use the Brier score / calibration curve to judge whether the model's stated confidence is trustworthy.** A model that says "80% up" and is right 80% of the time is far more useful than one that's overconfident, even at equal accuracy. Cheap to add, and it's what separates a usable signal from a lucky one.

### 10.4 Why not just pick one?
- **Accuracy alone** → fooled by class imbalance and by magnitude (small right calls, big wrong ones).
- **P&L alone** → noisy; a single lucky trade can dominate; not statistically interpretable.
- **Together** → "statistical skill" (§10.1) and "economic value" (§10.2) can and do diverge, and *that divergence is itself the interesting finding.* Reporting both, plus calibration, is the honest answer to your question.

### 10.5 Full metric list

| Tier | Metric | Answers |
|---|---|---|
| Primary (skill) | Directional accuracy vs. baseline + **Pesaran–Timmermann** p-value | RQ1, RQ3, RQ4 |
| Primary (economic) | Net-of-cost cumulative return, **Sharpe, Sortino**, max drawdown vs. buy-and-hold | RQ2 |
| Supporting | **Brier score** / reliability curve | RQ5 |
| Supporting | Precision/recall/F1 per class, confusion matrix | class-level behavior |
| Supporting | **Diebold–Mariano** (model vs. model) | is model A better than B |
| Supporting | Turnover, hit rate, rolling skill | costs, decay (H4) |

---

## 11. Experiment scale ("the amount")

Since you left the scale to me, here's a defensible default that's large enough to be credible and small enough to actually run:

- **Assets:** 3 (SPY, BTC, ETH)
- **Horizons:** 3 (daily = primary/high-power, weekly = medium, monthly = exploratory/low-power; see §5.2)
- **Prompt variants:** 4 (P0–P3)
- **Input conditions:** 2 (news-only, news+price)
- **Models:** Claude family (≥2 tiers) + 5 baselines (§9)
- **Robustness:** 3 band-width (θ) settings for sensitivity; rolling sub-periods for decay.

**The two-window timeline (this is the key fix):**

| Window | Dates | News source | Role & power |
|---|---|---|---|
| **A — Clean (primary)** | Pinned model's training cutoff → latest news (~**12–18 months** for a current Claude model) | Recent live feeds: GDELT + finance/crypto layers (§6.2) | **The headline result.** ~250–540 daily decisions/asset — strong for daily, medium for weekly, thin for monthly |
| **B — Historical (contaminated)** | ~1999–2023 | FNSPID (§6.2) | **"Upper bound only"**, never headlined. Gives long-horizon (incl. monthly) *context* and develops/validates baselines; also the window for chronologically-consistent open models |

Why not just "2–3 years post-cutoff"? Because a *current* frontier Claude model hasn't existed for 2–3 years past its cutoff — you cannot have both "newest model" and "long clean history." Window A is therefore intentionally short and honest; Window B supplies length at the cost of contamination, and the two are never blended in a headline number.

That's **3 × 3 × 4 × 2 = 72 core LLM cells** per model before robustness — comprehensive, but bounded. Daily predictions dominate the call volume; a caching layer (§13.3) keeps it tractable, and weekly/monthly cells are cheap.

**Because execution is on a Max subscription (§13.4), the binding constraint is usage limits, not dollars.** A full daily sweep is thousands of Claude calls, and Max limits are shared with your normal Claude usage and reset on a rolling window. Practical implications: (a) **cache aggressively** so no prediction is ever recomputed; (b) **run the sweep in paced batches spread across reset windows** rather than one burst; (c) start with a **reduced smoke-test scope** (one asset, one horizon, a few months) to validate before the full run; (d) if even the ~12–18-month clean daily sweep is too large for the plan's limits, prioritize by scientific value — daily crypto and daily SPY first (highest news sensitivity / cleanest tests), then weekly, then monthly. This staging is a config setting, not a code change.

---

## 12. Repository structure & GitHub plan

Everything below is the **plan** to be implemented; nothing is committed yet. The repo is designed to be safe to make public at any time.

### 12.1 Target repo
`JowettC/llm-market-oracle` — **private** initially, structured so flipping to public requires zero cleanup (no secrets ever enter git history).

### 12.2 Proposed directory layout

```
llm-market-oracle/
├── README.md                  # the plain-language explainer (see §12.5)
├── PRD.md                     # this document
├── LICENSE                    # MIT (permissive; fine for public research)
├── .gitignore                 # ignores .env, data caches, keys, __pycache__, results/*.raw
├── .env.example               # documents needed env vars WITHOUT values
├── pyproject.toml             # deps: pandas, numpy, scipy, statsmodels, matplotlib, httpx, pydantic
├── config/
│   └── experiment.yaml        # all knobs: assets, horizons, θ, costs, models, windows
├── src/
│   ├── data/
│   │   ├── market_providers.py    # yfinance/stooq/CSV backends behind one interface
│   │   ├── news_providers.py      # FNSPID + crypto loaders
│   │   └── assemble_context.py    # THE point-in-time gatekeeper (§6.3)
│   ├── predictors/
│   │   ├── base.py                # Predictor interface + JSON schema (§5.4)
│   │   ├── llm_predictor.py       # provider-agnostic LLM caller (keys from env only)
│   │   └── baselines.py           # always-up, random, momentum, sentiment, buy&hold
│   ├── labeling.py                # up/down/stay band logic (§5.3)
│   ├── backtest/
│   │   ├── walk_forward.py
│   │   ├── portfolio.py           # positions, costs, execution lag
│   │   └── metrics.py             # accuracy, PT test, DM test, Sharpe, Sortino, Brier
│   ├── probes/                    # lookahead/memorization probes (§7.3)
│   └── report/                    # tables + plots + results markdown generator
├── data/
│   ├── prices/                    # committed CSV snapshots (small, reproducible)
│   └── news/                      # loaders/pointers; large corpora git-ignored or via LFS
├── results/                       # committed baseline results + generated figures
├── notebooks/                     # exploratory analysis
└── tests/                         # unit tests, incl. a leakage test that FAILS if future data leaks
```

### 12.3 Secrets policy (non-negotiable)
- **No API keys, tokens, or credentials in git — ever.** All secrets come from environment variables or an untracked local `.env`.
- `.gitignore` excludes `.env`, `*.key`, `credentials*`, and result artifacts that might embed keys.
- `.env.example` documents *which* variables are needed with **no values**. Note: the **LLM path needs no key** — Claude runs on the Max subscription via Claude Code login state (§13.4), which lives outside the repo. `.env.example` therefore lists only *optional* keys the user might add later (e.g. `POLYGON_API_KEY` for a live price feed, or `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` only if switching to API billing or a non-Claude model).
- A pre-commit hook (e.g. `gitleaks` / `detect-secrets`) scans staged changes so a key can't slip in. Recommended before the first public flip.
- Because history matters for a repo that may go public: if a secret is *ever* committed by accident, it must be rotated and history rewritten before publishing.

### 12.4 Branching / workflow
`main` protected; work on feature branches; PRs with the test suite (including the **leakage test**) required to pass. Conventional commits. Tag releases (`v0.1-baselines`, `v1.0-full-study`).

### 12.5 The README (the "markdown explaining everything")
Plain-language, results-forward, structured as: what the project asks → how it's tested fairly (the lookahead story) → how to reproduce (`pip install`, set `.env`, `python -m src.run`) → **the headline results tables and equity-curve charts** → honest limitations → references. It should let a skeptical stranger rerun the baselines in minutes and trust the numbers. This PRD is committed alongside it as the deep-dive design doc.

### 12.6 Reproducibility
Fixed random seeds; pinned dependency versions; pinned model version strings; committed price snapshots; a single `make reproduce` / `python -m src.run --config config/experiment.yaml` entry point that regenerates every table and figure in the README from scratch.

---

## 13. Technical notes

### 13.1 Language & libraries
Python 3.11+. `pandas`/`numpy` (data), `scipy`/`statsmodels` (PT test, DM test, Newey-West), `matplotlib` (plots), `pydantic` (schema validation), `httpx` (API calls), `pytest` (tests). No heavyweight ML framework needed — the LLMs are called via API, baselines are simple.

### 13.2 Determinism with LLMs
LLM calls use `temperature=0` where supported and are **cached to disk keyed by (model, prompt, news_ids)** so a rerun is deterministic and doesn't re-spend usage. The cache is git-ignored (can be large) but its hash manifest can be committed for verification. Under a subscription (§13.4) this caching is doubly important, because every avoided call is preserved usage quota.

### 13.3 Usage / rate-limit control
Response caching (above); run cheap horizons in batches; start with one asset/one horizon smoke test before the full sweep; a `--dry-run` mode that reports the number of Claude calls a run will make **before** executing, so you can size it against your remaining limit; automatic **retry-with-backoff on rate-limit responses** and a **checkpoint/resume** so a sweep interrupted by a usage-limit reset picks up exactly where it stopped rather than restarting.

### 13.4 Running on a Claude Max subscription (no API key)
The LLM predictor authenticates through the user's **Claude Max subscription**, not a Platform API key. Two officially-supported mechanisms (either works; the harness wraps whichever is installed behind the `Predictor` interface):

- **Claude Code headless mode** — invoke `claude -p "<prompt>"` (print/non-interactive mode) as a subprocess and capture the JSON reply. Authenticated by logging in with your Claude credentials (`claude` then `/login`; if an `ANTHROPIC_API_KEY` is set, `/logout` and re-login to switch to subscription auth).
- **Claude Agent SDK** with subscription auth — the SDK can run against your Claude plan rather than an API key.

Key facts and caveats baked into the design (verified against Anthropic's current help center):

- As of the June 15, 2026 pause of the announced billing change, **Agent SDK and `claude -p` usage draws from your subscription's usage limits** — no separate credits required, no per-token bill.
- **Limits are shared** across Claude web/apps and Claude Code combined and reset on a rolling window; exceeding them means waiting for reset (or optionally enabling usage credits at API rates, or upgrading tier). The harness is built to respect this (backoff + resume, §13.3).
- **Use only Anthropic's official tooling** (Claude Code / Agent SDK) for subscription auth. Third-party proxies that repackage a subscription as a generic API are against Anthropic's usage policy and are explicitly out of scope here.
- **No credentials in the repo.** Subscription auth lives in the local Claude Code login state on the user's machine, never in git. `.env.example` therefore lists *no* `ANTHROPIC_API_KEY` for the LLM path (it remains optional only if the user later wants API billing or a non-Claude model).
- Because product/billing details in this area change, the README notes the verification date and links Anthropic's "Use Claude Code with your Pro or Max plan" and "Use the Claude Agent SDK with your Claude plan" help articles as the source of truth.

---

## 14. Pre-registration & scientific integrity

Before scoring the test window, we commit (in-repo, timestamped) to: the hypotheses (§4.2), the primary cells, the band-width θ, the prompt set, the cost assumptions, and the metrics. This prevents post-hoc story-fitting. **All** pre-registered results are reported — including the ones where the LLM loses to buy-and-hold (which, per STOCKBENCH, is a likely and legitimate outcome for SPY).

---

## 15. Risks, limitations & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Lookahead / memorization** | Fake skill | Post-cutoff window, point-in-time gate, memorization probes (§7) |
| **News timestamp errors** | Silent leakage | Drop untrustworthy timestamps; central gate; provenance logging |
| **Class imbalance** | Inflated accuracy | Baselines + PT test, not raw accuracy |
| **Multiple comparisons** | False positives | Pre-registration + FDR correction |
| **Transaction costs ignored** | Illusory profit | Net-of-cost as the only headline economic number |
| **Overlapping-horizon autocorrelation** | Overstated significance | Non-overlapping sampling / Newey-West |
| **Live data-API blocking** | Can't pull prices | CSV snapshot backend; source-agnostic provider |
| **Hitting Max usage limits** | Sweep stalls | Aggressive caching, paced batches across reset windows, checkpoint/resume, dry-run call-count estimate, staged scope (§11, §13.3–13.4) |
| **Subscription-auth policy** | ToS risk | Use only official Claude Code / Agent SDK; no third-party proxy repackaging (§13.4) |
| **Skill decay over time** | Non-stationary result | Rolling-window reporting; treat results as time-stamped, not eternal |
| **Survivorship / corporate actions** | Biased prices | Adjusted prices; index ETF + top-2 crypto avoids delisting |

### 15.1 Honest limitations to state in the README
Results are specific to the tested period and models; LLMs and markets both drift, so numbers are a snapshot, not a law. Three assets is breadth-limited by design. News corpora have their own coverage biases. And nothing here is investment advice — it's a measurement of a capability, not a trading recommendation.

---

## 16. Milestones & phases

| Phase | Deliverable | Notes |
|---|---|---|
| **0. Design sign-off** | This PRD approved | ← we are here |
| **1. Scaffold + data** | Repo, config, market/news providers, point-in-time gate, leakage test passing | No LLM calls yet |
| **2. Baselines + backtest engine** | All baselines, walk-forward engine, metrics, **committed baseline results** | Runs with no API key; establishes the market bar |
| **3. LLM harness** | `llm_predictor`, prompt templates, caching | Runs on your Max subscription via Claude Code `-p` / Agent SDK (§13.4); no API key |
| **4. Full sweep** | 72-cell run, robustness, probes | The main experiment |
| **5. Analysis + write-up** | Results tables, figures, README, decay analysis | The publishable artifact |
| **6. Public-readiness** | Secret scan, history check, license, polish | Flip private → public |

---

## 17. Success criteria for the *experiment* (not the LLM)

The project succeeds if it produces a **trustworthy, reproducible answer** — regardless of whether that answer flatters the LLM:

- Every headline number is out-of-sample, post-cutoff, net-of-cost, and significance-tested.
- A stranger can clone the repo and reproduce the baseline results without secrets.
- The README states clearly, for each asset × horizon, whether the LLM (a) has statistically significant directional skill and (b) beats buy-and-hold after costs — with the caveats.
- Lookahead probes pass (no evidence the edge is memorization).

A result of *"the LLM does **not** reliably beat the market on SPY but shows a small significant edge on crypto at the daily horizon that decays over time"* would be a complete, valuable, honest success.

---

## Appendix A — Prompt templates (P0 zero-shot)

```
System: You are a disciplined financial analyst. You only use the information
provided. You never assume knowledge of events after the stated cutoff.

User:
Asset: {asset}
Decision time (cutoff): {as_of} UTC
Horizon: over the next {horizon}, will the CLOSE be higher, lower, or roughly flat
(within ±{theta}) versus now?

Below are news items, ALL published on or before the cutoff. Use only these.
--- NEWS ---
{news_block}
------------

Respond ONLY as JSON:
{"prediction":"UP|DOWN|STAY","prob_up":..,"prob_stay":..,"prob_down":..,
 "confidence":..,"rationale":"<=40 words"}
```

## Appendix B — Key metric definitions

- **Directional accuracy** = correct labels / total labels.
- **Pesaran–Timmermann (1992)** = test statistic for whether predicted and realized directions are independent (H0: no market-timing skill); reject → genuine directional skill.
- **Sharpe** = mean(excess return) / std(excess return), annualized. **Sortino** = same but downside deviation only.
- **Max drawdown** = largest peak-to-trough equity decline.
- **Brier score** = mean squared error between predicted class probabilities and realized one-hot outcome; lower = better-calibrated.
- **Diebold–Mariano** = test of equal predictive accuracy between two forecasters.

## Appendix C — References (surveyed for this design)

1. Lopez-Lira, A. & Tang, Y. — *Can ChatGPT Forecast Stock Price Movements? Return Predictability and Large Language Models.* arXiv:2304.07619.
2. *STOCKBENCH: Evaluating LLMs in Realistic Stock Trading.* stockbench.github.io (2025).
3. He, S., Lv, L., Manela, A., Wu, J. — *Chronologically Consistent Large Language Models (ChronoBERT/ChronoGPT).* arXiv:2502.21206.
4. Gao, Z., Jiang, W., Yan, Y. — *A Test of Lookahead Bias in LLM Forecasts* / *Detecting Lookahead Bias in LLM Forecasts.* arXiv:2512.23847.
5. Dong, Z. et al. — *FNSPID: A Comprehensive Financial News Dataset in Time Series.* arXiv:2402.06698; GitHub `Zdong104/FNSPID_Financial_News_Dataset`.
6. Pesaran, M.H. & Timmermann, A. (1992) — *A Simple Nonparametric Test of Predictive Performance.*
7. Diebold, F.X. & Mariano, R.S. (1995) — *Comparing Predictive Accuracy.*

---

*End of PRD v1.0. This is a design document — no code, repo, or backtest has been created yet. Next step on approval: Phase 1 (scaffold + data pipeline + leakage test).*
