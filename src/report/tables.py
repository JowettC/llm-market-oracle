"""Render scored cells into committed Markdown + CSV artifacts (PRD §8.4, §12.5)."""

from __future__ import annotations

import pandas as pd


def _fmt(v, pct=False, nd=3):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, float):
        if v == float("inf"):
            return "∞"
        return f"{v * 100:.2f}%" if pct else f"{v:.{nd}f}"
    return str(v)


def _sig(p):
    if p is None or (isinstance(p, float) and pd.isna(p)):
        return ""
    if p < 0.01:
        return " ***"
    if p < 0.05:
        return " **"
    if p < 0.10:
        return " *"
    return ""


def results_markdown(df: pd.DataFrame, note: str = "") -> str:
    """A results-forward Markdown report grouped by asset × horizon."""
    lines: list[str] = []
    lines.append("# Baseline backtest results\n")
    lines.append(
        "Committed baseline results — the **market-performance bar** the LLM is "
        "measured against (PRD §7.4, §8.4). All economic figures are **net of "
        "transaction costs** with next-bar execution lag. `PT p` is the "
        "one-sided Pesaran-Timmermann market-timing p-value "
        "(`*` <0.10, `**` <0.05, `***` <0.01).\n"
    )
    if note:
        lines.append(f"> {note}\n")

    cols = [
        ("model", "Model", {}),
        ("n", "N", {}),
        ("accuracy", "Acc", {"pct": True}),
        ("pt_hit_rate", "Hit", {"pct": True}),
        ("pt_p", "PT p", {"nd": 3}),
        ("brier", "Brier", {"nd": 3}),
        ("sharpe", "Sharpe", {"nd": 2}),
        ("sortino", "Sortino", {"nd": 2}),
        ("max_drawdown", "MaxDD", {"pct": True}),
        ("cagr", "CAGR", {"pct": True}),
        ("bh_sharpe", "B&H Sharpe", {"nd": 2}),
        ("bh_cagr", "B&H CAGR", {"pct": True}),
    ]

    for (asset, horizon), grp in df.groupby(["asset", "horizon"], sort=False):
        power = {"daily": "high — primary", "weekly": "medium", "monthly": "LOW — exploratory only"}.get(horizon, "")
        lines.append(f"\n## {asset} · {horizon}  ({power})\n")
        header = "| " + " | ".join(c[1] for c in cols) + " |"
        sep = "| " + " | ".join("---" for _ in cols) + " |"
        lines.append(header)
        lines.append(sep)
        for _, row in grp.iterrows():
            cells = []
            for key, _label, opts in cols:
                val = _fmt(row[key], **opts)
                if key == "pt_p":
                    val = val + _sig(row["pt_p"])
                cells.append(val)
            lines.append("| " + " | ".join(cells) + " |")

    lines.append(
        "\n---\n*Note:* the committed `data/` corpus is **synthetic sample data** "
        "with no real predictive signal, so baselines should hover near chance "
        "here by construction — this table proves the engine runs end-to-end and "
        "establishes the reporting format. Real snapshots replace the samples in "
        "later phases.\n"
    )
    return "\n".join(lines)
