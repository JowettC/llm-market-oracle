# Baseline backtest results

Committed baseline results — the **market-performance bar** the LLM is measured against (PRD §7.4, §8.4). All economic figures are **net of transaction costs** with next-bar execution lag. `PT p` is the raw one-sided Pesaran-Timmermann market-timing p-value; **`PT q (FDR)` is the Benjamini-Hochberg-adjusted value across all cells, and the stars reflect `q`, not raw `p`** (`*` <0.10, `**` <0.05, `***` <0.01).


## SPY · daily  (high — primary)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 138 | 35.51% | 59.04% | — | — | 0.697 | 0.99 | 1.01 | -9.13% | 12.67% | 1.01 | 12.77% |
| baseline_buy_hold | 138 | 35.51% | 59.04% | — | — | 0.697 | 0.99 | 1.01 | -9.13% | 12.67% | 1.01 | 12.77% |
| baseline_random | 138 | 41.30% | 67.31% | 0.007 | 0.143 | 0.662 | -0.66 | -0.70 | -10.15% | -7.49% | 1.01 | 12.77% |
| baseline_momentum | 138 | 25.36% | 42.17% | 0.936 | 1.000 | 0.779 | -0.13 | -0.12 | -13.54% | -1.56% | 1.01 | 12.77% |
| baseline_sentiment | 138 | 35.51% | 59.04% | — | — | 0.823 | 0.99 | 1.01 | -9.13% | 12.67% | 1.01 | 12.77% |

## SPY · weekly  (medium)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 134 | 34.33% | 54.76% | — | — | 0.703 | 1.41 | 1.66 | -5.79% | 15.75% | 1.43 | 15.87% |
| baseline_buy_hold | 134 | 34.33% | 54.76% | — | — | 0.703 | 1.41 | 1.66 | -5.79% | 15.75% | 1.43 | 15.87% |
| baseline_random | 134 | 30.60% | 48.00% | 0.721 | 1.000 | 0.667 | -1.88 | -1.77 | -8.50% | -14.47% | 1.43 | 15.87% |
| baseline_momentum | 134 | 29.10% | 46.43% | 0.766 | 1.000 | 0.779 | -0.13 | -0.13 | -6.64% | -0.14% | 1.43 | 15.87% |
| baseline_sentiment | 134 | 34.33% | 54.76% | — | — | 0.871 | 1.41 | 1.66 | -5.79% | 15.75% | 1.43 | 15.87% |

## SPY · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 118 | 34.75% | 56.94% | — | — | 0.701 | 0.99 | 3.05 | -3.93% | 21.83% | 1.00 | 21.97% |
| baseline_buy_hold | 118 | 34.75% | 56.94% | — | — | 0.701 | 0.99 | 3.05 | -3.93% | 21.83% | 1.00 | 21.97% |
| baseline_random | 118 | 42.37% | 57.14% | 0.413 | 1.000 | 0.781 | 1.23 | 4.70 | -0.05% | 0.98% | 1.00 | 21.97% |
| baseline_momentum | 118 | 27.97% | 45.83% | 0.784 | 1.000 | 0.877 | -1.22 | -0.90 | -11.49% | -22.81% | 1.00 | 21.97% |
| baseline_sentiment | 118 | 34.75% | 56.94% | — | — | 0.903 | 0.99 | 3.05 | -3.93% | 21.83% | 1.00 | 21.97% |

## BTC · daily  (high — primary)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 203 | 25.62% | 46.85% | — | — | 0.747 | -0.86 | -0.86 | -39.53% | -34.90% | -0.85 | -34.78% |
| baseline_buy_hold | 203 | 25.62% | 46.85% | — | — | 0.747 | -0.86 | -0.86 | -39.53% | -34.90% | -0.85 | -34.78% |
| baseline_random | 203 | 29.56% | 48.44% | 0.764 | 1.000 | 0.667 | -1.35 | -1.34 | -43.05% | -40.97% | -0.85 | -34.78% |
| baseline_momentum | 203 | 24.14% | 44.14% | 0.901 | 1.000 | 0.845 | -3.21 | -2.74 | -67.39% | -74.35% | -0.85 | -34.78% |
| baseline_sentiment | 203 | 24.63% | 43.81% | 0.934 | 1.000 | 0.801 | -2.20 | -1.95 | -53.98% | -60.41% | -0.85 | -34.78% |

## BTC · weekly  (medium)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 197 | 30.46% | 48.00% | — | — | 0.723 | -1.25 | -1.02 | -36.91% | -47.55% | -1.24 | -47.40% |
| baseline_buy_hold | 197 | 30.46% | 48.00% | — | — | 0.723 | -1.25 | -1.02 | -36.91% | -47.55% | -1.24 | -47.40% |
| baseline_random | 197 | 32.49% | 55.07% | 0.283 | 1.000 | 0.673 | 2.47 | 3.58 | -13.96% | 139.28% | -1.24 | -47.40% |
| baseline_momentum | 197 | 36.04% | 56.80% | 0.068 | 0.716 | 0.870 | 1.70 | 2.35 | -10.72% | 92.05% | -1.24 | -47.40% |
| baseline_sentiment | 197 | 17.26% | 25.21% | 1.000 | 1.000 | 0.860 | -4.14 | -3.20 | -58.12% | -81.29% | -1.24 | -47.40% |

