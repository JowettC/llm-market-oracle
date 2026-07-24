"""News data providers behind one interface (PRD §6.2).

Every news item MUST carry a trustworthy ``published_at`` timestamp — a wrong
timestamp is the single biggest source of accidental lookahead (PRD §6.2), so
items with missing/untrusted timestamps are dropped when configured.

The clean-vs-historical corpus is a config switch, not a code change. Phase 1
ships a committed JSONL backend (``data/news/<ASSET>.jsonl``) so the pipeline
and the leakage test run fully offline; live feeds (GDELT, Alpha Vantage,
CryptoPanic, FNSPID loader) slot in behind the same interface later.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.config import REPO_ROOT


@dataclass(frozen=True)
class NewsItem:
    """One point-in-time news record. ``published_at`` is tz-aware UTC."""

    news_id: str
    published_at: pd.Timestamp
    headline: str
    body: str = ""
    source: str = ""
    assets: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "news_id": self.news_id,
            "published_at": self.published_at.isoformat(),
            "headline": self.headline,
            "body": self.body,
            "source": self.source,
            "assets": list(self.assets),
        }


class NewsDataProvider(ABC):
    """Interface every news backend implements."""

    @abstractmethod
    def get_items(self, asset_id: str) -> list[NewsItem]:
        """All available news items tagged for ``asset_id``, any time order."""
        raise NotImplementedError


class JSONLNewsProvider(NewsDataProvider):
    """Reads ``data/news/<ASSET>.jsonl`` — one JSON object per line.

    Required per-line fields: news_id, published_at, headline.
    Optional: body, source, assets (list).
    """

    def __init__(self, news_dir: str | Path = "data/news", drop_untrusted_timestamps: bool = True):
        self.news_dir = (REPO_ROOT / news_dir) if not Path(news_dir).is_absolute() else Path(news_dir)
        self.drop_untrusted_timestamps = drop_untrusted_timestamps
        self._cache: dict[str, list[NewsItem]] = {}

    def get_items(self, asset_id: str) -> list[NewsItem]:
        if asset_id in self._cache:
            return self._cache[asset_id]
        path = self.news_dir / f"{asset_id}.jsonl"
        if not path.exists():
            self._cache[asset_id] = []
            return []
        items: list[NewsItem] = []
        with path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                ts = self._parse_timestamp(rec.get("published_at"))
                if ts is None:
                    if self.drop_untrusted_timestamps:
                        continue
                    raise ValueError(f"{path}:{lineno} untrusted/missing published_at")
                for req in ("news_id", "headline"):
                    if req not in rec:
                        raise ValueError(f"{path}:{lineno} missing '{req}'")
                items.append(
                    NewsItem(
                        news_id=str(rec["news_id"]),
                        published_at=ts,
                        headline=rec["headline"],
                        body=rec.get("body", ""),
                        source=rec.get("source", ""),
                        assets=tuple(rec.get("assets", [asset_id])),
                    )
                )
        self._cache[asset_id] = items
        return items

    @staticmethod
    def _parse_timestamp(raw) -> pd.Timestamp | None:
        if raw is None or raw == "":
            return None
        try:
            ts = pd.Timestamp(raw)
        except (ValueError, TypeError):
            return None
        if pd.isna(ts):
            return None
        return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def get_news_provider(cfg: dict) -> NewsDataProvider:
    """Factory: build the news provider from config (default: committed JSONL)."""
    data_cfg = cfg.get("data", {})
    return JSONLNewsProvider(
        news_dir=data_cfg.get("news_dir", "data/news"),
        drop_untrusted_timestamps=data_cfg.get("drop_untrusted_timestamps", True),
    )
