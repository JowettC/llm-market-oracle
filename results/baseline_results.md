# Baseline backtest results

Committed baseline results — the **market-performance bar** the LLM is measured against (PRD §7.4, §8.4). All economic figures are **net of transaction costs** with next-bar execution lag. `PT p` is the one-sided Pesaran-Timmermann market-timing p-value (`*` <0.10, `**` <0.05, `***` <0.01).


## SPY · daily  (high — primary)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 221 | 27.15% | 45.80% | — | 0.739 | -0.43 | -0.47 | -13.45% | -7.20% | -0.42 | -7.14% |
| baseline_buy_hold | 221 | 27.15% | 45.80% | — | 0.739 | -0.43 | -0.47 | -13.45% | -7.20% | -0.42 | -7.14% |
| baseline_random | 221 | 29.41% | 56.00% | 0.084 * | 0.674 | -1.36 | -1.38 | -18.57% | -16.28% | -0.42 | -7.14% |
| baseline_momentum | 221 | 29.86% | 50.38% | 0.515 | 0.752 | -1.54 | -1.43 | -27.08% | -21.89% | -0.42 | -7.14% |
| baseline_sentiment | 221 | 30.77% | 51.20% | 0.836 | 0.765 | -0.33 | -0.31 | -9.73% | -5.73% | -0.42 | -7.14% |

## SPY · weekly  (medium)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 217 | 30.41% | 47.14% | — | 0.723 | -0.41 | -0.43 | -11.35% | -6.48% | -0.40 | -6.42% |
| baseline_buy_hold | 217 | 30.41% | 47.14% | — | 0.723 | -0.41 | -0.43 | -11.35% | -6.48% | -0.40 | -6.42% |
| baseline_random | 217 | 36.87% | 48.15% | 0.476 | 0.676 | -0.52 | -0.53 | -12.48% | -7.91% | -0.40 | -6.42% |
| baseline_momentum | 217 | 24.42% | 37.86% | 0.998 | 0.845 | -0.63 | -0.61 | -19.92% | -12.67% | -0.40 | -6.42% |
| baseline_sentiment | 217 | 29.49% | 45.86% | 0.996 | 0.774 | -0.02 | -0.02 | -8.79% | -0.15% | -0.40 | -6.42% |

## SPY · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 201 | 25.37% | 43.22% | — | 0.748 | -0.38 | -0.43 | -6.88% | -2.16% | -0.37 | -2.09% |
| baseline_buy_hold | 201 | 25.37% | 43.22% | — | 0.748 | -0.38 | -0.43 | -6.88% | -2.16% | -0.37 | -2.09% |
| baseline_random | 201 | 31.34% | 41.94% | 0.749 | 0.687 | -1.66 | -1.47 | -18.34% | -18.69% | -0.37 | -2.09% |
| baseline_momentum | 201 | 23.88% | 40.68% | 0.996 | 0.937 | -1.05 | -1.11 | -16.63% | -11.35% | -0.37 | -2.09% |
| baseline_sentiment | 201 | 24.88% | 46.30% | 0.995 | 0.806 | -0.78 | -0.75 | -6.44% | -6.63% | -0.37 | -2.09% |

## BTC · daily  (high — primary)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 309 | 25.57% | 42.25% | — | 0.747 | -1.67 | -1.62 | -79.93% | -71.70% | -1.66 | -71.67% |
| baseline_buy_hold | 309 | 25.57% | 42.25% | — | 0.747 | -1.67 | -1.62 | -79.93% | -71.70% | -1.66 | -71.67% |
| baseline_random | 309 | 34.30% | 53.85% | 0.200 | 0.668 | 0.38 | 0.39 | -41.93% | 6.82% | -1.66 | -71.67% |
| baseline_momentum | 309 | 32.36% | 53.48% | 0.213 | 0.864 | -1.18 | -1.14 | -80.31% | -61.19% | -1.66 | -71.67% |
| baseline_sentiment | 309 | 33.33% | 55.43% | 0.959 | 0.729 | 1.00 | 1.01 | -38.43% | 65.09% | -1.66 | -71.67% |

