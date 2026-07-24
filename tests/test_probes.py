"""Offline tests for the lookahead/memorization probes (PRD §7.3).

MockLLMClient drives the probes deterministically (zero subscription usage). We
assert both the mechanics (masking scrubs dates, placebo swaps news) and that
each probe's interpretation fires on a constructed memorization signal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.assemble_context import PredictionContext
from src.data.news_providers import NewsItem
from src.predictors.llm_client import MockLLMClient
from src.predictors.llm_predictor import LLMPredictor
from src.predictors.prompts import render
from src.predictors.response_cache import ResponseCache
from src.probes.masking import mask_dates
from src.probes.placebo import placebo_context
from src.probes.runner import run_masking_probe, run_placebo_probe, run_trivia_probe
from src.probes.trivia import build_trivia_prompt, score_trivia


def _news(nid, day, headline):
    return NewsItem(nid, pd.Timestamp(f"2026-{day}T10:00:00Z"), headline)


def _ctx(as_of="2026-03-02T21:00:00Z", news=None):
    news = news or [_news("n0", "03-01", "Fed holds rates on March 1, 2026")]
    return PredictionContext(asset="SPY", horizon="daily",
                             as_of=pd.Timestamp(as_of), news=news, theta=0.01)


# ---- date masking ----
def test_mask_dates_scrubs_formats():
    assert mask_dates("2026-03-01") == "[DATE]"
    assert "[DATE]" in mask_dates("On March 3, 2026 the market rose")
    assert "2026" not in mask_dates("gains in 2026")
    assert "March 3" not in mask_dates("rally on March 3")
    assert mask_dates("no dates here") == "no dates here"


def test_masked_prompt_hides_dates():
    ctx = _ctx()
    masked = render("P0", __import__("dataclasses").replace(ctx, mask_dates=True))[1]
    assert "2026-03" not in masked          # no ISO timestamp prefix or headline date
    assert "March 3" not in masked
    assert "[DATE]" in masked or "date hidden" in masked


# ---- placebo ----
def test_placebo_swaps_news_to_mismatched_date():
    pool = [_news(f"p{i}", f"01-{i:02d}", f"Jan headline {i}") for i in range(1, 15)]
    ctx = _ctx(news=[_news("real", "03-01", "March headline")])
    rng = np.random.default_rng(0)
    placebo = placebo_context(ctx, pool, rng, min_gap_days=30, news_span_days=10)
    assert placebo.news, "placebo should provide substitute news"
    assert all(it.news_id != "real" for it in placebo.news)
    assert all(it.published_at < ctx.as_of - pd.Timedelta(days=30) for it in placebo.news)


# ---- runner: masking probe flags a date-keyed model ----
def test_masking_probe_detects_drop(tmp_path):
    # model answers UP with dates, STAY without -> big accuracy drop when true=UP.
    def fn(system, user, model):
        up = '{"prediction":"UP","prob_up":0.7,"prob_stay":0.2,"prob_down":0.1,"confidence":0.7}'
        stay = '{"prediction":"STAY","prob_up":0.3,"prob_stay":0.5,"prob_down":0.2,"confidence":0.5}'
        return stay if ("date hidden" in user or "[DATE]" in user) else up
    lp = LLMPredictor(MockLLMClient(fn=fn), "m", "P0", cache=ResponseCache(tmp_path))
    samples = [(_ctx(), "UP") for _ in range(12)]
    res = run_masking_probe(lp, samples)
    assert res.metrics["acc_normal"] > res.metrics["acc_masked"]
    assert res.metrics["drop"] >= 0.10
    assert "memorization tell" in res.interpretation


# ---- runner: placebo probe flags a news-insensitive model ----
def test_placebo_probe_flags_news_insensitivity(tmp_path):
    # model always says UP regardless of news -> placebo == real, change_rate 0.
    lp = LLMPredictor(MockLLMClient('{"prediction":"UP","prob_up":0.8,"prob_stay":0.1,"prob_down":0.1,"confidence":0.8}'),
                      "m", "P0", cache=ResponseCache(tmp_path))
    pool = [_news(f"p{i}", f"01-{(i % 28) + 1:02d}", f"h{i}") for i in range(30)]
    samples = [(_ctx(), "UP") for _ in range(10)]
    res = run_placebo_probe(lp, samples, pool)
    assert res.metrics["change_rate"] == 0.0
    assert "ignoring the news" in res.interpretation


# ---- runner: trivia probe flags memorization ----
def test_trivia_probe_flags_recall(tmp_path):
    # model recalls the true label every time -> contamination signal.
    def fn(system, user, model):
        return '{"recall":"UP","confidence":0.9}'
    client = MockLLMClient(fn=fn)
    samples = [(_ctx(), "UP") for _ in range(15)]
    res = run_trivia_probe(client, "m", ResponseCache(tmp_path), samples, lambda c: "±1%")
    assert res.metrics["recall_accuracy"] == 1.0
    assert "knows this period" in res.interpretation


def test_trivia_unknown_not_scored():
    assert score_trivia("UNKNOWN", "UP") == {"answered": False, "correct": None}
    assert score_trivia("UP", "UP")["correct"] is True
    assert score_trivia("DOWN", "UP")["correct"] is False


def test_trivia_prompt_shape():
    system, user = build_trivia_prompt("SPY", "2026-03-02T21:00:00Z", "daily", "±1%")
    assert "recall" in user.lower()
    assert "SPY" in user
