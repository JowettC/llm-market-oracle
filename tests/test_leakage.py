"""THE leakage test (PRD §12.2) — fails loudly if future data ever leaks in.

This is the guard the whole study leans on. If `assemble_context` ever admits a
news item dated at or after the decision time, or exposes price bars from the
future, these tests must go red. Keep them strict.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.data.assemble_context import assemble_context
from src.data.market_providers import CSVMarketProvider
from src.data.news_providers import JSONLNewsProvider, NewsItem


# ---- a hand-built provider with news bracketing a known decision instant ----
class _FakeNews(JSONLNewsProvider):
    def __init__(self, items):
        self._items = items

    def get_items(self, asset_id):  # noqa: D401
        return list(self._items)


def _item(nid, ts):
    return NewsItem(news_id=nid, published_at=pd.Timestamp(ts, tz="UTC"), headline=nid)


AS_OF = pd.Timestamp("2025-06-15T21:00:00Z")


@pytest.fixture
def bracketing_news():
    return _FakeNews(
        [
            _item("past_1", "2025-06-14T10:00:00Z"),      # admissible
            _item("past_2", "2025-06-15T20:59:59Z"),      # admissible (before as_of)
            _item("exact", "2025-06-15T21:00:00Z"),       # NOT admissible (== as_of, strict <)
            _item("future_1", "2025-06-15T21:00:01Z"),    # NOT admissible
            _item("future_2", "2025-07-01T10:00:00Z"),    # NOT admissible
        ]
    )


def test_no_future_news_admitted(bracketing_news):
    ctx = assemble_context(AS_OF, "SPY", "daily", news_provider=bracketing_news)
    ids = set(ctx.news_ids)
    assert ids == {"past_1", "past_2"}, f"leaked future/at-instant news: {ids}"


def test_every_admitted_item_strictly_precedes_as_of(bracketing_news):
    ctx = assemble_context(AS_OF, "SPY", "daily", news_provider=bracketing_news)
    for item in ctx.news:
        assert item.published_at < ctx.as_of, f"{item.news_id} not strictly before as_of"


def test_at_instant_item_is_excluded(bracketing_news):
    """A headline stamped exactly at the decision instant is treated as unavailable."""
    ctx = assemble_context(AS_OF, "SPY", "daily", news_provider=bracketing_news)
    assert "exact" not in ctx.news_ids


def test_provenance_matches_admitted_news(bracketing_news):
    ctx = assemble_context(AS_OF, "SPY", "daily", news_provider=bracketing_news)
    # the audit trail (news_ids) must be exactly what was exposed, nothing more.
    assert ctx.news_ids == [n.news_id for n in ctx.news]


def test_price_history_never_reaches_future():
    news = _FakeNews([])
    market = CSVMarketProvider()
    ctx = assemble_context(
        AS_OF, "SPY", "daily", news_provider=news,
        market_provider=market, condition="news_plus_price",
    )
    assert ctx.price_history is not None
    assert (ctx.price_history.index < ctx.as_of).all(), "price context includes future bars"
    assert ctx.price_as_of < ctx.as_of


def test_untrusted_timestamp_dropped(tmp_path):
    """Items with missing/garbage timestamps are dropped (PRD §6.2)."""
    p = tmp_path / "XYZ.jsonl"
    with p.open("w") as fh:
        fh.write(json.dumps({"news_id": "good", "published_at": "2025-01-01T00:00:00Z", "headline": "h"}) + "\n")
        fh.write(json.dumps({"news_id": "no_ts", "headline": "h"}) + "\n")
        fh.write(json.dumps({"news_id": "bad_ts", "published_at": "not-a-date", "headline": "h"}) + "\n")
    prov = JSONLNewsProvider(news_dir=tmp_path, drop_untrusted_timestamps=True)
    ids = {i.news_id for i in prov.get_items("XYZ")}
    assert ids == {"good"}, f"kept an untrusted-timestamp item: {ids}"


def test_real_sample_corpus_is_gated():
    """End-to-end over the committed sample data: nothing at/after as_of leaks."""
    news = JSONLNewsProvider()
    market = CSVMarketProvider()
    as_of = pd.Timestamp("2025-03-10T21:00:00Z")
    for asset in ("SPY", "BTC", "ETH"):
        ctx = assemble_context(
            as_of, asset, "daily", news_provider=news,
            market_provider=market, condition="news_plus_price",
        )
        for item in ctx.news:
            assert item.published_at < as_of
        if ctx.price_history is not None and not ctx.price_history.empty:
            assert (ctx.price_history.index < as_of).all()