## BTC · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 174 | 16.67% | 30.21% | — | — | 0.792 | -1.70 | -1.84 | -21.94% | -44.82% | -1.68 | -44.61% |
| baseline_buy_hold | 174 | 16.67% | 30.21% | — | — | 0.792 | -1.70 | -1.84 | -21.94% | -44.82% | -1.68 | -44.61% |
| baseline_random | 174 | 38.51% | 62.71% | 0.731 | 1.000 | 0.684 | -0.15 | -0.12 | -17.48% | -12.07% | -1.68 | -44.61% |
| baseline_momentum | 174 | 25.29% | 45.83% | 0.395 | 1.000 | 1.168 | 0.14 | 0.11 | -30.00% | -27.85% | -1.68 | -44.61% |
| baseline_sentiment | 174 | 1.72% | 2.30% | 1.000 | 1.000 | 0.943 | -2.52 | -1.84 | -36.14% | -65.92% | -1.68 | -44.61% |

## ETH · daily  (high — primary)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 203 | 23.65% | 43.64% | — | — | 0.757 | -0.93 | -0.90 | -53.27% | -47.39% | -0.92 | -47.29% |
| baseline_buy_hold | 203 | 23.65% | 43.64% | — | — | 0.757 | -0.93 | -0.90 | -53.27% | -47.39% | -0.92 | -47.29% |
| baseline_random | 203 | 33.00% | 50.00% | 0.566 | 1.000 | 0.667 | -1.77 | -1.67 | -52.67% | -58.10% | -0.92 | -47.29% |
| baseline_momentum | 203 | 25.12% | 46.36% | 0.765 | 1.000 | 0.882 | -2.71 | -2.49 | -73.32% | -79.68% | -0.92 | -47.29% |
| baseline_sentiment | 203 | 23.65% | 43.64% | — | — | 0.964 | -0.93 | -0.90 | -53.27% | -47.39% | -0.92 | -47.29% |

## ETH · weekly  (medium)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 197 | 22.34% | 40.74% | — | — | 0.763 | -1.35 | -1.19 | -52.59% | -62.30% | -1.34 | -62.20% |
| baseline_buy_hold | 197 | 22.34% | 40.74% | — | — | 0.763 | -1.35 | -1.19 | -52.59% | -62.30% | -1.34 | -62.20% |
| baseline_random | 197 | 37.56% | 56.60% | 0.257 | 1.000 | 0.662 | 2.19 | 3.14 | -16.64% | 137.50% | -1.34 | -62.20% |
| baseline_momentum | 197 | 28.93% | 52.78% | 0.368 | 1.000 | 0.995 | 0.05 | 0.06 | -30.12% | -10.71% | -1.34 | -62.20% |
| baseline_sentiment | 197 | 22.34% | 40.74% | — | — | 0.986 | -1.35 | -1.19 | -52.59% | -62.30% | -1.34 | -62.20% |

## ETH · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | PT q (FDR) | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 174 | 14.37% | 25.00% | — | — | 0.803 | -2.30 | -1.99 | -27.66% | -54.03% | -2.30 | -53.85% |
| baseline_buy_hold | 174 | 14.37% | 25.00% | — | — | 0.803 | -2.30 | -1.99 | -27.66% | -54.03% | -2.30 | -53.85% |
| baseline_random | 174 | 35.06% | 60.00% | 0.727 | 1.000 | 0.705 | -1.43 | -0.83 | -13.37% | -29.14% | -2.30 | -53.85% |
| baseline_momentum | 174 | 26.44% | 46.00% | 0.719 | 1.000 | 1.183 | -0.41 | -0.30 | -19.93% | 26.16% | -2.30 | -53.85% |
| baseline_sentiment | 174 | 14.37% | 25.00% | — | — | 1.097 | -2.30 | -1.99 | -27.66% | -54.03% | -2.30 | -53.85% |

---
*Data:* **real** prices (SPY via Yahoo, BTC/ETH via Binance) and **real** point-in-time news (GDELT, leakage-safe `seendate`; see `data/news/MANIFEST.json`). Scored on the news-aligned clean window. These are baselines only — the market bar the LLM must beat; no LLM has run yet.

*Why the FDR column matters.* Across many asset×horizon×model cells, ~1 in 20 will look significant by pure chance. Here a **random** baseline lands at raw `p≈0.007` on SPY·daily — a textbook false positive (≈1.1 expected across the 21 testable cells). After the Benjamini-Hochberg correction its `q` rises well above 0.05 and it **loses its stars** — which is the point: headline claims must survive FDR, not a lone raw p-value (PRD §7.6).
