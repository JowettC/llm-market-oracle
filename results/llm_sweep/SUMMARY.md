# First real LLM result — Claude (Opus 4.8) reading the news, daily horizon

**Scope.** 542 real `claude -p` calls (Claude Max subscription, no API key).
Prompt **P0** (zero-shot Lopez-Lira style), **news-only**, **daily** horizon,
clean window **2026-01-01 → 2026-07-23**, real GDELT news. SPY n=138, BTC/ETH
n=203 each. This is one prompt, one model tier, one ~6.5-month window — a first
pass, not the full 72-cell sweep.

## Headline numbers (net of cost)

| Asset | Claude acc | best baseline acc | Claude PT p | PT q (FDR) | Claude Sharpe | Buy&Hold Sharpe |
|---|---|---|---|---|---|---|
| SPY | 0.275 | 0.413 (random) | 0.856 | 0.94 | **−3.70** | **+1.01** |
| BTC | 0.296 | 0.296 (=Claude) | 0.392 | 0.94 | +0.32 | −0.85 |
| ETH | 0.291 | 0.330 (random) | 0.555 | 0.94 | +0.08 | −0.92 |

## The honest read

**No statistically significant directional skill anywhere.** Every Pesaran-
Timmermann p-value is ≫ 0.05, and after the Benjamini-Hochberg FDR correction
every q ≈ 0.94. Claude's 3-class **accuracy (27–29%) is below the naive
baselines** (random scores 30–41%) and below the ~33% chance line.

**SPY (rising market): Claude fails hard.** It called UP 79 / DOWN 57 / STAY 2,
but was right only 30% of the time it said UP and 23% when it said DOWN — so it
repeatedly shorted a rising index and posted a **−3.70 Sharpe** while buy-and-hold
returned +12.8%. This is the STOCKBENCH / H2 result: the LLM does not beat the
index.

**Crypto (falling market): the "win" is a bias artifact, not skill.** Claude beat
buy-and-hold economically on BTC (+6.4% vs −34.8%) and ETH (−9.7% vs −47.3%) —
but only because it is **systematically bearish on crypto**: it predicted DOWN
**170/203 (84%) on BTC** and **166/203 (82%) on ETH**. A standing short bias
mechanically profits in a bear market. It is not timing: accuracy-when-it-said-
DOWN was ~0.30, barely the base rate, and PT finds no significant skill. Had
crypto risen this window, the same bias would have lost just as badly as it did
on SPY.

**Calibration is poor.** Mean confidence ≈ 0.44; Brier ≈ 0.70 (worse than the
random baseline's ~0.66).

## Verdict

On this window/prompt/model, **there is no evidence that Claude reading point-in-
time news has genuine directional skill.** It underperforms naive baselines on
accuracy, loses badly on the index, and its crypto out-performance is a static
bearish bias meeting a falling market — exactly the kind of false "edge" the PT
test + prediction-distribution audit are designed to catch. This is a clean,
honest negative result, consistent with the prior literature.

## Caveats / what would change the picture

- One prompt (P0), one model tier, one ~6.5-month window, coarse monthly news
  coverage. P1–P3, news+price, a second Claude tier, and a longer window remain.
- The bearish-bias finding suggests a **calibration / base-rate** issue worth a
  targeted prompt fix — but that is model-improvement, not evidence of skill.
- The memorization probes (§7.3) should be run at scale on these cells;
  the n=3 smoke already showed Claude answers UNKNOWN for these post-cutoff dates.
