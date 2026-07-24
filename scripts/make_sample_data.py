"""Generate small, deterministic SAMPLE fixtures for offline dev & tests.

These are SYNTHETIC placeholders (clearly marked) so the pipeline, baselines,
and the leakage test run with zero network. Real snapshots replace them via the
live providers (PRD §6.1-6.2). Deterministic: fixed seed, no wall-clock use.

Run:  python -m scripts.make_sample_data
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import REPO_ROOT

PRICES_DIR = REPO_ROOT / "data" / "prices"
NEWS_DIR = REPO_ROOT / "data" / "news"

# One clean, self-contained year of daily bars.
START = "2025-01-01"
N_DAYS = 400
SEED = 42

# (asset, kind, start_price, annual_drift, annual_vol)
ASSETS = [
    ("SPY", "equity", 480.0, 0.08, 0.16),
    ("BTC", "crypto", 42000.0, 0.30, 0.65),
    ("ETH", "crypto", 2300.0, 0.25, 0.80),
]

_POS = ["surges on strong earnings", "rallies as inflation cools", "gains on upgrade",
        "jumps after record profit", "climbs on adoption news", "boosted by partnership"]
_NEG = ["plunges on weak guidance", "falls as fears mount", "drops after downgrade",
        "slumps on selloff", "declines amid recession warning", "sinks after probe"]
_NEUTRAL = ["trades sideways in quiet session", "little changed ahead of data",
            "holds steady as traders wait", "mixed as volume thins"]


def _calendar(kind: str) -> pd.DatetimeIndex:
    all_days = pd.date_range(START, periods=N_DAYS, freq="D", tz="UTC")
    if kind == "equity":
        return all_days[all_days.weekday < 5]  # weekdays only
    return all_days  # crypto 24/7


def make_prices(rng: np.random.Generator, kind: str, p0: float, mu: float, sigma: float) -> pd.DataFrame:
    idx = _calendar(kind)
    n = len(idx)
    dt = 1 / 252
    daily_ret = rng.normal(mu * dt, sigma * np.sqrt(dt), n)
    close = p0 * np.exp(np.cumsum(daily_ret))
    open_ = np.concatenate([[p0], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.003, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.003, n)))
    vol = rng.integers(1_000_000, 5_000_000, n)
    return pd.DataFrame(
        {"date": idx, "open": open_, "high": high, "low": low, "close": close, "volume": vol}
    )


def make_news(rng: np.random.Generator, asset: str, prices: pd.DataFrame) -> list[dict]:
    """One headline per bar whose tone loosely tracks that bar's realized move.

    Timestamped ~14:30 UTC (before a US close / within the crypto day) so it is
    admissible for that day's decision. Tone is intentionally noisy — sentiment
    is a weak signal, exactly as in reality.
    """
    items = []
    closes = prices["close"].to_numpy()
    for i, row in prices.iterrows():
        move = 0.0 if i == 0 else closes[i] / closes[i - 1] - 1.0
        roll = rng.random()
        if move > 0.005 and roll > 0.3:
            phrase = rng.choice(_POS)
        elif move < -0.005 and roll > 0.3:
            phrase = rng.choice(_NEG)
        elif roll > 0.6:
            phrase = rng.choice(_POS if move >= 0 else _NEG)
        else:
            phrase = rng.choice(_NEUTRAL)
        ts = pd.Timestamp(row["date"]).replace(hour=14, minute=30)
        items.append(
            {
                "news_id": f"sample_{asset}_{i:04d}",
                "published_at": ts.isoformat(),
                "headline": f"{asset} {phrase}",
                "body": "",
                "source": "SYNTHETIC_SAMPLE",
                "assets": [asset],
            }
        )
    return items


def main() -> None:
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    for asset, kind, p0, mu, sigma in ASSETS:
        prices = make_prices(rng, kind, p0, mu, sigma)
        prices.to_csv(PRICES_DIR / f"{asset}.csv", index=False)
        news = make_news(rng, asset, prices)
        with (NEWS_DIR / f"{asset}.jsonl").open("w", encoding="utf-8") as fh:
            for item in news:
                fh.write(json.dumps(item) + "\n")
        print(f"{asset}: {len(prices)} bars, {len(news)} news items")


if __name__ == "__main__":
    main()
