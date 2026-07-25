"""Entry point: run the baseline backtests and regenerate committed results.

    python -m src.run                      # full baseline sweep
    python -m src.run --smoke              # daily horizon only (quick)
    python -m src.run --config other.yaml

The baseline half needs NO LLM access and produces the real, committed results
that establish the market-performance bar (PRD §8.4, Phase 2). The LLM half
(Phase 3) slots the same-interface Claude predictors into the identical loop.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.config import REPO_ROOT, asset_by_id, load_config
from src.data.market_providers import get_market_provider
from src.data.news_providers import get_news_provider
from src.labeling import build_labels, horizon_steps
from src.predictors.baselines import (
    AlwaysUpPredictor,
    BuyAndHoldPredictor,
    LexiconSentimentPredictor,
    MomentumPredictor,
    RandomStratifiedPredictor,
    estimate_class_freq,
)
from src.predictors.llm_client import ClaudeCLIClient, LLMUsageLimitError
from src.predictors.llm_predictor import LLMPredictor
from src.predictors.response_cache import ResponseCache
from src.report.plots import equity_curve_figure
from src.report.scoring import score_cell
from src.report.tables import results_markdown
from src.backtest.walk_forward import iter_decision_contexts, run_walk_forward


def build_llm_predictors(cfg, cache, prompts, model_filter):
    """Instantiate LLMPredictors for enabled Claude models × prompt variants.

    Runs on the Claude Max subscription via `claude -p` (no API key, §13.4).
    An LLM model is included if config marks it enabled, or if named in
    ``model_filter`` (e.g. from --llm-model on the CLI).
    """
    llm_cfg = cfg.get("llm", {})
    client = ClaudeCLIClient()
    preds = []
    for m in cfg["models"]:
        if m.get("kind") != "llm":
            continue
        if not (m.get("enabled", False) or (model_filter and m["id"] in model_filter)):
            continue
        for p in prompts:
            preds.append(LLMPredictor(
                client, m["model_string"], prompt_id=p, cache=cache,
                model_id=f"{m['id']}:{p}",
                max_retries=int(llm_cfg.get("max_retries", 5)),
                backoff_seconds=llm_cfg.get("backoff_seconds"),
            ))
    return preds


def estimate_llm_calls(predictor, asset_id, kind, horizon, band_cfg, news, market,
                       start, end, condition, max_news, max_decisions):
    """Count decisions and cache-miss (billable) calls without making any (§13.3)."""
    total = misses = 0
    for _i, ctx, *_ in iter_decision_contexts(
        asset_id, kind, horizon, band_cfg, news, market, start, end, condition, max_news):
        if max_decisions is not None and total >= max_decisions:
            break
        total += 1
        if not predictor.is_cached(ctx):
            misses += 1
    return total, misses


def build_baselines(cfg, market, asset_kind_map, calib_freq, seed):
    """Instantiate the five baselines (PRD §7.4); random uses calibrated freqs."""
    return [
        AlwaysUpPredictor(),
        BuyAndHoldPredictor(),
        RandomStratifiedPredictor(calib_freq, seed=seed),
        MomentumPredictor(market, asset_kind_map),
        LexiconSentimentPredictor(),
    ]


def news_window(news_provider, asset_id: str):
    """(earliest, latest) published_at for an asset, or (None, None) if no news."""
    items = news_provider.get_items(asset_id)
    if not items:
        return None, None
    ts = sorted(i.published_at for i in items)
    return ts[0], ts[-1]


def scored_and_calib_windows(close: pd.Series, news_provider, asset_id: str, lookback_days: int):
    """Align the scored window to the NEWS corpus so every baseline is judged on
    identical decisions; calibrate on the disjoint price history just before it.

    With real news covering only a recent window, scoring the full price history
    would make the news-based predictors incoherent. We therefore score all
    models on [news_start, news_end] and calibrate θ/class-freq strictly earlier.
    Falls back to a price-only split when an asset has no news.
    """
    price_start, price_end = close.index[0], close.index[-1]
    n_start, n_end = news_window(news_provider, asset_id)
    if n_start is None:  # no news committed for this asset
        scored_start = price_start + pd.Timedelta(days=lookback_days)
        return scored_start, price_end, price_start, scored_start
    scored_start = max(price_start, n_start)
    scored_end = min(price_end, n_end)
    calib_hi = scored_start
    calib_lo = max(price_start, scored_start - pd.Timedelta(days=lookback_days))
    return scored_start, scored_end, calib_lo, calib_hi


def main() -> None:
    ap = argparse.ArgumentParser(description="Baseline + LLM backtests -> committed results")
    ap.add_argument("--config", default=None)
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--smoke", action="store_true", help="daily horizon only")
    ap.add_argument("--assets", nargs="*", default=None, help="subset of asset ids (default: all)")
    ap.add_argument("--no-baselines", action="store_true", help="skip baselines")
    ap.add_argument("--llm", action="store_true", help="include LLM predictors (Claude Max, no key)")
    ap.add_argument("--llm-model", nargs="*", default=None,
                    help="LLM model ids to run even if disabled in config")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --llm: report the number of Claude calls, make none (§13.3)")
    ap.add_argument("--prompts", nargs="*", default=None, help="prompt ids (default: config)")
    ap.add_argument("--conditions", nargs="*", default=None,
                    help="input conditions (default: config)")
    ap.add_argument("--llm-max-news", type=int, default=40, help="cap news items per LLM prompt")
    ap.add_argument("--llm-limit", type=int, default=None,
                    help="cap decisions per LLM cell (cheap smoke run)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    seed = int(cfg.get("seed", 42))
    market = get_market_provider(cfg)
    news = get_news_provider(cfg)
    band_cfg = cfg["label_band"]
    asset_kind_map = {a["id"]: a["kind"] for a in cfg["assets"]}

    horizons = ["daily"] if args.smoke else list(cfg["horizons"].keys())
    out_dir = Path(args.output_dir) if args.output_dir else (REPO_ROOT / "results")
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts = args.prompts or cfg.get("prompts", ["P0"])
    conditions = args.conditions or cfg.get("conditions", ["news_only"])
    cache = ResponseCache(cfg.get("llm", {}).get("cache_dir", "cache/llm"))
    llm_predictors = build_llm_predictors(cfg, cache, prompts, args.llm_model) if (args.llm or args.dry_run) else []
    dry_total_calls = 0
    usage_limit_hit = False

    assets = cfg["assets"] if not args.assets else [a for a in cfg["assets"] if a["id"] in args.assets]

    all_rows = []
    for asset in assets:
        asset_id, kind = asset["id"], asset["kind"]
        cost_bps = float(asset.get("cost_bps_round_trip", 10))
        close = market.get_ohlcv(asset_id)["close"]
        lookback = cfg.get("calibration", {}).get("lookback_days", 90)
        scored_start, scored_end, calib_lo, calib_hi = scored_and_calib_windows(
            close, news, asset_id, lookback)
        print(f"# {asset_id}: score {scored_start.date()}..{scored_end.date()}  "
              f"(calib {calib_lo.date()}..{calib_hi.date()})")

        for horizon in horizons:
            # calibrate the stratified-random class frequencies on the calib window only
            labeled = build_labels(close, asset_id, kind, horizon, band_cfg)
            calib_mask = (labeled.label.index >= calib_lo) & (labeled.label.index < calib_hi)
            calib_freq = estimate_class_freq(labeled.label[calib_mask])

            records_by_model: dict[str, pd.DataFrame] = {}
            baselines = [] if args.no_baselines else build_baselines(
                cfg, market, asset_kind_map, calib_freq, seed)
            for predictor in baselines:
                records = run_walk_forward(
                    predictor, asset_id, kind, horizon, band_cfg,
                    news_provider=news, market_provider=market,
                    window_start=scored_start, window_end=scored_end,
                    condition="news_only",
                )
                if records.empty:
                    continue
                records_by_model[predictor.model_id] = records
                all_rows.append(score_cell(records, close, kind, horizon, cost_bps, cfg))
                print(f"scored {asset_id:>3} · {horizon:<7} · {predictor.model_id}"
                      f"  (n={len(records)})")

            # ---- LLM predictors (Claude Max subscription; §5.6, §9, §13.4) ----
            for lp in llm_predictors:
                for condition in conditions:
                    cell = f"{lp.model_id}:{condition}"
                    if args.dry_run:
                        total, misses = estimate_llm_calls(
                            lp, asset_id, kind, horizon, band_cfg, news, market,
                            scored_start, scored_end, condition, args.llm_max_news, args.llm_limit)
                        dry_total_calls += misses
                        print(f"[dry-run] {asset_id:>3} · {horizon:<7} · {cell}: "
                              f"{total} decisions, {misses} uncached Claude calls")
                        continue
                    try:
                        records = run_walk_forward(
                            lp, asset_id, kind, horizon, band_cfg,
                            news_provider=news, market_provider=market,
                            window_start=scored_start, window_end=scored_end,
                            condition=condition, max_news=args.llm_max_news,
                            max_decisions=args.llm_limit,
                        )
                    except LLMUsageLimitError as e:
                        print(f"\n⚠️  Claude usage limit reached at {cell} — stopping LLM "
                              f"runs and saving partial results (cache preserves progress; "
                              f"resume after reset). {str(e)[:120]}")
                        usage_limit_hit = True
                        break
                    if records.empty:
                        continue
                    records_by_model[cell] = records
                    all_rows.append(score_cell(records, close, kind, horizon, cost_bps, cfg))
                    print(f"scored {asset_id:>3} · {horizon:<7} · {cell}  (n={len(records)})")
                if usage_limit_hit:
                    break

            # one equity-curve figure per asset at the primary (daily) horizon
            if horizon == "daily" and records_by_model:
                equity_curve_figure(
                    records_by_model, close, asset_id, horizon, kind, cost_bps, cfg,
                    out_dir / "figures" / f"equity_{asset_id}_{horizon}.png",
                )
            if usage_limit_hit:
                break
        if usage_limit_hit:
            break

    if args.dry_run:
        print(f"\n[dry-run] total uncached Claude calls that a real run would make: "
              f"{dry_total_calls}")
        print("[dry-run] no calls were made and no results were written.")
        return

    if not all_rows:
        print("no cells scored (nothing enabled?).")
        return

    df = pd.DataFrame(all_rows)
    # FDR-adjust the PT p-values across ALL cells (PRD §7.6) so a lone lucky
    # p-value doesn't read as real skill.
    from src.backtest.metrics import benjamini_hochberg
    df["pt_p_fdr"] = benjamini_hochberg(df["pt_p"].tolist())

    csv_path = out_dir / "baseline_metrics.csv"
    md_path = out_dir / "baseline_results.md"
    df.to_csv(csv_path, index=False)
    md_path.write_text(results_markdown(df), encoding="utf-8")
    print(f"\nwrote {csv_path} and {md_path}")
    print(f"{len(df)} cells scored across {df['asset'].nunique()} assets × "
          f"{df['horizon'].nunique()} horizons")


if __name__ == "__main__":
    main()