## BTC · weekly  (medium)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 303 | 18.48% | 30.94% | — | 0.783 | -2.54 | -2.11 | -76.44% | -82.35% | -2.54 | -82.32% |
| baseline_buy_hold | 303 | 18.48% | 30.94% | — | 0.783 | -2.54 | -2.11 | -76.44% | -82.35% | -2.54 | -82.32% |
| baseline_random | 303 | 32.67% | 51.61% | 0.226 | 0.670 | -1.33 | -1.19 | -62.08% | -61.74% | -2.54 | -82.32% |
| baseline_momentum | 303 | 32.01% | 53.59% | 0.635 | 1.016 | 0.14 | 0.14 | -35.30% | 7.23% | -2.54 | -82.32% |
| baseline_sentiment | 303 | 38.94% | 65.73% | 0.938 | 0.694 | 1.71 | 2.10 | -30.08% | 216.90% | -2.54 | -82.32% |

## BTC · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 280 | 8.57% | 14.20% | — | 0.832 | -2.84 | -2.18 | -76.35% | -85.37% | -2.84 | -85.34% |
| baseline_buy_hold | 280 | 8.57% | 14.20% | — | 0.832 | -2.84 | -2.18 | -76.35% | -85.37% | -2.84 | -85.34% |
| baseline_random | 280 | 41.07% | 74.76% | 0.547 | 0.651 | -1.44 | -0.77 | -38.71% | -47.94% | -2.84 | -85.34% |
| baseline_momentum | 280 | 42.14% | 69.82% | 0.990 | 0.925 | 1.41 | 1.71 | -27.96% | 85.95% | -2.84 | -85.34% |
| baseline_sentiment | 280 | 51.43% | 83.93% | 0.763 | 0.623 | 1.86 | 2.09 | -24.29% | 285.23% | -2.84 | -85.34% |

## ETH · daily  (high — primary)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 309 | 36.89% | 56.72% | — | 0.691 | 1.59 | 1.78 | -41.65% | 157.12% | 1.59 | 157.44% |
| baseline_buy_hold | 309 | 36.89% | 56.72% | — | 0.691 | 1.59 | 1.78 | -41.65% | 157.12% | 1.59 | 157.44% |
| baseline_random | 309 | 35.28% | 53.97% | 0.179 | 0.670 | -0.62 | -0.65 | -57.62% | -43.80% | 1.59 | 157.44% |
| baseline_momentum | 309 | 31.39% | 48.26% | 0.715 | 0.889 | 0.78 | 0.76 | -53.66% | 35.85% | 1.59 | 157.44% |
| baseline_sentiment | 309 | 36.89% | 56.72% | — | 0.711 | 1.59 | 1.78 | -41.65% | 157.12% | 1.59 | 157.44% |

## ETH · weekly  (medium)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 303 | 38.94% | 62.43% | — | 0.680 | 1.90 | 2.03 | -37.37% | 221.88% | 1.90 | 222.56% |
| baseline_buy_hold | 303 | 38.94% | 62.43% | — | 0.680 | 1.90 | 2.03 | -37.37% | 221.88% | 1.90 | 222.56% |
| baseline_random | 303 | 35.31% | 60.71% | 0.288 | 0.667 | 2.21 | 2.84 | -32.11% | 390.60% | 1.90 | 222.56% |
| baseline_momentum | 303 | 29.37% | 47.09% | 0.979 | 1.099 | -1.33 | -1.28 | -75.57% | -79.26% | 1.90 | 222.56% |
| baseline_sentiment | 303 | 38.94% | 62.43% | — | 0.699 | 1.90 | 2.03 | -37.37% | 221.88% | 1.90 | 222.56% |

## ETH · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 280 | 49.29% | 75.41% | — | 0.629 | 2.32 | 3.25 | -17.86% | 393.75% | 2.32 | 394.63% |
| baseline_buy_hold | 280 | 49.29% | 75.41% | — | 0.629 | 2.32 | 3.25 | -17.86% | 393.75% | 2.32 | 394.63% |
| baseline_random | 280 | 50.36% | 78.43% | — | 0.715 | 3.34 | 447.29 | -0.15% | 677.66% | 2.32 | 394.63% |
| baseline_momentum | 280 | 37.86% | 57.92% | 0.746 | 1.029 | 0.18 | 0.16 | -77.22% | -47.91% | 2.32 | 394.63% |
| baseline_sentiment | 280 | 49.29% | 75.41% | — | 0.633 | 2.32 | 3.25 | -17.86% | 393.75% | 2.32 | 394.63% |

---
*Note:* the committed `data/` corpus is **synthetic sample data** with no real predictive signal, so baselines should hover near chance here by construction — this table proves the engine runs end-to-end and establishes the reporting format. Real snapshots replace the samples in later phases.
