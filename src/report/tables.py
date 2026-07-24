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
        "transaction costs** with next-bar execution lag. `PT p` is the raw "
        "one-sided Pesaran-Timmermann market-timing p-value; **`PT q (FDR)` is the "
        "Benjamini-Hochberg-adjusted value across all cells, and the stars reflect "
        "`q`, not raw `p`** (`*` <0.10, `**` <0.05, `***` <0.01).\n"
    )
    if note:
        lines.append(f"> {note}\n")

    cols = [
        ("model", "Model", {}),
        ("n", "N", {}),
        ("accuracy", "Acc", {"pct": True}),
        ("pt_hit_rate", "Hit", {"pct": True}),
        ("pt_p", "PT p", {"nd": 3}),
        ("pt_p_fdr", "PT q (FDR)", {"nd": 3}),
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
                if key == "pt_p_fdr":
                    val = val + _sig(row.get("pt_p_fdr"))  # stars reflect FDR-adjusted q
                cells.append(val)
            lines.append("| " + " | ".join(cells) + " |")

    lines.append(
        "\n---\n"
        "*Data:* **real** prices (SPY via Yahoo, BTC/ETH via Binance) and **real** "
        "point-in-time news (GDELT, leakage-safe `seendate`; see "
        "`data/news/MANIFEST.json`). Scored on the news-aligned clean window. These "
        "are baselines only — the market bar the LLM must beat; no LLM has run yet.\n\n"
        "*Why the FDR column matters.* Across many asset×horizon×model cells, ~1 in "
        "20 will look significant by pure chance. Here a **random** baseline lands at "
        "raw `p≈0.007` on SPY·daily — a textbook false positive (≈1.1 expected across "
        "the 21 testable cells). After the Benjamini-Hochberg correction its `q` rises "
        "well above 0.05 and it **loses its stars** — which is the point: headline "
        "claims must survive FDR, not a lone raw p-value (PRD §7.6).\n"
    )
    return "\n".join(lines)
