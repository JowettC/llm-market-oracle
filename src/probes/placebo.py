"""Placebo-news probe (PRD §7.3).

Feed the model news from a *different, mismatched* date while keeping the real
outcome. A predictor with genuine news-reading skill should score at chance on
mismatched news — it has no true signal. If accuracy stays high on placebo news,
the "skill" is coming from something other than reading the news (e.g. a
memorized outcome tied to the date, or trailing price context), which is a
lookahead red flag.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from src.data.assemble_context import PredictionContext
from src.data.news_providers import NewsItem


def placebo_context(
    context: PredictionContext,
    pool: list[NewsItem],
    rng: np.random.Generator,
    min_gap_days: int = 45,
    news_span_days: int = 3,
) -> PredictionContext:
    """Return a copy of ``context`` whose news is swapped for a mismatched date's.

    Picks a random anchor time in ``pool`` at least ``min_gap_days`` from the real
    decision time, then takes items from the ``news_span_days`` before that anchor.
    Keeps the same number of items where possible so prompt size is comparable.
    """
    if not pool:
        return context
    times = pd.Series([it.published_at for it in pool])
    as_of = context.as_of
    far = times[(times - as_of).abs() > pd.Timedelta(days=min_gap_days)]
    if far.empty:
        far = times  # corpus too short to guarantee a gap; still shuffle
    anchor = far.iloc[int(rng.integers(0, len(far)))]
    lo = anchor - pd.Timedelta(days=news_span_days)
    candidates = [it for it in pool if lo <= it.published_at < anchor]
    if not candidates:
        candidates = [it for it in pool if it.published_at < anchor][-len(context.news):]
    n = max(1, len(context.news))
    placebo_news = candidates[:n] if len(candidates) >= n else candidates
    return dataclasses.replace(context, news=list(placebo_news))
