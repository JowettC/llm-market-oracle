"""Walk-forward, out-of-sample prediction generation (PRD §8.1).

Predictions are generated strictly sequentially through time: for each decision
bar in the test window, the point-in-time gate (`assemble_context`) exposes only
past news/prices, the predictor emits a `Prediction`, and we pair it with the
realized label/return for that bar. Nothing downstream of a decision date ever
informs it.

There is no in-sample fitting of a predictor here — the only "training" is θ
selection and baseline calibration, done earlier on a disjoint window.
"""

from __future__ import annotations

import dataclasses

import pandas as pd

from src.data.assemble_context import assemble_context
from src.data.market_providers import MarketDataProvider
from src.data.news_providers import NewsDataProvider
from src.labeling import build_labels, horizon_steps
from src.predictors.base import Predictor

RECORD_COLUMNS = [
    "asset", "horizon", "model", "condition", "bar_index",
    "as_of", "entry_ts", "prediction", "confidence",
    "prob_up", "prob_stay", "prob_down",
    "realized_label", "realized_return", "theta", "n_news",
]


def iter_decision_contexts(
    asset_id: str,
    asset_kind: str,
    horizon: str,
    band_cfg: dict,
    news_provider: NewsDataProvider,
    market_provider: MarketDataProvider,
    window_start: pd.Timestamp | str | None = None,
    window_end: pd.Timestamp | str | None = None,
    condition: str = "news_only",
    max_news: int | None = None,
):
    """Yield (bar_index, context, realized_label, realized_return) for each scored bar.

    The single source of truth for which decisions exist, shared by the real
    walk-forward and the dry-run call estimator so they never diverge.
    """
    close = market_provider.get_ohlcv(asset_id)["close"]
    labeled = build_labels(close, asset_id, asset_kind, horizon, band_cfg)
    steps = horizon_steps(asset_kind, horizon)
    index = close.index
    lo = _to_utc(window_start) if window_start is not None else index[0]
    hi = _to_utc(window_end) if window_end is not None else index[-1]
    n = len(index)
    for i in range(n):
        as_of = index[i]
        if as_of < lo or as_of > hi:
            continue
        if i + steps >= n:
            break
        realized_label = labeled.label.iloc[i]
        if realized_label is None or (isinstance(realized_label, float) and pd.isna(realized_label)):
            continue
        ctx = assemble_context(
            as_of, asset_id, horizon,
            news_provider=news_provider, market_provider=market_provider,
            condition=condition, max_news=max_news,
        )
        theta_i = labeled.theta.iloc[i]
        ctx = dataclasses.replace(ctx, theta=None if pd.isna(theta_i) else float(theta_i))
        yield i, ctx, realized_label, float(labeled.fwd_return.iloc[i]), float(theta_i) if not pd.isna(theta_i) else float("nan")


def run_walk_forward(
    predictor: Predictor,
    asset_id: str,
    asset_kind: str,
    horizon: str,
    band_cfg: dict,
    news_provider: NewsDataProvider,
    market_provider: MarketDataProvider,
    window_start: pd.Timestamp | str | None = None,
    window_end: pd.Timestamp | str | None = None,
    condition: str = "news_only",
    max_news: int | None = None,
    max_decisions: int | None = None,
) -> pd.DataFrame:
    """Score one (predictor × asset × horizon × condition) cell over a window.

    Returns a DataFrame with one row per decision bar (see ``RECORD_COLUMNS``).
    Only bars with a realized forward label (i.e. ``i + steps`` exists) and that
    fall inside ``[window_start, window_end]`` are scored. ``max_decisions`` caps
    the number of decisions (for cheap LLM smoke runs).
    """
    close = market_provider.get_ohlcv(asset_id)["close"]
    index = close.index
    n = len(index)
    rows = []
    for i, ctx, realized_label, realized_return, theta_i in iter_decision_contexts(
        asset_id, asset_kind, horizon, band_cfg, news_provider, market_provider,
        window_start, window_end, condition, max_news,
    ):
        if max_decisions is not None and len(rows) >= max_decisions:
            break
        pred = predictor.predict(ctx)
        entry_ts = index[i + 1] if i + 1 < n else pd.NaT  # next available bar (exec lag)

        rows.append({
            "asset": asset_id,
            "horizon": horizon,
            "model": pred.model,
            "condition": condition,
            "bar_index": i,
            "as_of": ctx.as_of,
            "entry_ts": entry_ts,
            "prediction": pred.prediction,
            "confidence": pred.confidence,
            "prob_up": pred.prob_up,
            "prob_stay": pred.prob_stay,
            "prob_down": pred.prob_down,
            "realized_label": realized_label,
            "realized_return": realized_return,
            "theta": theta_i,
            "n_news": len(ctx.news),
        })

    return pd.DataFrame(rows, columns=RECORD_COLUMNS)


def _to_utc(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
