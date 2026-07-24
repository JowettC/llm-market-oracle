"""Tests for up/down/stay labeling and the neutral band (PRD §5.3)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.labeling import (
    DOWN,
    STAY,
    UP,
    build_labels,
    forward_returns,
    horizon_steps,
    label_from_return,
)


def test_label_band_boundaries():
    theta = 0.01
    assert label_from_return(0.02, theta) == UP
    assert label_from_return(-0.02, theta) == DOWN
    assert label_from_return(0.005, theta) == STAY
    assert label_from_return(0.01, theta) == STAY   # boundary is inclusive of STAY
    assert label_from_return(-0.01, theta) == STAY
    assert label_from_return(np.nan, theta) is None


def test_forward_returns_alignment():
    close = pd.Series([100.0, 110.0, 121.0])  # +10% each step
    fwd = forward_returns(close, steps=1)
    assert abs(fwd.iloc[0] - 0.10) < 1e-9
    assert abs(fwd.iloc[1] - 0.10) < 1e-9
    assert np.isnan(fwd.iloc[2])  # no future for the last bar


def test_horizon_steps_differ_by_asset_kind():
    assert horizon_steps("equity", "weekly") == 5
    assert horizon_steps("crypto", "weekly") == 7
    assert horizon_steps("crypto", "monthly") == 30


def test_build_labels_vol_scaled_runs():
    idx = pd.date_range("2025-01-01", periods=60, freq="D", tz="UTC")
    rng = np.random.default_rng(0)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 60))), index=idx)
    band_cfg = {"method": "vol_scaled", "vol_scaled": {"k": 0.5, "lookback_days": 20}}
    out = build_labels(close, "SPY", "equity", "daily", band_cfg)
    valid = out.label.dropna()
    assert len(valid) > 0
    assert set(valid.unique()).issubset({UP, DOWN, STAY})
    # theta must be non-negative wherever it is defined
    assert (out.theta.dropna() >= 0).all()


def test_build_labels_fixed_band():
    idx = pd.date_range("2025-01-01", periods=10, freq="D", tz="UTC")
    close = pd.Series([100, 101, 100, 99, 100, 105, 95, 100, 100, 100], index=idx, dtype=float)
    band_cfg = {"method": "fixed", "fixed": {"SPY": {"daily": 0.02, "weekly": 0.04, "monthly": 0.08}}}
    out = build_labels(close, "SPY", "equity", "daily", band_cfg)
    # bar 4->5 is +5% => UP; bar 5->6 is ~-9.5% => DOWN
    assert out.label.iloc[4] == UP
    assert out.label.iloc[5] == DOWN
