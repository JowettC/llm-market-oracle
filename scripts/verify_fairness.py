"""Audit the committed news corpus for fairness (PRD §7.1, §7.2, §6.4).

A standalone, re-runnable check a skeptic can use to convince themselves the
study cannot cheat. It verifies, on the REAL committed corpus:

  1. every ``published_at`` is tz-aware UTC and <= the recorded fetch instant
     (no physically-impossible / future articles);
  2. the point-in-time gate leaks nothing — at many probe times, every admitted
     item is strictly before the decision instant;
  3. how much of the corpus is CLEAN (dated after the model's training cutoff)
     vs. CONTAMINATED (at/before cutoff), per PRD §7.2.

Exit code is non-zero if any hard fairness invariant fails.

Run:  python -m scripts.verify_fairness
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from src.config import REPO_ROOT, load_config
from src.data.assemble_context import assemble_context
from src.data.news_providers import JSONLNewsProvider

NEWS_DIR = REPO_ROOT / "data" / "news"


def _clean_cutoffs(cfg) -> dict[str, pd.Timestamp]:
    """Earliest LLM training cutoff per config — the clean-window boundary."""
    cutoffs = [
        pd.Timestamp(m["training_cutoff"], tz="UTC")
        for m in cfg["models"]
        if m.get("kind") == "llm" and m.get("training_cutoff")
    ]
    return min(cutoffs) if cutoffs else None


def main() -> int:
    cfg = load_config()
    provider = JSONLNewsProvider()
    manifest_path = NEWS_DIR / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    fetched_at = pd.Timestamp(manifest["fetched_at"]) if manifest.get("fetched_at") else pd.Timestamp.now(tz="UTC")
    cutoff = _clean_cutoffs(cfg)

    print("=" * 68)
    print("FAIRNESS AUDIT — committed news corpus")
    print("=" * 68)
    print(f"fetched_at (manifest): {fetched_at}")
    print(f"clean-window cutoff (min LLM training_cutoff): {cutoff}")
    print("-" * 68)

    failures = 0
    for asset in [a["id"] for a in cfg["assets"]]:
        items = provider.get_items(asset)
        if not items:
            print(f"{asset}: (no corpus committed yet)")
            continue
        ts = pd.Series([i.published_at for i in items])

        # (1) UTC + no future
        naive = sum(1 for t in ts if t.tzinfo is None)
        future = int((ts > fetched_at).sum())
        # (3) clean vs contaminated split
        clean = int((ts > cutoff).sum()) if cutoff is not None else len(ts)
        contaminated = len(ts) - clean

        # (2) gate leakage probe at 8 evenly spaced decision instants
        lo, hi = ts.min(), ts.max()
        leaks = 0
        for frac in [i / 9 for i in range(1, 9)]:
            as_of = lo + (hi - lo) * frac
            ctx = assemble_context(as_of, asset, "daily", news_provider=provider)
            leaks += sum(1 for it in ctx.news if it.published_at >= as_of)

        ok = (naive == 0 and future == 0 and leaks == 0)
        failures += 0 if ok else 1
        print(f"{asset}: {len(items):>5} items  {lo.date()}..{hi.date()}")
        print(f"     UTC-naive={naive}  future={future}  gate-leaks={leaks}  "
              f"{'✅ PASS' if ok else '❌ FAIL'}")
        print(f"     clean(post-cutoff)={clean}  contaminated(<=cutoff)={contaminated}")

    print("-" * 68)
    if failures:
        print(f"❌ {failures} asset(s) FAILED a hard fairness invariant")
        return 1
    print("✅ all committed corpora pass the fairness invariants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
