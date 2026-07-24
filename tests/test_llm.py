"""Offline tests for the LLM harness (PRD §5.4, §5.5, §13.2-13.4).

No subscription usage: a MockLLMClient supplies scripted responses so prompting,
JSON parsing, schema reconciliation, caching, backoff, and the dry-run estimator
are all exercised deterministically.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.assemble_context import PredictionContext
from src.data.news_providers import NewsItem
from src.predictors.llm_client import LLMUsageLimitError, MockLLMClient
from src.predictors.llm_predictor import LLMPredictor, parse_model_json
from src.predictors.prompts import RESPONSE_CONTRACT, render
from src.predictors.response_cache import ResponseCache


def _ctx(news=("h1", "h2"), condition="news_only", theta=0.01):
    items = [NewsItem(f"n{i}", pd.Timestamp("2026-03-01T10:00:00Z"), h) for i, h in enumerate(news)]
    return PredictionContext(
        asset="SPY", horizon="daily", as_of=pd.Timestamp("2026-03-02T21:00:00Z"),
        news=items, condition=condition, theta=theta,
    )


_GOOD = '{"prediction":"UP","prob_up":0.6,"prob_stay":0.3,"prob_down":0.1,"confidence":0.6,"rationale":"bullish"}'


def test_prompts_render_all_variants():
    ctx = _ctx()
    for pid in ("P0", "P1", "P2", "P3"):
        system, user = render(pid, ctx)
        assert system and user
        assert RESPONSE_CONTRACT.split("\n")[0] in user  # contract embedded
        assert "SPY" in user
    # theta surfaced as a percentage band
    assert "±1.00%" in render("P0", ctx)[1]


def test_prompts_price_block_only_with_price_condition():
    ctx_np = _ctx(condition="news_only")
    assert "Recent closes" not in render("P0", ctx_np)[1]


def test_parse_model_json_tolerates_fences_and_prose():
    assert parse_model_json(_GOOD)["prediction"] == "UP"
    fenced = "```json\n" + _GOOD + "\n```"
    assert parse_model_json(fenced)["prediction"] == "UP"
    prosed = "Here is my answer:\n" + _GOOD + "\nThanks!"
    assert parse_model_json(prosed)["prob_up"] == 0.6
    assert parse_model_json("no json here") == {}


def test_llm_predictor_produces_valid_prediction(tmp_path):
    lp = LLMPredictor(MockLLMClient(_GOOD), "claude-x", "P0",
                      cache=ResponseCache(tmp_path), model_id="claude_opus:P0")
    pred = lp.predict(_ctx())
    assert pred.prediction == "UP"
    assert abs(pred.prob_up + pred.prob_stay + pred.prob_down - 1.0) < 1e-6
    assert pred.model == "claude_opus:P0"
    assert pred.news_ids == ["n0", "n1"]


def test_llm_predictor_reconciles_argmax_mismatch(tmp_path):
    # model says UP but puts most mass on DOWN -> must still yield a valid schema
    bad = '{"prediction":"UP","prob_up":0.1,"prob_stay":0.2,"prob_down":0.7,"confidence":0.5}'
    lp = LLMPredictor(MockLLMClient(bad), "claude-x", "P0", cache=ResponseCache(tmp_path))
    pred = lp.predict(_ctx())
    probs = {"UP": pred.prob_up, "STAY": pred.prob_stay, "DOWN": pred.prob_down}
    assert max(probs, key=probs.__getitem__) == pred.prediction  # schema invariant holds


def test_llm_predictor_handles_garbage_without_crashing(tmp_path):
    lp = LLMPredictor(MockLLMClient("the model refused"), "claude-x", "P0", cache=ResponseCache(tmp_path))
    pred = lp.predict(_ctx())
    assert pred.prediction in ("UP", "DOWN", "STAY")  # neutral fallback, valid schema


def test_cache_avoids_second_call(tmp_path):
    client = MockLLMClient(_GOOD)
    lp = LLMPredictor(client, "claude-x", "P0", cache=ResponseCache(tmp_path))
    ctx = _ctx()
    lp.predict(ctx)
    lp.predict(ctx)  # identical (model, prompt, news_ids) -> cache hit
    assert len(client.calls) == 1, "second identical prediction should hit the cache"


def test_cache_key_depends_on_news_ids(tmp_path):
    cache = ResponseCache(tmp_path)
    lp = LLMPredictor(MockLLMClient(_GOOD), "claude-x", "P0", cache=cache)
    assert lp.cache_key(_ctx(("a",))) != lp.cache_key(_ctx(("a", "b")))


def test_is_cached_reflects_state(tmp_path):
    client = MockLLMClient(_GOOD)
    lp = LLMPredictor(client, "claude-x", "P0", cache=ResponseCache(tmp_path))
    ctx = _ctx()
    assert not lp.is_cached(ctx)   # dry-run would count this as a call
    lp.predict(ctx)
    assert lp.is_cached(ctx)       # now cached -> no call


def test_usage_limit_backoff_then_raises(tmp_path, monkeypatch):
    import src.predictors.llm_predictor as mod
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)  # no real waiting

    def always_limit(system, user, model):
        raise LLMUsageLimitError("usage limit reached")

    client = MockLLMClient(fn=always_limit)
    lp = LLMPredictor(client, "claude-x", "P0", cache=ResponseCache(tmp_path),
                      max_retries=3, backoff_seconds=[0, 0, 0])
    with pytest.raises(LLMUsageLimitError):
        lp.predict(_ctx())
    assert len(client.calls) == 4  # initial + 3 retries
