"""Score a walk-forward record set into both evaluation lenses (PRD §8.2)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest import metrics as M
from src.backtest.portfolio import BacktestResult, compute_backtest
from src.labeling import horizon_steps


def score_cell(
    records: pd.DataFrame,
    close: pd.Series,
    asset_kind: str,
    horizon: str,
    cost_bps_round_trip: float,
    cfg: dict,
) -> dict:
    """Return one flat dict of metrics for a (model × asset × horizon) cell."""
    recs = records.dropna(subset=["realized_label"])
    pred = recs["prediction"].tolist()
    actual = recs["realized_label"].tolist()
    prob_rows = [
        {"UP": r.prob_up, "STAY": r.prob_stay, "DOWN": r.prob_down}
        for r in recs.itertuples()
    ]

    ann = cfg["portfolio"]["annualization"].get(horizon, 252)
    steps = horizon_steps(asset_kind, horizon)
    bt: BacktestResult = compute_backtest(recs, close, steps, cost_bps_round_trip, cfg)

    pt = M.pesaran_timmermann(pred, actual)

    out = {
        "asset": recs["asset"].iloc[0] if not recs.empty else None,
        "horizon": horizon,
        "model": recs["model"].iloc[0] if not recs.empty else None,
        "condition": recs["condition"].iloc[0] if not recs.empty else None,
        "n": len(recs),
        # ---- statistical lens ----
        "accuracy": M.directional_accuracy(pred, actual),
        "pt_stat": pt.statistic,
        "pt_p": pt.p_value,
        "pt_hit_rate": pt.hit_rate,
        "pt_n": pt.n,
        "brier": M.brier_score(prob_rows, actual),
        # ---- economic lens (net of cost) ----
        "n_trades": bt.n_periods,
        "turnover": bt.turnover,
        "sharpe": M.sharpe(bt.strategy_returns, ann),
        "sortino": M.sortino(bt.strategy_returns, ann),
        "max_drawdown": M.max_drawdown(bt.strategy_equity) if len(bt.strategy_equity) else float("nan"),
        "cagr": M.cagr(bt.strategy_equity, ann) if len(bt.strategy_equity) else float("nan"),
        "final_equity": float(bt.strategy_equity[-1]) if len(bt.strategy_equity) else float("nan"),
        # ---- buy & hold benchmark ----
        "bh_sharpe": M.sharpe(bt.buy_hold_returns, ann),
        "bh_cagr": M.cagr(bt.buy_hold_equity, ann) if len(bt.buy_hold_equity) else float("nan"),
        "bh_final_equity": float(bt.buy_hold_equity[-1]) if len(bt.buy_hold_equity) else float("nan"),
    }
    return out


def per_class_table(records: pd.DataFrame) -> dict:
    recs = records.dropna(subset=["realized_label"])
    return M.per_class_f1(recs["prediction"].tolist(), recs["realized_label"].tolist())
