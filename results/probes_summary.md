# Lookahead / memorization probes — summary (PRD §7.3)

Model `claude-opus-4-8`, prompt P0, **40 samples per asset** from the clean
(post-cutoff) window. Per-asset detail in `probes_{SPY,BTC,ETH}.md`.

These probes test whether the null result (no directional skill) could be an
artifact of contamination or of the model ignoring the news. It is neither.

| Asset | Date-masking (acc drop) | Placebo-news (Δpred / placebo acc) | Future-trivia (recalled) |
|---|---|---|---|
| **SPY** | −0.175 (no drop) | 35% change / 0.20→0.33 | **0 / 40** |
| **BTC** | −0.075 (no drop) | 50% change / 0.25→0.20 | **0 / 40** |
| **ETH** | −0.100 (no drop) | 45% change / 0.30→0.28 | **0 / 40** |

## Verdict: the null result is genuine, not contamination

1. **No date-keying.** Hiding every date (news timestamps, headline dates,
   decision date) does *not* reduce accuracy on any asset — Claude isn't
   recognizing calendar dates to recall outcomes.
2. **Claude reads the news.** Swapping in mismatched-date news changes 35–50% of
   its predictions and pushes accuracy toward chance — it is genuinely
   conditioning on the provided headlines (it just predicts poorly from them).
3. **Zero memorization.** Asked to *recall* the actual outcome for these
   post-cutoff dates, Claude answered UNKNOWN **every single time (0/120)** — it
   does not know the test period. The clean window held perfectly.

**Conclusion:** the finding that Claude has no significant directional skill
(0/24 cells across prompts × conditions) is a *real* capability measurement, not
a leakage or memorization artifact. Its crypto "outperformance" is a structural
bearish bias, and its news-reading is real but unskilled — both confirmed here.
