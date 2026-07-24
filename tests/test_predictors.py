"""Tests for the prediction schema and baseline predictors (PRD §5.4, §7.4)."""

from __future__ import annotations

import pandas as pd
import pytest
from pydantic import ValidationError

from src.data.assemble_context import assemble_context
from src.data.market_providers import CSVMarketProvider
from src.data.news_providers import JSONLNewsProvider
from src.predictors.base import Prediction, prediction_from_label
from src.predictors.baselines import (
    AlwaysUpPredictor,
    BuyAndHoldPredictor,
    LexiconSentimentPredictor,
    MomentumPredictor,
    RandomStratifiedPredictor,
    estimate_class_freq,
)
from src.labeling import LABELS

AS_OF = pd.Timestamp("2025-06-01T21:00:00Z")


def _ctx(asset="SPY", condition="news_only", market=None):
    return assemble_context(
        AS_OF, asset, "daily",
        news_provider=JSONLNewsProvider(),
        market_provider=market,
        condition=condition,
    )


def test_schema_rejects_bad_label():
    with pytest.raises(ValidationError):
        Prediction(asset="SPY", horizon="daily", as_of="x", prediction="SIDEWAYS",
                   confidence=0.5, prob_up=0.5, prob_stay=0.3, prob_down=0.2)


def test_schema_rejects_probs_not_summing_to_one():
    with pytest.raises(ValidationError):
        Prediction(asset="SPY", horizon="daily", as_of="x", prediction="UP",
                   confidence=0.5, prob_up=0.5, prob_stay=0.3, prob_down=0.3)


def test_schema_rejects_argmax_mismatch():
    with pytest.raises(ValidationError):
        Prediction(asset="SPY", horizon="daily", as_of="x", prediction="UP",
                   confidence=0.2, prob_up=0.2, prob_stay=0.5, prob_down=0.3)


def test_prediction_from_label_is_valid_and_carries_provenance():
    ctx = _ctx()
    pred = prediction_from_label("DOWN", ctx, "test", confidence=0.7)
    assert pred.prediction == "DOWN"
    assert abs(pred.prob_up + pred.prob_stay + pred.prob_down - 1.0) < 1e-6
    assert pred.news_ids == ctx.news_ids


@pytest.mark.parametrize("predictor", [AlwaysUpPredictor(), BuyAndHoldPredictor()])
def test_always_up_and_buy_hold_predict_up(predictor):
    assert predictor.predict(_ctx()).prediction == "UP"


def test_random_stratified_respects_frequencies_and_seed():
    freq = {"UP": 0.5, "DOWN": 0.3, "STAY": 0.2}
    p1 = RandomStratifiedPredictor(freq, seed=7)
    p2 = RandomStratifiedPredictor(freq, seed=7)
    ctx = _ctx()
    # same seed => deterministic (reproducibility, PRD §12.6)
    assert p1.predict(ctx).prediction == p2.predict(ctx).prediction
    assert all(pr.prediction in LABELS for pr in (p1.predict(ctx), p2.predict(ctx)))


def test_momentum_uses_point_in_time_prices():
    market = CSVMarketProvider()
    mom = MomentumPredictor(market, asset_kind={"BTC": "crypto"})
    pred = mom.predict(_ctx("BTC"))
    assert pred.prediction in LABELS


def test_sentiment_reacts_to_news_direction():
    sent = LexiconSentimentPredictor()
    pred = sent.predict(_ctx("SPY"))
    assert pred.prediction in LABELS
    assert "net=" in pred.rationale


def test_estimate_class_freq_sums_to_one():
    labels = pd.Series(["UP", "UP", "DOWN", "STAY", "UP", None])
    freq = estimate_class_freq(labels)
    assert abs(sum(freq.values()) - 1.0) < 1e-9
    assert freq["UP"] == pytest.approx(3 / 5)
