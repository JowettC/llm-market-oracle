# Baseline backtest results

Committed baseline results — the **market-performance bar** the LLM is measured against (PRD §7.4, §8.4). All economic figures are **net of transaction costs** with next-bar execution lag. `PT p` is the one-sided Pesaran-Timmermann market-timing p-value (`*` <0.10, `**` <0.05, `***` <0.01).


## SPY · daily  (high — primary)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 437 | 33.41% | 57.25% | — | 0.708 | 0.90 | 0.89 | -19.00% | 15.05% | 0.91 | 15.08% |
| baseline_buy_hold | 437 | 33.41% | 57.25% | — | 0.708 | 0.90 | 0.89 | -19.00% | 15.05% | 0.91 | 15.08% |
| baseline_random | 437 | 36.38% | 46.56% | 0.913 | 0.662 | -0.46 | -0.46 | -12.98% | -5.62% | 0.91 | 15.08% |
| baseline_momentum | 437 | 30.21% | 51.76% | 0.332 | 0.746 | -1.19 | -1.04 | -41.84% | -19.60% | 0.91 | 15.08% |
| baseline_sentiment | 437 | 29.06% | 42.27% | 0.879 | 0.777 | -0.94 | -0.94 | -29.28% | -15.26% | 0.91 | 15.08% |

## SPY · weekly  (medium)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 433 | 36.72% | 58.67% | — | 0.691 | 1.14 | 1.09 | -14.06% | 16.53% | 1.15 | 16.57% |
| baseline_buy_hold | 433 | 36.72% | 58.67% | — | 0.691 | 1.14 | 1.09 | -14.06% | 16.53% | 1.15 | 16.57% |
| baseline_random | 433 | 33.26% | 51.66% | 0.729 | 0.672 | -0.42 | -0.40 | -16.48% | -5.03% | 1.15 | 16.57% |
| baseline_momentum | 433 | 29.56% | 47.23% | 0.867 | 0.797 | -0.36 | -0.35 | -21.92% | -5.95% | 1.15 | 16.57% |
| baseline_sentiment | 433 | 24.48% | 37.50% | 0.987 | 0.792 | -1.22 | -1.13 | -28.34% | -15.63% | 1.15 | 16.57% |

## SPY · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 417 | 41.49% | 67.05% | — | 0.668 | 1.08 | 1.27 | -9.12% | 15.56% | 1.08 | 15.59% |
| baseline_buy_hold | 417 | 41.49% | 67.05% | — | 0.668 | 1.08 | 1.27 | -9.12% | 15.56% | 1.08 | 15.59% |
| baseline_random | 417 | 39.33% | 66.22% | — | 0.689 | 0.47 | 0.53 | -10.61% | 5.26% | 1.08 | 15.59% |
| baseline_momentum | 417 | 37.17% | 60.08% | 0.046 ** | 0.782 | -0.11 | -0.09 | -23.21% | -4.80% | 1.08 | 15.59% |
| baseline_sentiment | 417 | 20.38% | 27.44% | 1.000 | 0.829 | -0.97 | -0.82 | -27.10% | -14.67% | 1.08 | 15.59% |

## BTC · daily  (high — primary)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 909 | 27.94% | 51.11% | — | 0.735 | 0.50 | 0.53 | -52.97% | 11.94% | 0.50 | 11.99% |
| baseline_buy_hold | 909 | 27.94% | 51.11% | — | 0.735 | 0.50 | 0.53 | -52.97% | 11.94% | 0.50 | 11.99% |
| baseline_random | 909 | 36.08% | 45.75% | 0.934 | 0.656 | -0.38 | -0.40 | -52.93% | -14.57% | 0.50 | 11.99% |
| baseline_momentum | 909 | 26.62% | 48.69% | 0.721 | 0.821 | -1.40 | -1.40 | -93.64% | -47.32% | 0.50 | 11.99% |
| baseline_sentiment | 909 | 34.65% | 49.84% | 0.804 | 0.733 | 0.05 | 0.04 | -46.98% | -2.52% | 0.50 | 11.99% |

## BTC · weekly  (medium)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 903 | 31.67% | 53.06% | — | 0.717 | 0.61 | 0.68 | -51.75% | 18.47% | 0.61 | 18.54% |
| baseline_buy_hold | 903 | 31.67% | 53.06% | — | 0.717 | 0.61 | 0.68 | -51.75% | 18.47% | 0.61 | 18.54% |
| baseline_random | 903 | 36.21% | 56.97% | 0.029 ** | 0.664 | 0.94 | 1.28 | -28.87% | 33.48% | 0.61 | 18.54% |
| baseline_momentum | 903 | 30.12% | 50.46% | 0.430 | 0.943 | 0.46 | 0.49 | -43.78% | 10.80% | 0.61 | 18.54% |
| baseline_sentiment | 903 | 32.89% | 48.48% | 0.944 | 0.727 | 0.22 | 0.17 | -39.16% | 2.00% | 0.61 | 18.54% |

