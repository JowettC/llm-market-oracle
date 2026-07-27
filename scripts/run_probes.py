"""Run the lookahead/memorization probes against Claude (PRD §7.3).

    python -m scripts.run_probes --asset SPY --limit 20            # real Claude (Max sub)
    python -m scripts.run_probes --asset SPY --limit 20 --dry-run  # count calls only

Probes: date-masking, placebo-news, future-trivia. Results and their plain
interpretations are printed and written to results/probes.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import REPO_ROOT, asset_by_id, load_config
from src.data.market_providers import get_market_provider
from src.data.news_providers import get_news_provider
from src.predictors.llm_client import (
    BudgetExceededError,
    ClaudeCLIClient,
    LLMUsageLimitError,
    UsageBudget,
)
from src.predictors.llm_predictor import LLMPredictor
from src.predictors.response_cache import ResponseCache
from src.probes.runner import run_masking_probe, run_placebo_probe, run_trivia_probe
from src.backtest.walk_forward import iter_decision_contexts


def _theta_pct(ctx):
    return f"±{ctx.theta * 100:.2f}%" if ctx.theta is not None else "a small band"


def main() -> None:
    ap = argparse.ArgumentParser(description="Lookahead/memorization probes")
    ap.add_argument("--asset", default="SPY")
    ap.add_argument("--horizon", default="daily")
    ap.add_argument("--model", default=None, help="LLM model id in config (default: first enabled/any)")
    ap.add_argument("--prompt", default="P0")
    ap.add_argument("--limit", type=int, default=20, help="number of decision samples")
    ap.add_argument("--dry-run", action="store_true", help="estimate Claude calls, make none")
    ap.add_argument("--budget-calls", type=int, default=None, help="hard ceiling on NEW calls")
    args = ap.parse_args()

    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    budget_calls = args.budget_calls if args.budget_calls is not None else llm_cfg.get("budget_calls")
    _cache_dir = llm_cfg.get("cache_dir", "cache/llm")
    window_state = str((REPO_ROOT / _cache_dir / ".window_calls") if not Path(_cache_dir).is_absolute()
                       else Path(_cache_dir) / ".window_calls")
    budget = UsageBudget(max_calls=budget_calls, state_file=window_state) if budget_calls else None
    market = get_market_provider(cfg)
    news = get_news_provider(cfg)
    band_cfg = cfg["label_band"]
    asset = asset_by_id(cfg, args.asset)
    kind = asset["kind"]

    model_string = next((m["model_string"] for m in cfg["models"]
                         if m.get("kind") == "llm" and (args.model is None or m["id"] == args.model)),
                        None)
    if model_string is None:
        raise SystemExit("no LLM model found in config")

    cache = ResponseCache(cfg.get("llm", {}).get("cache_dir", "cache/llm"))
    client = ClaudeCLIClient()
    predictor = LLMPredictor(client, model_string, args.prompt, cache=cache,
                             model_id=f"probe:{model_string}:{args.prompt}", budget=budget)

    # collect samples over the clean (news) window
    n_start, n_end = None, None
    items = news.get_items(args.asset)
    if items:
        ts = sorted(i.published_at for i in items)
        n_start, n_end = ts[0], ts[-1]
    samples = []
    for _i, ctx, label, _r, _t in iter_decision_contexts(
            args.asset, kind, args.horizon, band_cfg, news, market, n_start, n_end):
        samples.append((ctx, label))
        if len(samples) >= args.limit:
            break

    if not samples:
        raise SystemExit("no samples (is the news corpus present?)")

    if args.dry_run:
        # masking: normal+masked (2N), placebo: real+placebo (2N), trivia: N  -> ~5N calls,
        # minus whatever is already cached.
        est = 5 * len(samples)
        print(f"[dry-run] ~{est} Claude calls for {len(samples)} samples "
              f"(masking 2N + placebo 2N + trivia N), minus cached. No calls made.")
        return

    print(f"Running probes on {args.asset}·{args.horizon} with {len(samples)} samples "
          f"({model_string}, {args.prompt})\n")
    try:
        results = [
            run_masking_probe(predictor, samples),
            run_placebo_probe(predictor, samples, items),
            run_trivia_probe(client, model_string, cache, samples, _theta_pct, budget=budget),
        ]
    except (BudgetExceededError, LLMUsageLimitError) as e:
        spent = budget.calls if budget else "?"
        print(f"\n⚠️  stopping LLM runs — budget/limit reached ({spent} new calls). "
              f"Cache preserves progress; resume later. {str(e)[:100]}")
        raise SystemExit(3)
    lines = [f"# Lookahead / memorization probes — {args.asset}·{args.horizon}\n",
             f"Model `{model_string}`, prompt `{args.prompt}`, {len(samples)} samples "
             f"from the clean window. See PRD §7.3.\n"]
    for r in results:
        print(r.summary(), "\n")
        lines.append(f"### {r.name}\n\n- n = {r.n}\n"
                     + "\n".join(f"- {k}: {v}" for k, v in r.metrics.items())
                     + f"\n\n**Interpretation:** {r.interpretation}\n")

    out = REPO_ROOT / "results" / f"probes_{args.asset}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
