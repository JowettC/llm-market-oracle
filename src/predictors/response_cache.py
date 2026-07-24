"""On-disk LLM response cache (PRD §13.2).

Keyed by (model, system, user, news_ids) so a rerun is deterministic and never
re-spends subscription usage. The cache dir is git-ignored (can be large); its
hash manifest could be committed for verification. Every avoided call is
preserved quota — doubly important under a subscription (PRD §13.2, §11).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.config import REPO_ROOT


class ResponseCache:
    def __init__(self, cache_dir: str | Path = "cache/llm"):
        self.cache_dir = (REPO_ROOT / cache_dir) if not Path(cache_dir).is_absolute() else Path(cache_dir)

    @staticmethod
    def key(model: str, system: str, user: str, news_ids: list[str]) -> str:
        payload = json.dumps(
            {"model": model, "system": system, "user": user, "news_ids": sorted(news_ids)},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> str | None:
        p = self._path(key)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))["text"]

    def put(self, key: str, text: str, meta: dict | None = None) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(
            json.dumps({"text": text, "meta": meta or {}}), encoding="utf-8"
        )

    def has(self, key: str) -> bool:
        return self._path(key).exists()
