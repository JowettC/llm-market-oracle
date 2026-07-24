"""Up / down / stay labeling with the critical neutral band (PRD §5.3).

The forward return over a horizon is mapped to a three-way label using a
neutral band ``theta``:

    UP    if  fwd_return >  +theta
    DOWN  if  fwd_return <  -theta
    STAY  if  -theta <= fwd_return <= +theta

``theta`` is a pre-registered hyperparameter chosen on the calibration window
only, never tuned on the test set (PRD §5.3, §7.5). Two methods are supported:
a fixed band and a volatility-scaled band (recommended, fairer across assets).

All horizons use the close-to-close convention (PRD §5.2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

UP, DOWN, STAY = "UP", "DOWN", "STAY"
LABELS = (UP, DOWN, STAY)

# Trading/calendar bars per horizon step, by asset kind (PRD §5.2).
HORIZON_STEPS = {
    "equity": {"daily": 1, "weekly": 5, "monthly": 21},
    "crypto": {"daily": 1, "weekly": 7, "monthly": 30},
}


def horizon_steps(asset_kind: str, horizon: str) -> int:
    try:
        return HORIZON_STEPS[asset_kind][horizon]
    except KeyError as exc:
        raise ValueError(f"no step for {asset_kind}/{horizon}") from exc


def forward_returns(close: pd.Series, steps: int) -> pd.Series:
    """Close-to-close forward return over ``steps`` bars, indexed by decision bar.

    ``fwd[t] = close[t+steps] / close[t] - 1``. The last ``steps`` entries are
    NaN (no realized future yet) and must be dropped before scoring.
    """
    close = close.astype(float)
    fwd = close.shift(-steps) / close - 1.0
    return fwd


def realized_vol(close: pd.Series, lookback: int) -> pd.Series:
    """Trailing realized volatility of 1-bar log returns (per-bar, not annualized)."""
    logret = np.log(close.astype(float)).diff()
    return logret.rolling(lookback).std()


def compute_theta(
    close: pd.Series,
    asset_id: str,
    asset_kind: str,
    horizon: str,
    band_cfg: dict,
) -> pd.Series | float:
    """Return the neutral-band half-width theta for each decision bar.

    For ``vol_scaled`` theta varies per bar (a Series aligned to ``close``);
    for ``fixed`` it is a scalar. theta is scaled to the horizon so a weekly
    band is wider than a daily one.
    """
    method = band_cfg.get("method", "vol_scaled")
    steps = horizon_steps(asset_kind, horizon)

    if method == "fixed":
        table = band_cfg["fixed"].get(asset_id)
        if table is None or horizon not in table:
            raise ValueError(f"no fixed band for {asset_id}/{horizon}")
        return float(table[horizon])

    if method == "vol_scaled":
        vs = band_cfg["vol_scaled"]
        k = float(vs.get("k", 0.5))
        lookback = int(vs.get("lookback_days", 20))
        per_bar_vol = realized_vol(close, lookback)
        # scale 1-bar vol to the horizon: sqrt(steps) under iid returns.
        horizon_vol = per_bar_vol * np.sqrt(steps)
        return k * horizon_vol

    raise ValueError(f"unknown label_band.method: {method!r}")


def label_from_return(fwd_return: float, theta: float) -> str | None:
    """Map a single forward return to UP/DOWN/STAY given theta. NaN -> None."""
    if fwd_return is None or (isinstance(fwd_return, float) and np.isnan(fwd_return)):
        return None
    if np.isnan(theta):
        return None
    if fwd_return > theta:
        return UP
    if fwd_return < -theta:
        return DOWN
    return STAY


@dataclass(frozen=True)
class LabeledSeries:
    """Realized labels aligned to decision bars, plus the returns and theta used."""

    fwd_return: pd.Series
    theta: pd.Series  # broadcast to a Series even for the fixed method
    label: pd.Series


def build_labels(
    close: pd.Series,
    asset_id: str,
    asset_kind: str,
    horizon: str,
    band_cfg: dict,
) -> LabeledSeries:
    """Compute forward returns, theta, and realized labels for every decision bar."""
    steps = horizon_steps(asset_kind, horizon)
    fwd = forward_returns(close, steps)
    theta = compute_theta(close, asset_id, asset_kind, horizon, band_cfg)
    theta_series = theta if isinstance(theta, pd.Series) else pd.Series(theta, index=close.index)

    labels = pd.Series(
        [label_from_return(r, t) for r, t in zip(fwd.to_numpy(), theta_series.to_numpy())],
        index=close.index,
        dtype="object",
    )
    return LabeledSeries(fwd_return=fwd, theta=theta_series, label=labels)
