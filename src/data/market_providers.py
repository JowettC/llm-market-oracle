"""Market (price) data providers behind one interface (PRD §6.1).

The backtest is source-agnostic: a ``MarketDataProvider`` yields point-in-time
OHLCV for an asset, and the default backend reads committed CSV snapshots under
``data/prices/`` so the study is fully reproducible offline. Live backends
(yfinance / Stooq / Polygon / Tiingo) can be slotted in behind the same
interface when a network is available.

Prices are snapshotted once and frozen — never revised look-back (PRD §6.1).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from src.config import REPO_ROOT

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


class MarketDataProvider(ABC):
    """Interface every price backend implements."""

    @abstractmethod
    def get_ohlcv(self, asset_id: str) -> pd.DataFrame:
        """Return a UTC-DatetimeIndex frame with columns OHLCV_COLUMNS.

        Index must be sorted ascending, unique, tz-aware (UTC), one row per bar.
        """
        raise NotImplementedError

    def close_at(self, asset_id: str, as_of: pd.Timestamp) -> float | None:
        """Most recent close at or before ``as_of`` (point-in-time safe)."""
        df = self.get_ohlcv(asset_id)
        window = df.loc[df.index <= _to_utc(as_of)]
        if window.empty:
            return None
        return float(window["close"].iloc[-1])


class CSVMarketProvider(MarketDataProvider):
    """Reads ``data/prices/<ASSET>.csv``.

    CSV schema: a ``date`` column (ISO-8601, UTC) plus open,high,low,close,volume.
    """

    def __init__(self, prices_dir: str | Path = "data/prices"):
        self.prices_dir = (REPO_ROOT / prices_dir) if not Path(prices_dir).is_absolute() else Path(prices_dir)
        self._cache: dict[str, pd.DataFrame] = {}

    def get_ohlcv(self, asset_id: str) -> pd.DataFrame:
        if asset_id in self._cache:
            return self._cache[asset_id]
        path = self.prices_dir / f"{asset_id}.csv"
        if not path.exists():
            raise FileNotFoundError(f"no price snapshot for {asset_id}: {path}")
        df = pd.read_csv(path)
        if "date" not in df.columns:
            raise ValueError(f"{path} missing 'date' column")
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date").sort_index()
        missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"{path} missing columns: {missing}")
        df = df[OHLCV_COLUMNS]
        if df.index.has_duplicates:
            raise ValueError(f"{path} has duplicate timestamps")
        self._cache[asset_id] = df
        return df


def get_market_provider(cfg: dict) -> MarketDataProvider:
    """Factory: build the provider named in config (default: csv)."""
    kind = cfg.get("data", {}).get("market_provider", "csv")
    if kind == "csv":
        return CSVMarketProvider(cfg.get("data", {}).get("prices_dir", "data/prices"))
    raise NotImplementedError(
        f"market_provider '{kind}' not wired yet; only 'csv' ships in Phase 1"
    )


def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
