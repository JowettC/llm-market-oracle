"""Fetch a REAL point-in-time news corpus (GDELT) and commit it under data/news/.

Walks the clean window in weekly chunks, paced within GDELT's rate limit, with
retry-with-backoff AND checkpoint/resume (PRD §13.3): every successful chunk is
cached to ``data/news/.cache/`` (git-ignored), so re-running skips finished
chunks and only fills gaps — the crawl converges to full coverage across runs
even when GDELT throttles.

Uses ``seendate`` as a conservative, leakage-safe ``published_at`` (see
src/data/gdelt.py). Runs §6.4 quality checks and records provenance in
data/news/MANIFEST.json.

Run (re-run until it reports 0 missing chunks):
    python -m scripts.fetch_real_news
    python -m scripts.fetch_real_news --start 2026-01-01 --end 2026-07-23
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from src.config import REPO_ROOT
from src.data.gdelt import ASSET_QUERIES, _RateLimiter, build_query, fetch_window
from src.data.news_providers import NewsItem
from src.data.quality import clean_news

NEWS_DIR = REPO_ROOT / "data" / "news"
CACHE_DIR = NEWS_DIR / ".cache"
DEFAULT_START = "2026-01-01"
DEFAULT_END = "2026-07-23"
DEFAULT_MAX = 250  # articles per weekly chunk per asset (GDELT max; denser coverage)


def time_chunks(start: pd.Timestamp, end: pd.Timestamp, days: int):
    cur, step = start, pd.Timedelta(days=days)
    while cur < end:
        yield cur, min(cur + step, end)
        cur += step


def _cache_path(asset: str, c0: pd.Timestamp, c1: pd.Timestamp) -> Path:
    return CACHE_DIR / f"{asset}__{c0.strftime('%Y%m%d')}_{c1.strftime('%Y%m%d')}.json"


def _item_from_dict(d: dict) -> NewsItem:
    return NewsItem(
        news_id=d["news_id"], published_at=pd.Timestamp(d["published_at"]),
        headline=d["headline"], body=d.get("body", ""),
        source=d.get("source", ""), assets=tuple(d.get("assets", [])),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch real GDELT news corpus (resumable)")
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    ap.add_argument("--max-records", type=int, default=DEFAULT_MAX)
    ap.add_argument("--chunk-days", type=int, default=7,
                    help="window size per request; 7=weekly (dense), 30=monthly (coarse, fewer requests)")
    ap.add_argument("--assets", nargs="*", default=list(ASSET_QUERIES.keys()))
    args = ap.parse_args()

    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")
    fetched_at = pd.Timestamp(datetime.now(timezone.utc))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    limiter = _RateLimiter()
    chunks = list(time_chunks(start, end, args.chunk_days))
    manifest = {
        "source": "GDELT DOC 2.0 artlist (https://api.gdeltproject.org)",
        "timestamp_field": "seendate (conservative: >= real publication; leakage-safe)",
        "sort": "hybridrel",
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "chunk_days": args.chunk_days,
        "max_records_per_chunk": args.max_records,
        "fetched_at": fetched_at.isoformat(),
        "note": ("Headlines + metadata only (no bodies). English only, hybridrel sort. "
                 f"{args.chunk_days}-day chunks, resumable. Coverage is best-effort under "
                 "GDELT rate limits; see per-asset distinct_days below."),
        "assets": {},
    }
    total_missing_before = sum(
        1 for a in args.assets for c0, c1 in chunks if not _cache_path(a, c0, c1).exists()
    )
    print(f"{len(args.assets)} assets x {len(chunks)} weekly chunks; "
          f"{total_missing_before} not yet cached\n")

    still_missing = 0
    with httpx.Client() as client:
        for asset in args.assets:
            for i, (c0, c1) in enumerate(chunks, 1):
                cp = _cache_path(asset, c0, c1)
                if cp.exists():
                    continue  # checkpoint hit — skip
                try:
                    items = fetch_window(asset, c0, c1, args.max_records, limiter, client)
                    cp.write_text(json.dumps([it.to_dict() for it in items]), encoding="utf-8")
                    print(f"  {asset} [{i:>2}/{len(chunks)}] {c0.date()}..{c1.date()}: +{len(items)} cached")
                except Exception as e:  # noqa: BLE001
                    still_missing += 1
                    print(f"  {asset} [{i:>2}/{len(chunks)}] {c0.date()}..{c1.date()}: "
                          f"MISS ({type(e).__name__}: {str(e)[:60]})")

            # assemble this asset's corpus from ALL cached chunks
            raw: list[NewsItem] = []
            cached_chunks = 0
            for c0, c1 in chunks:
                cp = _cache_path(asset, c0, c1)
                if cp.exists():
                    cached_chunks += 1
                    raw.extend(_item_from_dict(d) for d in json.loads(cp.read_text()))
            clean, report = clean_news(raw, fetched_at)
            with (NEWS_DIR / f"{asset}.jsonl").open("w", encoding="utf-8") as fh:
                for it in clean:
                    fh.write(json.dumps(it.to_dict()) + "\n")
            distinct_days = len({it.published_at.date() for it in clean})
            manifest["assets"][asset] = {
                "query": build_query(asset),
                "chunks_cached": cached_chunks,
                "chunks_total": len(chunks),
                "distinct_days": distinct_days,
                "quality": report.as_dict(),
            }
            print(f"  -> {asset}: {report.kept} items, {distinct_days} distinct days, "
                  f"{cached_chunks}/{len(chunks)} chunks\n")

    (NEWS_DIR / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if still_missing:
        print(f"⚠️  {still_missing} chunks still missing — RE-RUN to fill gaps (resumable).")
    else:
        print("✅ all chunks cached.")


if __name__ == "__main__":
    main()
