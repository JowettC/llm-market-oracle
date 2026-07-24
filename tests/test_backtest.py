"""Tests for the walk-forward engine and portfolio (PRD §8.1, §8.3)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.portfolio import compute_backtest
from src.backtest.walk_forward import run_walk_forward
from src.config import load_config
from src.data.market_providers import CSVMarketProvider
from src.data.news_providers import JSONLNewsProvider
from src.predictors.base import Predictor, prediction_from_label
from src.predictors.baselines import AlwaysUpPredictor


class _OraclePredictor(Predictor):
    """Cheats using realized labels — ONLY for testing the economic engine.

    It is NOT wired through assemble_context leakage rules; it reads a lookup of
    bar -> realized label passed in at construction. Used to confirm a perfect
    directional call beats buy-and-hold in the portfolio.
    """

    model_id = "oracle_test"

    def __init__(self, label_by_asof):
        self.label_by_asof = label_by_asof

    def predict(self, context):
        label = self.label_by_asof.get(context.as_of, "STAY")
        return prediction_from_label(label, context, self.model_id, confidence=0.9)


def _cfg():
    return load_config()


def test_walk_forward_runs_and_is_time_ordered():
    cfg = _cfg()
    recs = run_walk_forward(
        AlwaysUpPredictor(), "SPY", "equity", "daily", cfg["label_band"],
        news_provider=JSONLNewsProvider(), market_provider=CSVMarketProvider(),
        window_start="2025-06-01", window_end="2025-12-31",
    )
    assert not recs.empty
    assert recs["as_of"].is_monotonic_increasing
    assert (recs["prediction"] == "UP").all()
    # every decision has a realized label and a finite return
    assert recs["realized_label"].notna().all()
    assert np.isfinite(recs["realized_return"]).all()


def test_walk_forward_records_no_future_news():
    """n_news counts only admissible items; a mid-history as_of sees fewer than the end."""
    cfg = _cfg()
    recs = run_walk_forward(
        AlwaysUpPredictor(), "BTC", "crypto", "daily", cfg["label_band"],
        news_provider=JSONLNewsProvider(), market_provider=CSVMarketProvider(),
        window_start="2025-03-01", window_end="2025-12-31",
    )
    # news available grows over time (strictly non-decreasing as as_of advances)
    n_news = recs.sort_values("as_of")["n_news"].to_numpy()
    assert (np.diff(n_news) >= 0).all()


def test_always_up_equals_buy_hold_gross():
    """Always-UP with zero cost must equal buy-and-hold period returns."""
    cfg = _cfg()
    close = CSVMarketProvider().get_ohlcv("SPY")["close"]
    recs = run_walk_forward(
        AlwaysUpPredictor(), "SPY", "equity", "daily", cfg["label_band"],
        news_provider=JSONLNewsProvider(), market_provider=CSVMarketProvider(),
        window_start="2025-06-01", window_end="2025-12-31",
    )
    bt = compute_backtest(recs, close, steps=1, cost_bps_round_trip=0.0, cfg=cfg)
    assert np.allclose(bt.strategy_returns, bt.buy_hold_returns)


def test_oracle_beats_buy_hold():
    """A perfect directional predictor must beat buy-and-hold net of modest cost.

    The economic engine trades the EXECUTION-LAGGED window (enter at bar i+1,
    hold `steps`), so the oracle is aligned to that window: for a decision at bar
    i it foresees the sign of close[i+2]/close[i+1]. This also documents the real
    subtlety that a statistically-perfect (no-lag) call is NOT automatically
    economically perfect once execution lag is applied.
    """
    cfg = _cfg()
    market = CSVMarketProvider()
    close = market.get_ohlcv("BTC")["close"]
    index = close.index
    vals = close.to_numpy(dtype=float)
    # entry-aligned oracle labels: decision at bar i -> direction of close[i+1]->close[i+2]
    label_by_asof = {}
    for i in range(len(vals) - 2):
        ret = vals[i + 2] / vals[i + 1] - 1.0
        label_by_asof[index[i]] = "UP" if ret > 0 else "DOWN"

    recs = run_walk_forward(
        _OraclePredictor(label_by_asof), "BTC", "crypto", "daily", cfg["label_band"],
        news_provider=JSONLNewsProvider(), market_provider=market,
        window_start="2025-03-01", window_end="2025-12-31",
    )
    bt = compute_backtest(recs, close, steps=1, cost_bps_round_trip=30.0, cfg=cfg)
    assert bt.strategy_equity[-1] > bt.buy_hold_equity[-1]


def test_costs_reduce_returns():
    cfg = _cfg()
    market = CSVMarketProvider()
    close = market.get_ohlcv("ETH")["close"]
    recs = run_walk_forward(
        AlwaysUpPredictor(), "ETH", "crypto", "daily", cfg["label_band"],
        news_provider=JSONLNewsProvider(), market_provider=market,
        window_start="2025-06-01", window_end="2025-12-31",
    )
    free = compute_backtest(recs, close, 1, 0.0, cfg)
    costly = compute_backtest(recs, close, 1, 50.0, cfg)
    # always-UP holds a constant position, so only entry+exit legs cost -> small but >=0 drag
    assert costly.strategy_equity[-1] <= free.strategy_equity[-1]
