"""Offline tests for GDELT parsing + data-quality guards (PRD §6.2, §6.4).

No network: a static GDELT-shaped payload exercises the pure functions. The
fairness guarantees (leakage-safe timestamp, dedup, future guard) are asserted
here so a regression fails the build.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.gdelt import build_query, parse_articles, parse_seendate
from src.data.news_providers import NewsItem
from src.data.quality import clean_news

FETCHED_AT = pd.Timestamp("2026-07-24T00:00:00Z")

_PAYLOAD = {
    "articles": [
        {"url": "https://a.com/1", "seendate": "20260301T231500Z",
         "title": "Bitcoin rallies to new high", "domain": "a.com"},
        {"url": "https://b.com/2", "seendate": "20260302T091500Z",
         "title": "Ethereum upgrade ships", "domain": "b.com"},
        {"url": "https://a.com/1", "seendate": "20260301T231500Z",  # exact duplicate url
         "title": "Bitcoin rallies to new high", "domain": "a.com"},
        {"url": "https://c.com/3", "seendate": "bogus-timestamp",   # untrusted ts -> dropped
         "title": "Should be dropped", "domain": "c.com"},
        {"url": "https://d.com/4", "seendate": "20260303T101500Z",
         "title": "", "domain": "d.com"},                          # empty title -> dropped
    ]
}


def test_parse_seendate_utc():
    ts = parse_seendate("20260301T231500Z")
    assert ts == pd.Timestamp("2026-03-01T23:15:00Z")
    assert ts.tzinfo is not None
    assert parse_seendate("garbage") is None
    assert parse_seendate("") is None


def test_parse_articles_drops_bad_rows():
    items = parse_articles(_PAYLOAD, "BTC")
    # 5 raw rows -> drop untrusted-ts and empty-title -> 3 remain (incl. the dup url)
    assert len(items) == 3
    assert all(it.published_at.tzinfo is not None for it in items)
    assert all(it.headline for it in items)


def test_news_id_is_stable_and_url_derived():
    a = parse_articles(_PAYLOAD, "BTC")
    ids = [it.news_id for it in a]
    # the duplicate URL yields the SAME id -> dedup can catch it downstream
    assert ids.count(ids[0]) == 2
    assert all(i.startswith("gdelt_") for i in ids)


def test_clean_news_dedups_and_sorts():
    items = parse_articles(_PAYLOAD, "BTC")
    clean, rep = clean_news(items, FETCHED_AT)
    assert rep.dropped_duplicate == 1
    assert rep.kept == 2
    # sorted ascending by published_at
    assert clean[0].published_at <= clean[1].published_at


def test_clean_news_future_guard():
    future = NewsItem("f1", pd.Timestamp("2027-01-01T00:00:00Z"), "from the future")
    good = NewsItem("g1", pd.Timestamp("2026-05-01T00:00:00Z"), "real")
    clean, rep = clean_news([future, good], FETCHED_AT)
    assert rep.dropped_future == 1
    assert [c.news_id for c in clean] == ["g1"]


def test_clean_news_normalizes_naive_ts_to_utc():
    naive = NewsItem("n1", pd.Timestamp("2026-05-01T00:00:00"), "naive ts")  # no tz
    clean, rep = clean_news([naive], FETCHED_AT)
    assert rep.kept == 1
    assert clean[0].published_at.tzinfo is not None


def test_build_query_known_and_unknown():
    assert "sourcelang:english" in build_query("BTC")
    with pytest.raises(ValueError):
        build_query("DOGE")
