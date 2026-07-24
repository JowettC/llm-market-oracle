"""Equity-curve figures for the results README (PRD §8.4).

Uses the non-interactive Agg backend so plots render headless with no display.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.backtest.portfolio import compute_backtest  # noqa: E402
from src.labeling import horizon_steps  # noqa: E402


def equity_curve_figure(
    records_by_model: dict[str, pd.DataFrame],
    close: pd.Series,
    asset_id: str,
    horizon: str,
    asset_kind: str,
    cost_bps: float,
    cfg: dict,
    out_path: Path,
) -> None:
    """Plot each model's net-of-cost equity curve vs. buy-and-hold for one cell."""
    steps = horizon_steps(asset_kind, horizon)
    fig, ax = plt.subplots(figsize=(9, 5))

    bh_drawn = False
    for model, recs in records_by_model.items():
        if recs.empty:
            continue
        bt = compute_backtest(recs, close, steps, cost_bps, cfg)
        if len(bt.strategy_equity) == 0:
            continue
        x = bt.entry_ts
        ax.plot(x, bt.strategy_equity, label=model.replace("baseline_", ""), linewidth=1.3)
        if not bh_drawn:
            ax.plot(x, bt.buy_hold_equity, label="buy & hold", color="black",
                    linewidth=2.0, linestyle="--")
            bh_drawn = True

    ax.axhline(1.0, color="grey", linewidth=0.6, alpha=0.6)
    ax.set_title(f"{asset_id} · {horizon} — net-of-cost equity vs. buy & hold "
                 f"(SYNTHETIC sample data)")
    ax.set_ylabel("equity (start = 1.0)")
    ax.set_xlabel("entry date")
    ax.legend(loc="best", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
