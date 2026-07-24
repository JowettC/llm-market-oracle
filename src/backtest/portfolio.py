"""Economic lens: predictions -> positions -> net-of-cost equity curve (PRD §8.3).

Turns a walk-forward record set into a tradeable strategy and compares it to
buy-and-hold. Two realism knobs the PRD insists on:

- **Execution lag** — act at the *next available* price, not the close the
  prediction was computed from (PRD §7.7). We enter at ``bar_index + 1``.
- **Transaction costs** — every result is net of a configurable round-trip cost
  (PRD §7.7); gross numbers are never headlined.

The economic lens uses a **non-overlapping** decision grid (step = horizon
length) so held positions never overlap and the compounded equity curve is
honest. The statistical lens (metrics.py) separately uses all overlapping
decisions with a HAC correction (PRD §8.3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.labeling import DOWN, STAY, UP


@dataclass(frozen=True)
class BacktestResult:
    strategy_returns: np.ndarray      # per-period net-of-cost returns
    strategy_equity: np.ndarray       # equity curve, starts at 1.0
    buy_hold_returns: np.ndarray
    buy_hold_equity: np.ndarray
    turnover: float                   # average |Δposition| per period
    n_periods: int
    entry_ts: list[pd.Timestamp]


def _target_position(row: pd.Series, cfg: dict) -> float:
    pmap = cfg["portfolio"]["position_map"]
    down_flat = cfg["portfolio"].get("down_flat", False)
    pred = row["prediction"]
    pos = float(pmap.get(pred, 0))
    if down_flat and pred == DOWN:
        pos = 0.0
    if cfg["portfolio"].get("confidence_weighted", False) and pos != 0.0:
        scale = np.clip((row["confidence"] - 0.5) / 0.5, 0.0, 1.0)
        pos *= scale
    return pos


def compute_backtest(
    records: pd.DataFrame,
    close: pd.Series,
    steps: int,
    cost_bps_round_trip: float,
    cfg: dict,
) -> BacktestResult:
    """Build the net-of-cost equity curve for one (model × asset × horizon) cell."""
    if records.empty:
        empty = np.array([])
        return BacktestResult(empty, empty, empty, empty, 0.0, 0, [])

    recs = records.sort_values("bar_index").reset_index(drop=True)
    close_vals = close.to_numpy(dtype=float)
    n_bars = len(close_vals)

    # non-overlapping grid: take every `steps`-th decision so holds don't overlap
    first = int(recs["bar_index"].iloc[0])
    grid = recs[(recs["bar_index"] - first) % steps == 0]

    one_way = (cost_bps_round_trip / 2.0) / 1e4
    prev_pos = 0.0
    strat_rets, bh_rets, positions, entry_ts = [], [], [], []

    for _, row in grid.iterrows():
        i = int(row["bar_index"])
        entry_i = i + 1              # execution lag: enter at next bar
        exit_i = entry_i + steps
        if exit_i >= n_bars:
            break
        asset_ret = close_vals[exit_i] / close_vals[entry_i] - 1.0
        pos = _target_position(row, cfg)

        cost = one_way * abs(pos - prev_pos)
        strat_rets.append(pos * asset_ret - cost)
        bh_rets.append(asset_ret)
        positions.append(pos)
        entry_ts.append(close.index[entry_i])
        prev_pos = pos

    # close out the final position (pay the exit leg)
    if strat_rets:
        strat_rets[-1] -= one_way * abs(prev_pos)

    strat_rets = np.array(strat_rets)
    bh_rets = np.array(bh_rets)
    positions = np.array(positions)
    turnover = float(np.mean(np.abs(np.diff(np.concatenate([[0.0], positions]))))) if len(positions) else 0.0

    return BacktestResult(
        strategy_returns=strat_rets,
        strategy_equity=np.cumprod(1.0 + strat_rets) if len(strat_rets) else strat_rets,
        buy_hold_returns=bh_rets,
        buy_hold_equity=np.cumprod(1.0 + bh_rets) if len(bh_rets) else bh_rets,
        turnover=turnover,
        n_periods=len(strat_rets),
        entry_ts=entry_ts,
    )
