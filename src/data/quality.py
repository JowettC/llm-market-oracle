"""Data-quality checks run before any news is scored (PRD §6.4).

These are fairness guards, not cosmetics: a duplicate inflates a headline's
weight, a non-UTC timestamp corrupts the point-in-time gate, and a timestamp
after the fetch instant is physically impossible (an article we could not have
seen). Each is caught here, centrally, before the corpus is committed.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.data.news_providers import NewsItem


@dataclass
class QualityReport:
    kept: int
    dropped_duplicate: int
    dropped_future: int
    dropped_untrusted_ts: int
    earliest: pd.Timestamp | None
    latest: pd.Timestamp | None

    def as_dict(self) -> dict:
        return {
            "kept": self.kept,
            "dropped_duplicate": self.dropped_duplicate,
            "dropped_future": self.dropped_future,
            "dropped_untrusted_ts": self.dropped_untrusted_ts,
            "earliest": self.earliest.isoformat() if self.earliest is not None else None,
            "latest": self.latest.isoformat() if self.latest is not None else None,
        }


def clean_news(items: list[NewsItem], fetched_at: pd.Timestamp) -> tuple[list[NewsItem], QualityReport]:
    """Dedup, enforce UTC, and drop physically-impossible (future) timestamps.

    ``fetched_at`` is the wall-clock instant the crawl ran; nothing can carry a
    ``published_at`` after it (we could not have observed a not-yet-seen article).
    """
    fetched_at = _utc(fetched_at)
    seen_ids: set[str] = set()
    kept: list[NewsItem] = []
    dup = future = untrusted = 0

    for it in items:
        ts = it.published_at
        if ts is None or pd.isna(ts):
            untrusted += 1
            continue
        ts = _utc(ts)
        if ts.tzinfo is None:
            untrusted += 1
            continue
        if ts > fetched_at:
            future += 1
            continue
        if it.news_id in seen_ids:
            dup += 1
            continue
        seen_ids.add(it.news_id)
        # normalize timestamp to UTC on the stored item
        kept.append(NewsItem(
            news_id=it.news_id, published_at=ts, headline=it.headline,
            body=it.body, source=it.source, assets=it.assets,
        ))

    kept.sort(key=lambda n: n.published_at)
    earliest = kept[0].published_at if kept else None
    latest = kept[-1].published_at if kept else None
    return kept, QualityReport(len(kept), dup, future, untrusted, earliest, latest)


def _utc(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
