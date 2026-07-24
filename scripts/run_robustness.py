"""Robustness analyses for the baselines (PRD §5.3, §8.4, H4).

Two checks, so results don't hinge on one arbitrary choice and so decay is visible:

  1. theta-sensitivity — re-score across the pre-registered band widths
     (label_band.sensitivity_k). Shows how the STAY class balance and each
     baseline's accuracy shift as the neutral band widens/narrows.
  2. rolling decay — split each asset's daily scored window into equal sub-periods
     and report per-period accuracy + buy&hold Sharpe, to expose non-stationarity
     (H4: skill/behavior drifts over time).

No LLM access needed. Writes results/robustness.md.

Run:  python -m scripts.run_robustness
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from src.backtest.metrics import directional_accuracy, sharpe
from src.backtest.portfolio import compute_backtest
from src.config import REPO_ROOT, load_config
from src.data.market_providers import get_market_provider
from src.data.news_providers import get_news_provider
from src.labeling import STAY, build_labels, horizon_steps
from src.report.scoring import score_cell
from src.run import build_baselines, scored_and_calib_windows
from src.predictors.baselines import estimate_class_freq
from src.backtest.walk_forward import run_walk_forward


def theta_sensitivity(cfg, market, news, asset, kind, band_cfg, seed):
    """Accuracy + STAY-rate per baseline across sensitivity_k, daily horizon."""
    ks = band_cfg.get("sensitivity_k", [0.25, 0.5, 1.0])
    close = market.get_ohlcv(asset)["close"]
    lookback = cfg.get("calibration", {}).get("lookback_days", 90)
    s0, s1, c0, c1 = scored_and_calib_windows(close, news, asset, lookback)
    kind_map = {a["id"]: a["kind"] for a in cfg["assets"]}
    rows = []
    for k in ks:
        bc = copy.deepcopy(band_cfg)
        bc["method"] = "vol_scaled"
        bc.setdefault("vol_scaled", {})["k"] = k
        labeled = build_labels(close, asset, kind, "daily", bc)
        scored = labeled.label[(labeled.label.index >= s0) & (labeled.label.index <= s1)].dropna()
        stay_rate = float((scored == STAY).mean()) if len(scored) else float("nan")
        calib_freq = estimate_class_freq(
            labeled.label[(labeled.label.index >= c0) & (labeled.label.index < c1)])
        for pred in build_baselines(cfg, market, kind_map, calib_freq, seed):
            recs = run_walk_forward(pred, asset, kind, "daily", bc,
                                    news_provider=news, market_provider=market,
                                    window_start=s0, window_end=s1, condition="news_only")
            if recs.empty:
                continue
            acc = directional_accuracy(recs["prediction"].tolist(),
                                       recs["realized_label"].tolist())
            rows.append({"k": k, "stay_rate": stay_rate, "model": pred.model_id, "acc": acc})
    return pd.DataFrame(rows)


def rolling_decay(cfg, market, news, asset, kind, band_cfg, seed, n_periods=4):
    """Per-sub-period accuracy (sentiment, momentum) + buy&hold Sharpe, daily."""
    close = market.get_ohlcv(asset)["close"]
    lookback = cfg.get("calibration", {}).get("lookback_days", 90)
    s0, s1, c0, c1 = scored_and_calib_windows(close, news, asset, lookback)
    kind_map = {a["id"]: a["kind"] for a in cfg["assets"]}
    labeled = build_labels(close, asset, kind, "daily", band_cfg)
    calib_freq = estimate_class_freq(
        labeled.label[(labeled.label.index >= c0) & (labeled.label.index < c1)])
    preds = {p.model_id: p for p in build_baselines(cfg, market, kind_map, calib_freq, seed)}
    steps = horizon_steps(kind, "daily")

    out = []
    for name in ("baseline_sentiment", "baseline_momentum", "baseline_buy_hold"):
        recs = run_walk_forward(preds[name], asset, kind, "daily", band_cfg,
                                news_provider=news, market_provider=market,
                                window_start=s0, window_end=s1, condition="news_only")
        if recs.empty:
            continue
        recs = recs.sort_values("as_of").reset_index(drop=True)
        bounds = np.linspace(0, len(recs), n_periods + 1).astype(int)
        for i in range(1, n_periods + 1):
            ch = recs.iloc[bounds[i - 1]:bounds[i]]
            if ch.empty:
                continue
            acc = directional_accuracy(ch["prediction"].tolist(), ch["realized_label"].tolist())
            bt = compute_backtest(ch, close, steps, 10.0, cfg)
            shp = sharpe(bt.strategy_returns, cfg["portfolio"]["annualization"]["daily"])
            lo, hi = ch["as_of"].iloc[0].date(), ch["as_of"].iloc[-1].date()
            out.append({"model": name, "period": f"P{i} ({lo}..{hi})", "n": len(ch),
                        "acc": acc, "sharpe": shp})
    return pd.DataFrame(out)


def _fmt(v):
    return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else (
        f"{v:.3f}" if isinstance(v, float) else str(v))


def main() -> None:
    cfg = load_config()
    seed = int(cfg.get("seed", 42))
    market = get_market_provider(cfg)
    news = get_news_provider(cfg)
    band_cfg = cfg["label_band"]

    lines = ["# Robustness — θ-sensitivity & rolling decay\n",
             "Baselines only (no LLM). Daily horizon. Shows results don't hinge on one "
             "band width, and exposes non-stationarity over the window (PRD §5.3, H4).\n"]

    for a in cfg["assets"]:
        asset, kind = a["id"], a["kind"]
        lines.append(f"\n## {asset}\n\n### θ-sensitivity (accuracy by band width k)\n")
        ts = theta_sensitivity(cfg, market, news, asset, kind, band_cfg, seed)
        if not ts.empty:
            piv = ts.pivot_table(index="model", columns="k", values="acc")
            stay = ts.groupby("k")["stay_rate"].first()
            lines.append("STAY-rate by k: " + ", ".join(f"k={k}: {v:.0%}" for k, v in stay.items()) + "\n")
            header = "| model | " + " | ".join(f"k={k} acc" for k in piv.columns) + " |"
            sep = "| --- | " + " | ".join("---" for _ in piv.columns) + " |"
            lines += [header, sep]
            for model, row in piv.iterrows():
                lines.append("| " + model + " | " + " | ".join(_fmt(row[k]) for k in piv.columns) + " |")

        lines.append("\n### Rolling decay (per sub-period)\n")
        rd = rolling_decay(cfg, market, news, asset, kind, band_cfg, seed)
        if not rd.empty:
            lines.append("| model | period | n | acc | Sharpe |")
            lines.append("| --- | --- | --- | --- | --- |")
            for _, r in rd.iterrows():
                lines.append(f"| {r['model']} | {r['period']} | {r['n']} | "
                             f"{_fmt(r['acc'])} | {_fmt(r['sharpe'])} |")

    out = REPO_ROOT / "results" / "robustness.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
