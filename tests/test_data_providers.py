"""Tests for the market/news providers and config loader."""

from __future__ import annotations

import pandas as pd

from src.config import asset_ids, load_config
from src.data.market_providers import OHLCV_COLUMNS, CSVMarketProvider, get_market_provider
from src.data.news_providers import get_news_provider


def test_config_loads_and_has_assets():
    cfg = load_config()
    assert asset_ids(cfg) == ["SPY", "BTC", "ETH"]
    assert cfg["label_band"]["method"] in ("fixed", "vol_scaled")


def test_market_provider_shape_and_ordering():
    m = CSVMarketProvider()
    df = m.get_ohlcv("SPY")
    assert list(df.columns) == OHLCV_COLUMNS
    assert df.index.is_monotonic_increasing
    assert df.index.tz is not None
    assert not df.index.has_duplicates


def test_close_at_is_point_in_time():
    m = CSVMarketProvider()
    df = m.get_ohlcv("BTC")
    mid = df.index[100]
    close = m.close_at("BTC", mid)
    assert close == df["close"].iloc[100]
    # a timestamp between bars returns the most recent PAST close, never a future one
    between = mid + pd.Timedelta(hours=12)
    assert m.close_at("BTC", between) == df["close"].iloc[100]


def test_news_provider_reads_sample():
    cfg = load_config()
    n = get_news_provider(cfg)
    items = n.get_items("ETH")
    assert len(items) > 0
    assert all(i.published_at.tzinfo is not None for i in items)


def test_market_factory_default_csv():
    cfg = load_config()
    assert isinstance(get_market_provider(cfg), CSVMarketProvider)
