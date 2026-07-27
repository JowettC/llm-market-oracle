# Baseline backtest results

Committed baseline results — the **market-performance bar** the LLM is measured against (PRD §7.4, §8.4). All economic figures are **net of transaction costs** with next-bar execution lag. `PT p` is the raw one-sided Pesaran-Timmermann market-timing p-value; **`PT q (FDR)` is the Benjamini-Hochberg-adjusted value across all cells, and the stars reflect `q`, not raw `p`** (`*` <0.10, `**` <0.05, `***` <0.01).


## SPY · daily  (high — primary)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 138 | 35.51% | 59.04% | — | — | 0.697 | 0.99 | 1.01 | -9.13% | 12.67% | 1.01 | 12.77% |
| baseline_buy_hold | 138 | 35.51% | 59.04% | — | — | 0.697 | 0.99 | 1.01 | -9.13% | 12.67% | 1.01 | 12.77% |
| baseline_random | 138 | 41.30% | 67.31% | 0.007 | 0.130 | 0.662 | -0.66 | -0.70 | -10.15% | -7.49% | 1.01 | 12.77% |
| baseline_momentum | 138 | 25.36% | 42.17% | 0.936 | 0.984 | 0.779 | -0.13 | -0.12 | -13.54% | -1.56% | 1.01 | 12.77% |
| baseline_sentiment | 138 | 35.51% | 59.04% | — | — | 0.823 | 0.99 | 1.01 | -9.13% | 12.67% | 1.01 | 12.77% |
| claude_opus:P0 | 138 | 36.23% | 49.35% | 0.507 | 0.984 | 0.675 | -0.22 | -0.21 | -15.37% | -2.59% | 1.01 | 12.77% |
| claude_opus:P1 | 138 | 27.54% | 36.99% | 0.984 | 0.984 | 0.705 | -3.41 | -3.01 | -22.93% | -36.62% | 1.01 | 12.77% |
| claude_opus:P2 | 138 | 29.71% | 46.75% | 0.658 | 0.984 | 0.690 | -2.32 | -2.11 | -17.87% | -27.21% | 1.01 | 12.77% |
| claude_opus:P3 | 138 | 29.71% | 46.48% | 0.576 | 0.984 | 0.703 | -1.47 | -1.37 | -15.56% | -19.43% | 1.01 | 12.77% |

## BTC · daily  (high — primary)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 203 | 25.62% | 46.85% | — | — | 0.747 | -0.86 | -0.86 | -39.53% | -34.90% | -0.85 | -34.78% |
| baseline_buy_hold | 203 | 25.62% | 46.85% | — | — | 0.747 | -0.86 | -0.86 | -39.53% | -34.90% | -0.85 | -34.78% |
| baseline_random | 203 | 29.56% | 48.44% | 0.764 | 0.984 | 0.667 | -1.35 | -1.34 | -43.05% | -40.97% | -0.85 | -34.78% |
| baseline_momentum | 203 | 24.14% | 44.14% | 0.901 | 0.984 | 0.845 | -3.21 | -2.74 | -67.39% | -74.35% | -0.85 | -34.78% |
| baseline_sentiment | 203 | 24.63% | 43.81% | 0.934 | 0.984 | 0.801 | -2.20 | -1.95 | -53.98% | -60.41% | -0.85 | -34.78% |
| claude_opus:P0 | 203 | 29.06% | 48.00% | 0.728 | 0.984 | 0.698 | -1.56 | -1.40 | -50.75% | -47.07% | -0.85 | -34.78% |
| claude_opus:P1 | 203 | 31.03% | 54.81% | 0.214 | 0.984 | 0.689 | -0.78 | -0.73 | -43.19% | -31.32% | -0.85 | -34.78% |
| claude_opus:P2 | 203 | 29.06% | 48.54% | 0.936 | 0.984 | 0.701 | -2.15 | -1.96 | -52.41% | -57.98% | -0.85 | -34.78% |
| claude_opus:P3 | 203 | 27.59% | 49.04% | 0.847 | 0.984 | 0.761 | 0.46 | 0.48 | -37.53% | 12.77% | -0.85 | -34.78% |

## ETH · daily  (high — primary)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 203 | 23.65% | 43.64% | — | — | 0.757 | -0.93 | -0.90 | -53.27% | -47.39% | -0.92 | -47.29% |
| baseline_buy_hold | 203 | 23.65% | 43.64% | — | — | 0.757 | -0.93 | -0.90 | -53.27% | -47.39% | -0.92 | -47.29% |
| baseline_random | 203 | 33.00% | 50.00% | 0.566 | 0.984 | 0.667 | -1.77 | -1.67 | -52.67% | -58.10% | -0.92 | -47.29% |
| baseline_momentum | 203 | 25.12% | 46.36% | 0.765 | 0.984 | 0.882 | -2.71 | -2.49 | -73.32% | -79.68% | -0.92 | -47.29% |
| baseline_sentiment | 203 | 23.65% | 43.64% | — | — | 0.964 | -0.93 | -0.90 | -53.27% | -47.39% | -0.92 | -47.29% |
| claude_opus:P0 | 203 | 25.62% | 50.00% | 0.969 | 0.984 | 0.698 | -1.82 | -1.74 | -58.27% | -65.20% | -0.92 | -47.29% |
| claude_opus:P1 | 203 | 30.54% | 58.33% | 0.136 | 0.984 | 0.686 | -1.02 | -0.93 | -50.91% | -47.96% | -0.92 | -47.29% |
| claude_opus:P2 | 203 | 31.03% | 52.58% | 0.641 | 0.984 | 0.686 | -1.33 | -1.19 | -53.44% | -54.43% | -0.92 | -47.29% |
| claude_opus:P3 | 203 | 25.12% | 46.08% | 0.925 | 0.984 | 0.770 | 0.34 | 0.35 | -25.49% | 4.19% | -0.92 | -47.29% |

---
*Data:* **real** prices (SPY via Yahoo, BTC/ETH via Binance) and **real** point-in-time news (GDELT, leakage-safe `seendate`; see `data/news/MANIFEST.json`). Scored on the news-aligned clean window. These are baselines only — the market bar the LLM must beat; no LLM has run yet.

*Why the FDR column matters.* Across many asset×horizon×model cells, ~1 in 20 will look significant by pure chance. Here a **random** baseline lands at raw `p≈0.007` on SPY·daily — a textbook false positive (≈1.1 expected across the 21 testable cells). After the Benjamini-Hochberg correction its `q` rises well above 0.05 and it **loses its stars** — which is the point: headline claims must survive FDR, not a lone raw p-value (PRD §7.6).