## BTC · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 880 | 30.11% | 53.11% | — | 0.724 | 0.56 | 0.73 | -45.70% | 4.70% | 0.56 | 4.77% |
| baseline_buy_hold | 880 | 30.11% | 53.11% | — | 0.724 | 0.56 | 0.73 | -45.70% | 4.70% | 0.56 | 4.77% |
| baseline_random | 880 | 35.91% | 53.28% | 0.308 | 0.686 | 1.03 | 1.70 | -15.34% | 40.76% | 0.56 | 4.77% |
| baseline_momentum | 880 | 27.27% | 48.10% | 0.871 | 1.106 | -0.66 | -0.78 | -63.50% | -27.32% | 0.56 | 4.77% |
| baseline_sentiment | 880 | 34.32% | 52.19% | 1.000 | 0.731 | 0.08 | 0.07 | -39.48% | -2.07% | 0.56 | 4.77% |

## ETH · daily  (high — primary)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 909 | 25.63% | 49.57% | — | 0.747 | 0.20 | 0.20 | -67.55% | -5.59% | 0.20 | -5.55% |
| baseline_buy_hold | 909 | 25.63% | 49.57% | — | 0.747 | 0.20 | 0.20 | -67.55% | -5.59% | 0.20 | -5.55% |
| baseline_random | 909 | 37.29% | 49.19% | 0.607 | 0.648 | -0.25 | -0.26 | -70.90% | -17.80% | 0.20 | -5.55% |
| baseline_momentum | 909 | 25.41% | 49.15% | 0.643 | 0.877 | -0.78 | -0.79 | -93.58% | -46.17% | 0.20 | -5.55% |
| baseline_sentiment | 909 | 33.00% | 47.06% | 0.533 | 0.748 | -0.22 | -0.18 | -67.55% | -19.18% | 0.20 | -5.55% |

## ETH · weekly  (medium)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 903 | 27.24% | 48.43% | — | 0.739 | 0.22 | 0.25 | -67.11% | -7.91% | 0.22 | -7.85% |
| baseline_buy_hold | 903 | 27.24% | 48.43% | — | 0.739 | 0.22 | 0.25 | -67.11% | -7.91% | 0.22 | -7.85% |
| baseline_random | 903 | 36.77% | 56.39% | 0.012 ** | 0.661 | 0.45 | 0.52 | -38.22% | 10.90% | 0.22 | -7.85% |
| baseline_momentum | 903 | 29.68% | 52.76% | 0.097 * | 1.013 | 1.53 | 1.95 | -43.73% | 127.57% | 0.22 | -7.85% |
| baseline_sentiment | 903 | 30.23% | 43.42% | 0.790 | 0.750 | -0.06 | -0.06 | -67.11% | -16.17% | 0.22 | -7.85% |

## ETH · monthly  (LOW — exploratory only)

| Model | N | Acc | Hit | PT p | Brier | Sharpe | Sortino | MaxDD | CAGR | B&H Sharpe | B&H CAGR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_always_up | 880 | 26.25% | 44.34% | — | 0.744 | 0.25 | 0.36 | -59.88% | -20.51% | 0.25 | -20.46% |
| baseline_buy_hold | 880 | 26.25% | 44.34% | — | 0.744 | 0.25 | 0.36 | -59.88% | -20.51% | 0.25 | -20.46% |
| baseline_random | 880 | 34.43% | 47.84% | — | 0.700 | 1.05 | 2.19 | -25.99% | 63.99% | 0.25 | -20.46% |
| baseline_momentum | 880 | 33.64% | 56.81% | 0.003 *** | 1.059 | -0.54 | -0.41 | -91.06% | -48.02% | 0.25 | -20.46% |
| baseline_sentiment | 880 | 30.91% | 38.70% | 0.041 ** | 0.747 | -0.02 | -0.02 | -59.88% | -20.57% | 0.25 | -20.46% |

---
*Note:* the committed `data/` corpus is **synthetic sample data** with no real predictive signal, so baselines should hover near chance here by construction — this table proves the engine runs end-to-end and establishes the reporting format. Real snapshots replace the samples in later phases.
