# Robustness — θ-sensitivity & rolling decay

Baselines only (no LLM). Daily horizon. Shows results don't hinge on one band width, and exposes non-stationarity over the window (PRD §5.3, H4).


## SPY

### θ-sensitivity (accuracy by band width k)

STAY-rate by k: k=0.25: 20%, k=0.5: 40%, k=1.0: 70%

| model | k=0.25 acc | k=0.5 acc | k=1.0 acc |
| --- | --- | --- | --- |
| baseline_always_up | 0.449 | 0.355 | 0.159 |
| baseline_buy_hold | 0.449 | 0.355 | 0.159 |
| baseline_momentum | 0.341 | 0.254 | 0.116 |
| baseline_random | 0.413 | 0.413 | 0.514 |
| baseline_sentiment | 0.449 | 0.355 | 0.159 |

### Rolling decay (per sub-period)

| model | period | n | acc | Sharpe |
| --- | --- | --- | --- | --- |
| baseline_sentiment | P1 (2026-01-02..2026-02-20) | 34 | 0.382 | -0.036 |
| baseline_sentiment | P2 (2026-02-23..2026-04-13) | 35 | 0.343 | 0.796 |
| baseline_sentiment | P3 (2026-04-14..2026-06-01) | 34 | 0.412 | 5.634 |
| baseline_sentiment | P4 (2026-06-02..2026-07-22) | 35 | 0.286 | -1.016 |
| baseline_momentum | P1 (2026-01-02..2026-02-20) | 34 | 0.265 | -3.012 |
| baseline_momentum | P2 (2026-02-23..2026-04-13) | 35 | 0.314 | -0.810 |
| baseline_momentum | P3 (2026-04-14..2026-06-01) | 34 | 0.294 | 4.364 |
| baseline_momentum | P4 (2026-06-02..2026-07-22) | 35 | 0.143 | 0.056 |
| baseline_buy_hold | P1 (2026-01-02..2026-02-20) | 34 | 0.382 | -0.036 |
| baseline_buy_hold | P2 (2026-02-23..2026-04-13) | 35 | 0.343 | 0.796 |
| baseline_buy_hold | P3 (2026-04-14..2026-06-01) | 34 | 0.412 | 5.634 |
| baseline_buy_hold | P4 (2026-06-02..2026-07-22) | 35 | 0.286 | -1.016 |

## BTC

### θ-sensitivity (accuracy by band width k)

STAY-rate by k: k=0.25: 25%, k=0.5: 45%, k=1.0: 70%

| model | k=0.25 acc | k=0.5 acc | k=1.0 acc |
| --- | --- | --- | --- |
| baseline_always_up | 0.369 | 0.256 | 0.143 |
| baseline_buy_hold | 0.369 | 0.256 | 0.143 |
| baseline_momentum | 0.335 | 0.241 | 0.138 |
| baseline_random | 0.335 | 0.296 | 0.552 |
| baseline_sentiment | 0.320 | 0.246 | 0.143 |

### Rolling decay (per sub-period)

| model | period | n | acc | Sharpe |
| --- | --- | --- | --- | --- |
| baseline_sentiment | P1 (2026-01-02..2026-02-20) | 50 | 0.240 | -3.048 |
| baseline_sentiment | P2 (2026-02-21..2026-04-12) | 51 | 0.294 | -1.307 |
| baseline_sentiment | P3 (2026-04-13..2026-06-02) | 51 | 0.176 | -3.893 |
| baseline_sentiment | P4 (2026-06-03..2026-07-23) | 51 | 0.275 | -0.486 |
| baseline_momentum | P1 (2026-01-02..2026-02-20) | 50 | 0.260 | -3.687 |
| baseline_momentum | P2 (2026-02-21..2026-04-12) | 51 | 0.294 | -2.035 |
| baseline_momentum | P3 (2026-04-13..2026-06-02) | 51 | 0.216 | -2.974 |
| baseline_momentum | P4 (2026-06-03..2026-07-23) | 51 | 0.196 | -1.819 |
| baseline_buy_hold | P1 (2026-01-02..2026-02-20) | 50 | 0.240 | -2.475 |
| baseline_buy_hold | P2 (2026-02-21..2026-04-12) | 51 | 0.294 | 1.281 |
| baseline_buy_hold | P3 (2026-04-13..2026-06-02) | 51 | 0.216 | -2.467 |
| baseline_buy_hold | P4 (2026-06-03..2026-07-23) | 51 | 0.275 | 0.450 |

## ETH

### θ-sensitivity (accuracy by band width k)

STAY-rate by k: k=0.25: 28%, k=0.5: 46%, k=1.0: 71%

| model | k=0.25 acc | k=0.5 acc | k=1.0 acc |
| --- | --- | --- | --- |
| baseline_always_up | 0.330 | 0.236 | 0.128 |
| baseline_buy_hold | 0.330 | 0.236 | 0.128 |
| baseline_momentum | 0.365 | 0.251 | 0.148 |
| baseline_random | 0.340 | 0.330 | 0.562 |
| baseline_sentiment | 0.330 | 0.236 | 0.128 |

### Rolling decay (per sub-period)

| model | period | n | acc | Sharpe |
| --- | --- | --- | --- | --- |
| baseline_sentiment | P1 (2026-01-02..2026-02-20) | 50 | 0.180 | -3.073 |
| baseline_sentiment | P2 (2026-02-21..2026-04-12) | 51 | 0.314 | 1.729 |
| baseline_sentiment | P3 (2026-04-13..2026-06-02) | 51 | 0.196 | -4.214 |
| baseline_sentiment | P4 (2026-06-03..2026-07-23) | 51 | 0.255 | 0.908 |
| baseline_momentum | P1 (2026-01-02..2026-02-20) | 50 | 0.200 | -3.135 |
| baseline_momentum | P2 (2026-02-21..2026-04-12) | 51 | 0.275 | -1.699 |
| baseline_momentum | P3 (2026-04-13..2026-06-02) | 51 | 0.275 | -3.016 |
| baseline_momentum | P4 (2026-06-03..2026-07-23) | 51 | 0.255 | -1.522 |
| baseline_buy_hold | P1 (2026-01-02..2026-02-20) | 50 | 0.180 | -3.073 |
| baseline_buy_hold | P2 (2026-02-21..2026-04-12) | 51 | 0.314 | 1.729 |
| baseline_buy_hold | P3 (2026-04-13..2026-06-02) | 51 | 0.196 | -4.214 |
| baseline_buy_hold | P4 (2026-06-03..2026-07-23) | 51 | 0.255 | 0.908 |