"""Honest, strong baselines — the "market performance general" bar (PRD §7.4).

The LLM must beat these, not just beat 33% random. None of them need any LLM
access, so they run out-of-the-box and produce the committed baseline results
that establish the bar (PRD §8.4, Phase 2).

    Always-UP            exploits equities' upward drift
    Random (stratified)  honest chance level given class imbalance
    Momentum             predict continuation of last period's move
    Buy-and-hold         the economic benchmark (always long); as a label = UP
    Lexicon sentiment    news-sentiment classifier -> direction

All emit the shared Prediction schema via ``prediction_from_label`` (PRD §5.4).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.assemble_context import PredictionContext
from src.data.market_providers import MarketDataProvider
from src.labeling import DOWN, LABELS, STAY, UP, horizon_steps
from src.predictors.base import Predictor, prediction_from_label


class AlwaysUpPredictor(Predictor):
    """Predict UP every period (PRD §7.4). Deceptively strong for SPY."""

    model_id = "baseline_always_up"

    def predict(self, context: PredictionContext):
        return prediction_from_label(UP, context, self.model_id, confidence=0.5,
                                     rationale="always-up baseline")


class BuyAndHoldPredictor(Predictor):
    """The 'just hold the asset' benchmark. Directionally == always long == UP.

    Distinct id from always-up so the economic lens can label its equity curve
    'buy-and-hold' explicitly (PRD §7.4, §10.2).
    """

    model_id = "baseline_buy_hold"

    def predict(self, context: PredictionContext):
        return prediction_from_label(UP, context, self.model_id, confidence=0.5,
                                     rationale="buy-and-hold benchmark")


class RandomStratifiedPredictor(Predictor):
    """Sample from historical class frequencies (PRD §7.4).

    Frequencies are estimated on the calibration window ONLY, never the test set.
    Uses a seeded RNG for reproducibility (PRD §12.6).
    """

    model_id = "baseline_random"

    def __init__(self, class_freq: dict[str, float], seed: int = 42):
        total = sum(class_freq.get(c, 0.0) for c in LABELS)
        if total <= 0:
            raise ValueError("class_freq must have positive mass")
        self.p = np.array([class_freq.get(c, 0.0) / total for c in LABELS])
        self._rng = np.random.default_rng(seed)

    def predict(self, context: PredictionContext):
        label = str(self._rng.choice(LABELS, p=self.p))
        conf = float(self.p[LABELS.index(label)])
        return prediction_from_label(label, context, self.model_id,
                                     confidence=max(conf, 1e-3),
                                     rationale="stratified random baseline")


class MomentumPredictor(Predictor):
    """Predict continuation of the last horizon's move (PRD §7.4).

    Needs price context regardless of the input condition, so it holds its own
    market provider and reads the trailing return point-in-time (< as_of).
    """

    model_id = "baseline_momentum"

    def __init__(self, market_provider: MarketDataProvider, asset_kind: dict[str, str],
                 theta: float = 0.0):
        self.market = market_provider
        self.asset_kind = asset_kind  # asset_id -> 'equity'|'crypto'
        self.theta = theta

    def predict(self, context: PredictionContext):
        kind = self.asset_kind.get(context.asset, "equity")
        steps = horizon_steps(kind, context.horizon)
        ohlcv = self.market.get_ohlcv(context.asset)
        hist = ohlcv.loc[ohlcv.index < context.as_of, "close"]
        label, conf = STAY, 0.34
        if len(hist) > steps:
            last_ret = float(hist.iloc[-1] / hist.iloc[-1 - steps] - 1.0)
            if last_ret > self.theta:
                label = UP
            elif last_ret < -self.theta:
                label = DOWN
            conf = min(0.5 + abs(last_ret) * 5, 0.9)
        return prediction_from_label(label, context, self.model_id, confidence=conf,
                                     rationale=f"momentum: last {context.horizon} move")


# A tiny, transparent finance lexicon — deliberately simple so it represents the
# "off-the-shelf sentiment" bar the LLM must beat (PRD §7.4). Not FinBERT, but
# the same role; swap in FinBERT behind this interface later without changing scoring.
_POSITIVE = {
    "beat", "beats", "surge", "surges", "rally", "rallies", "gain", "gains", "soar",
    "soars", "record", "growth", "profit", "profits", "upgrade", "bullish", "jump",
    "jumps", "rise", "rises", "strong", "boost", "outperform", "approval", "adopt",
    "adoption", "partnership", "expansion", "optimism", "recovery", "wins", "win",
}
_NEGATIVE = {
    "miss", "misses", "plunge", "plunges", "crash", "crashes", "loss", "losses",
    "downgrade", "bearish", "fall", "falls", "drop", "drops", "slump", "fear",
    "fears", "selloff", "weak", "cut", "cuts", "lawsuit", "ban", "bans", "hack",
    "hacked", "fraud", "recession", "default", "warning", "decline", "declines",
    "layoffs", "probe", "sanction", "sanctions",
}


class LexiconSentimentPredictor(Predictor):
    """Classic news-sentiment classifier -> direction (PRD §7.4).

    Nets positive vs. negative lexicon hits across admissible headlines. Isolates
    whether the LLM adds value over off-the-shelf sentiment.
    """

    model_id = "baseline_sentiment"

    def predict(self, context: PredictionContext):
        pos = neg = 0
        for item in context.news:
            text = f"{item.headline} {item.body}".lower()
            tokens = set(_tokenize(text))
            pos += len(tokens & _POSITIVE)
            neg += len(tokens & _NEGATIVE)
        net = pos - neg
        total = pos + neg
        if total == 0:
            label, conf = STAY, 0.34
        elif net > 0:
            label, conf = UP, 0.5 + 0.5 * net / total
        elif net < 0:
            label, conf = DOWN, 0.5 + 0.5 * (-net) / total
        else:
            label, conf = STAY, 0.4
        return prediction_from_label(label, context, self.model_id,
                                     confidence=min(conf, 0.95),
                                     rationale=f"lexicon sentiment net={net} (+{pos}/-{neg})")


def _tokenize(text: str) -> list[str]:
    return [t.strip(".,!?;:'\"()[]") for t in text.split()]


def estimate_class_freq(labels: pd.Series) -> dict[str, float]:
    """Class frequencies over a labeled window, for the stratified baseline."""
    counts = labels.dropna().value_counts()
    total = int(counts.sum())
    if total == 0:
        return {UP: 1 / 3, STAY: 1 / 3, DOWN: 1 / 3}
    return {c: int(counts.get(c, 0)) / total for c in LABELS}
