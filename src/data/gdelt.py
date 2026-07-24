"""GDELT DOC 2.0 ingestion — real, point-in-time news with trustworthy timestamps.

GDELT is open and free for research. We use the DOC 2.0 *artlist* API, which
returns article URL, title, `seendate`, and domain. No API key.

FAIRNESS-CRITICAL CHOICE — the timestamp (PRD §6.2, §7.1):
    We map ``published_at := seendate``.
    ``seendate`` is when GDELT first *observed* the article in its global crawl,
    which is always at or after the article's real publication. Using it can
    only ever make an article available to the model *later* than reality —
    never earlier — so it cannot introduce lookahead. It is the conservative,
    leakage-safe choice. (A source's self-reported publish time could be wrong
    or backdated; ``seendate`` is an independently observed lower bound on
    public availability.)

Only headlines + metadata are stored (not article bodies): that matches the
Lopez-Lira headline-labeling template (PRD §3.1) and avoids copyright issues.

The HTTP fetch lives here but is never called by the test suite; the pure
parsing/query helpers are unit-tested with static fixtures so tests stay offline.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
import pandas as pd

from src.data.news_providers import NewsItem

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
UA = {"User-Agent": "Mozilla/5.0 (research; llm-market-oracle)"}
# GDELT is slow-but-valid on success (~40s) and fast-but-throttled on failure.
# So we FAIL FAST (no long inline backoff) and rely on checkpoint/resume across
# repeated passes (PRD §13.3): each pass caches what succeeds, misses are retried
# next pass as GDELT's throttle varies. A short pace keeps us under the limit.
MIN_REQUEST_INTERVAL_S = 8.0
RETRY_BACKOFF_S = [10]  # a single quick retry; deeper retries handled by re-running

# Pre-registered, transparent per-asset queries (recorded in the manifest).
# English-only + relevance sort; targeted enough to stay on-topic.
ASSET_QUERIES = {
    "SPY": '("S&P 500" OR "stock market" OR "Wall Street" OR "Dow Jones") sourcelang:english',
    "BTC": "bitcoin sourcelang:english",
    "ETH": "ethereum sourcelang:english",
}


def build_query(asset_id: str) -> str:
    try:
        return ASSET_QUERIES[asset_id]
    except KeyError as exc:
        raise ValueError(f"no GDELT query defined for {asset_id}") from exc


def parse_seendate(raw: str) -> pd.Timestamp | None:
    """Parse GDELT's ``YYYYMMDDTHHMMSSZ`` into a tz-aware UTC Timestamp."""
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return pd.Timestamp(dt)


def _news_id(url: str) -> str:
    return "gdelt_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def parse_articles(payload: dict, asset_id: str) -> list[NewsItem]:
    """Convert a GDELT artlist JSON payload into NewsItems (untrusted ts dropped)."""
    items: list[NewsItem] = []
    for a in payload.get("articles", []):
        url = a.get("url", "")
        ts = parse_seendate(a.get("seendate", ""))
        title = (a.get("title") or "").strip()
        if not url or ts is None or not title:
            continue  # drop items lacking a trustworthy timestamp / identity
        items.append(
            NewsItem(
                news_id=_news_id(url),
                published_at=ts,
                headline=title,
                body="",
                source=a.get("domain", ""),
                assets=(asset_id,),
            )
        )
    return items


@dataclass
class _RateLimiter:
    """Simple monotonic-clock pacer so we honor GDELT's request cadence."""

    interval: float = MIN_REQUEST_INTERVAL_S
    _last: float = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        gap = self.interval - (now - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.monotonic()


def fetch_window(
    asset_id: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    max_records: int,
    limiter: _RateLimiter,
    client: httpx.Client,
) -> list[NewsItem]:
    """Fetch one time-window of news for an asset (live HTTP; not used in tests)."""
    params = {
        "query": build_query(asset_id),
        "mode": "artlist",
        "format": "json",
        "maxrecords": str(max_records),
        "sort": "hybridrel",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    }
    attempts = len(RETRY_BACKOFF_S) + 1
    last_err: Exception | None = None
    for attempt in range(attempts):
        limiter.wait()
        try:
            # GDELT can be very slow under load (20-60s); allow generous headroom
            r = client.get(GDELT_DOC_URL, params=params, headers=UA, timeout=120)
            if r.status_code == 429:
                raise RuntimeError("429 Too Many Requests")
            r.raise_for_status()
            text = r.text.strip()
            if not text.startswith("{"):
                # GDELT returns a plain-text notice (e.g. rate-limit) instead of JSON
                raise RuntimeError(f"non-JSON response: {text[:80]}")
            return parse_articles(r.json(), asset_id)
        except (httpx.HTTPError, RuntimeError) as e:
            last_err = e
            if attempt < attempts - 1:
                time.sleep(RETRY_BACKOFF_S[attempt])
    raise RuntimeError(f"GDELT fetch failed after {attempts} attempts: {last_err}")
