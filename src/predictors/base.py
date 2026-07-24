"""Predictor interface + the shared prediction schema (PRD §5.4).

Every predictor — LLM or baseline — emits the SAME structured object so scoring
is uniform. The schema is validated with pydantic; ``prob_*`` fields enable
calibration (Brier) scoring and ``news_ids`` is the leakage audit trail.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, field_validator, model_validator

from src.data.assemble_context import PredictionContext
from src.labeling import LABELS


class Prediction(BaseModel):
    """One prediction, identical schema for LLMs and baselines (PRD §5.4)."""

    asset: str
    horizon: str
    as_of: str  # ISO-8601 UTC decision timestamp
    prediction: str  # UP | DOWN | STAY
    confidence: float = Field(ge=0.0, le=1.0)
    prob_up: float = Field(ge=0.0, le=1.0)
    prob_stay: float = Field(ge=0.0, le=1.0)
    prob_down: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    model: str = ""
    news_ids: list[str] = Field(default_factory=list)

    @field_validator("prediction")
    @classmethod
    def _valid_label(cls, v: str) -> str:
        if v not in LABELS:
            raise ValueError(f"prediction must be one of {LABELS}, got {v!r}")
        return v

    @model_validator(mode="after")
    def _probs_sum_to_one(self) -> "Prediction":
        total = self.prob_up + self.prob_stay + self.prob_down
        if abs(total - 1.0) > 1e-3:
            raise ValueError(f"prob_up+prob_stay+prob_down must sum to 1.0, got {total:.4f}")
        # the argmax class should match the stated prediction (guards silent bugs)
        probs = {"UP": self.prob_up, "STAY": self.prob_stay, "DOWN": self.prob_down}
        if max(probs, key=probs.__getitem__) != self.prediction:
            raise ValueError(
                f"prediction {self.prediction!r} disagrees with argmax of probs {probs}"
            )
        return self


class Predictor(ABC):
    """Provider-agnostic predictor. Any model slots in behind this (PRD §9)."""

    #: stable identifier written into every Prediction.model field
    model_id: str = "abstract"

    @abstractmethod
    def predict(self, context: PredictionContext) -> Prediction:
        """Produce a Prediction from an already-gated point-in-time context."""
        raise NotImplementedError


def prediction_from_label(
    label: str,
    context: PredictionContext,
    model_id: str,
    confidence: float = 0.5,
    rationale: str = "",
) -> Prediction:
    """Helper: build a valid Prediction for a hard-label predictor.

    Puts ``confidence`` mass on the chosen class and splits the remainder evenly
    across the other two, so ``prob_*`` are always well-formed for Brier scoring.

    ``confidence`` is floored at just above 1/3: with three classes that is the
    minimum share for the chosen class to remain the argmax, keeping the emitted
    distribution consistent with the label (a hard-label pick can't honestly
    claim less certainty than "the plurality class").
    """
    confidence = min(max(confidence, 1.0 / 3.0 + 1e-6), 1.0)
    other = max((1.0 - confidence) / 2.0, 0.0)
    probs = {"UP": other, "STAY": other, "DOWN": other}
    probs[label] = confidence
    total = sum(probs.values())
    probs = {k: v / total for k, v in probs.items()}  # renormalize defensively
    return Prediction(
        asset=context.asset,
        horizon=context.horizon,
        as_of=context.as_of.isoformat(),
        prediction=label,
        confidence=probs[label],
        prob_up=probs["UP"],
        prob_stay=probs["STAY"],
        prob_down=probs["DOWN"],
        rationale=rationale,
        model=model_id,
        news_ids=context.news_ids,
    )
