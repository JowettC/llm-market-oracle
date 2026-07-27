"""Generate headline summary figures for the README (no LLM calls).

Reads committed metrics + the cached predictions and produces two punchy charts:
  1. Sharpe: following Claude vs. just holding (the economic verdict)
  2. Claude's DOWN-share of predictions by prompt (the structural bearish bias)

Palettes are Okabe-Ito based and validated CVD-safe (dataviz skill); every bar
carries a direct value label (secondary encoding + resolves the contrast WARN).

Run:  python -m scripts.make_summary_figures
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import REPO_ROOT, load_config  # noqa: E402
from src.data.market_providers import get_market_provider  # noqa: E402
from src.data.news_providers import get_news_provider  # noqa: E402
from src.predictors.llm_client import ClaudeCLIClient, UsageBudget  # noqa: E402
from src.predictors.llm_predictor import LLMPredictor  # noqa: E402
from src.predictors.response_cache import ResponseCache  # noqa: E402
from src.backtest.walk_forward import run_walk_forward  # noqa: E402
from src.run import scored_and_calib_windows  # noqa: E402

FIG_DIR = REPO_ROOT / "results" / "figures"
ASSETS = [("SPY", "equity"), ("BTC", "crypto"), ("ETH", "crypto")]
INK, MUTED, GRID = "#1a1a1a", "#666666", "#dddddd"
TRIO = {"SPY": "#0072B2", "BTC": "#E69F00", "ETH": "#009E73"}   # validated CVD-safe
CLAUDE_C, HOLD_C = "#D55E00", "#0072B2"                         # validated pair


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_sharpe(cfg):
    """Grouped bars: Claude P0 Sharpe vs Buy&Hold Sharpe, per asset."""
    df = pd.read_csv(REPO_ROOT / "results" / "llm_sweep" / "baseline_metrics.csv")
    assets = [a for a, _ in ASSETS]
    claude = [float(df[(df.asset == a) & (df.model == "claude_opus:P0")]["sharpe"].iloc[0]) for a in assets]
    hold = [float(df[(df.asset == a) & (df.model == "claude_opus:P0")]["bh_sharpe"].iloc[0]) for a in assets]

    x = np.arange(len(assets))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.6))
    b1 = ax.bar(x - w / 2, claude, w, label="Follow Claude", color=CLAUDE_C, zorder=3)
    b2 = ax.bar(x + w / 2, hold, w, label="Just hold (buy & hold)", color=HOLD_C, zorder=3)
    ax.axhline(0, color=INK, linewidth=1.0, zorder=4)
    for bars in (b1, b2):
        for r in bars:
            h = r.get_height()
            ax.annotate(f"{h:+.2f}", (r.get_x() + r.get_width() / 2, h),
                        ha="center", va="bottom" if h >= 0 else "top",
                        fontsize=10, color=INK, xytext=(0, 3 if h >= 0 else -3),
                        textcoords="offset points")
    ax.set_xticks(x, assets)
    ax.set_ylabel("Sharpe ratio (net of cost)", color=MUTED, fontsize=10)
    ax.set_title("Following Claude's news calls vs. just holding the asset",
                 color=INK, fontsize=13, fontweight="bold", pad=12)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    _style(ax)
    fig.tight_layout()
    out = FIG_DIR / "summary_sharpe.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    return out


def fig_capital(cfg, start=10000):
    """Grouped bars: ending capital from a $10k start — follow Claude vs. hold."""
    df = pd.read_csv(REPO_ROOT / "results" / "llm_sweep" / "baseline_metrics.csv")
    assets = [a for a, _ in ASSETS]
    claude = [start * float(df[(df.asset == a) & (df.model == "claude_opus:P0")]["final_equity"].iloc[0]) for a in assets]
    hold = [start * float(df[(df.asset == a) & (df.model == "claude_opus:P0")]["bh_final_equity"].iloc[0]) for a in assets]

    x = np.arange(len(assets))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.8))
    b1 = ax.bar(x - w / 2, claude, w, label="Follow Claude", color=CLAUDE_C, zorder=3)
    b2 = ax.bar(x + w / 2, hold, w, label="Just hold (buy & hold)", color=HOLD_C, zorder=3)
    ax.axhline(start, color=INK, linewidth=1.2, linestyle="--", zorder=4)
    ax.annotate(f"start: ${start:,}", (2.42, start), color=INK, fontsize=9,
                va="center", ha="left")
    for bars in (b1, b2):
        for r in bars:
            h = r.get_height()
            ax.annotate(f"${h:,.0f}", (r.get_x() + r.get_width() / 2, h), ha="center",
                        va="bottom", fontsize=10, color=INK, xytext=(0, 3),
                        textcoords="offset points")
    ax.set_xticks(x, assets)
    ax.set_ylabel("Ending capital (USD)", color=MUTED, fontsize=10)
    ax.set_ylim(0, max(max(claude), max(hold)) * 1.15)
    ax.set_title(f"${start:,} over the 6.5-month test — follow Claude vs. just hold",
                 color=INK, fontsize=13, fontweight="bold", pad=12)
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    ax.yaxis.set_major_formatter(lambda v, _p: f"${v/1000:.0f}k")
    _style(ax)
    fig.tight_layout()
    out = FIG_DIR / "summary_capital.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    return out


def fig_bias(cfg):
    """Grouped bars: Claude's DOWN-share of predictions by prompt, per asset."""
    market = get_market_provider(cfg); news = get_news_provider(cfg)
    band = cfg["label_band"]; cache = ResponseCache("cache/llm"); client = ClaudeCLIClient()
    zero = UsageBudget(max_calls=0)  # guarantees zero new calls
    prompts = ["P0", "P1", "P2", "P3"]
    down = {a: [] for a, _ in ASSETS}
    for aid, kind in ASSETS:
        close = market.get_ohlcv(aid)["close"]
        s0, s1, c0, c1 = scored_and_calib_windows(close, news, aid, 90)
        for p in prompts:
            lp = LLMPredictor(client, "claude-opus-4-8", p, cache=cache,
                              model_id=f"claude_opus:{p}", budget=zero)
            recs = run_walk_forward(lp, aid, kind, "daily", band, news_provider=news,
                                    market_provider=market, window_start=s0, window_end=s1,
                                    condition="news_only", max_news=40)
            down[aid].append(100.0 * (recs.prediction == "DOWN").mean())

    x = np.arange(len(prompts))
    w = 0.26
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for i, (aid, _) in enumerate(ASSETS):
        bars = ax.bar(x + (i - 1) * w, down[aid], w, label=aid, color=TRIO[aid], zorder=3)
        for r in bars:
            h = r.get_height()
            ax.annotate(f"{h:.0f}", (r.get_x() + r.get_width() / 2, h), ha="center",
                        va="bottom", fontsize=9, color=INK, xytext=(0, 2),
                        textcoords="offset points")
    ax.axhline(33.3, color=MUTED, linewidth=1.0, linestyle="--", zorder=4)
    ax.annotate("balanced (33%)", (3.4, 33.3), color=MUTED, fontsize=9, va="center")
    ax.set_xticks(x, ["P0\nzero-shot", "P1\nchain-of-thought", "P2\nstructured", "P3\nsentiment"])
    ax.set_ylabel("% of predictions that were DOWN", color=MUTED, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_title("Claude's reflexive bearishness on crypto — same under every prompt",
                 color=INK, fontsize=13, fontweight="bold", pad=12)
    ax.legend(frameon=False, fontsize=10, loc="upper right", ncol=3)
    _style(ax)
    fig.tight_layout()
    out = FIG_DIR / "summary_bias.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    return out


def main():
    cfg = load_config()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    print("wrote", fig_capital(cfg))
    print("wrote", fig_sharpe(cfg))
    print("wrote", fig_bias(cfg))


if __name__ == "__main__":
    main()
