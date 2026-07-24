"""Fetch REAL daily OHLCV snapshots and commit them under data/prices/.

No API keys required:
  - SPY  <- Yahoo Finance chart API
  - BTC  <- Binance klines (BTCUSDT)
  - ETH  <- Binance klines (ETHUSDT)

Snapshots are written once and frozen (PRD §6.1). This realizes the PRD's
intended default — committed CSV snapshots for reproducibility — replacing the
synthetic placeholders for the price side. (News is fetched separately.)

Run:  python -m scripts.fetch_real_prices
"""

from __future__ import annotations

import io

import httpx
import pandas as pd

from src.config import REPO_ROOT

PRICES_DIR = REPO_ROOT / "data" / "prices"
UA = {"User-Agent": "Mozilla/5.0 (research; llm-market-oracle)"}


def fetch_yahoo(symbol: str, rng: str = "2y") -> pd.DataFrame:
    """Daily OHLCV from Yahoo's public chart API. Timestamped at the session close."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": rng, "interval": "1d"}
    r = httpx.get(url, params=params, headers=UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    ts = pd.to_datetime(res["timestamp"], unit="s", utc=True)
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame(
        {
            "date": ts.normalize() + pd.Timedelta(hours=21),  # ~US close, UTC
            "open": q["open"], "high": q["high"], "low": q["low"],
            "close": q["close"], "volume": q["volume"],
        }
    )
    return df.dropna(subset=["close"]).reset_index(drop=True)


def fetch_binance(symbol: str, limit: int = 1000) -> pd.DataFrame:
    """Daily OHLCV from Binance klines. Timestamped at the 00:00 UTC day boundary."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1d", "limit": limit}
    r = httpx.get(url, params=params, headers=UA, timeout=30)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(
        {
            "date": pd.to_datetime([row[0] for row in rows], unit="ms", utc=True),
            "open": [float(row[1]) for row in rows],
            "high": [float(row[2]) for row in rows],
            "low": [float(row[3]) for row in rows],
            "close": [float(row[4]) for row in rows],
            "volume": [float(row[5]) for row in rows],
        }
    )
    return df


SOURCES = {
    "SPY": lambda: fetch_yahoo("SPY", "2y"),
    "BTC": lambda: fetch_binance("BTCUSDT"),
    "ETH": lambda: fetch_binance("ETHUSDT"),
}


def main() -> None:
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    for asset, fetch in SOURCES.items():
        df = fetch()
        out = PRICES_DIR / f"{asset}.csv"
        df.to_csv(out, index=False)
        lo, hi = df["date"].iloc[0].date(), df["date"].iloc[-1].date()
        print(f"{asset}: {len(df):>4} real bars  {lo} -> {hi}  "
              f"(last close {df['close'].iloc[-1]:,.2f})")


if __name__ == "__main__":
    main()
