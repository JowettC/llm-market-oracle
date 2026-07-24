"""LLM predictor — prompt → cache → Claude → validated Prediction (PRD §5.4, §9).

Slots into the exact same ``Predictor`` interface the baselines use, so the
walk-forward engine and scoring treat it identically. Determinism and quota
preservation come from the response cache (§13.2); usage-limit replies trigger
retry-with-backoff (§13.3).
"""

from __future__ import annotations

import json
import re
import time

from src.data.assemble_context import PredictionContext
from src.predictors.base import Prediction, Predictor, prediction_from_label
from src.predictors.llm_client import LLMClient, LLMUsageLimitError
from src.predictors.prompts import render
from src.predictors.response_cache import ResponseCache
from src.labeling import DOWN, LABELS, STAY, UP

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMPredictor(Predictor):
    def __init__(
        self,
        client: LLMClient,
        model_string: str,
        prompt_id: str = "P0",
        cache: ResponseCache | None = None,
        model_id: str | None = None,
        max_retries: int = 5,
        backoff_seconds: list[int] | None = None,
    ):
        self.client = client
        self.model_string = model_string
        self.prompt_id = prompt_id
        self.cache = cache or ResponseCache()
        self.model_id = model_id or f"llm:{model_string}:{prompt_id}"
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds or [5, 15, 45, 120, 300]

    # -- prompt / cache helpers (used by the dry-run estimator too) --
    def render(self, context: PredictionContext) -> tuple[str, str]:
        return render(self.prompt_id, context)

    def cache_key(self, context: PredictionContext) -> str:
        system, user = self.render(context)
        return self.cache.key(self.model_string, system, user, context.news_ids)

    def is_cached(self, context: PredictionContext) -> bool:
        return self.cache.has(self.cache_key(context))

    # -- the Predictor contract --
    def predict(self, context: PredictionContext) -> Prediction:
        system, user = self.render(context)
        key = self.cache.key(self.model_string, system, user, context.news_ids)
        text = self.cache.get(key)
        if text is None:
            text = self._call_with_backoff(system, user)
            self.cache.put(key, text, meta={"model": self.model_string, "prompt": self.prompt_id})
        return self._to_prediction(text, context)

    def _call_with_backoff(self, system: str, user: str) -> str:
        last: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.client.complete(system, user, self.model_string).text
            except LLMUsageLimitError as e:
                last = e
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds[min(attempt, len(self.backoff_seconds) - 1)])
        raise LLMUsageLimitError(f"usage limit persisted after {self.max_retries} retries: {last}")

    def _to_prediction(self, text: str, context: PredictionContext) -> Prediction:
        parsed = parse_model_json(text)
        label = _coerce_label(parsed.get("prediction"))
        probs = _coerce_probs(parsed)
        confidence = _num(parsed.get("confidence"))
        rationale = str(parsed.get("rationale", ""))[:300]

        if label is None and probs is not None:
            label = max(probs, key=probs.__getitem__)  # fall back to argmax
        if label is None:
            label = STAY  # last-resort neutral rather than crash

        # If the model gave a consistent distribution, use it; else rebuild a
        # valid one around the stated label (schema requires argmax == label).
        if probs is not None and max(probs, key=probs.__getitem__) == label:
            conf = confidence if confidence is not None else probs[label]
            try:
                return Prediction(
                    asset=context.asset, horizon=context.horizon,
                    as_of=context.as_of.isoformat(), prediction=label,
                    confidence=min(max(conf, 0.0), 1.0),
                    prob_up=probs[UP], prob_stay=probs[STAY], prob_down=probs[DOWN],
                    rationale=rationale, model=self.model_id, news_ids=context.news_ids,
                )
            except Exception:  # noqa: BLE001 — fall through to reconstruction
                pass
        conf = confidence if confidence is not None else (probs[label] if probs else 0.5)
        pred = prediction_from_label(label, context, self.model_id,
                                     confidence=conf if conf is not None else 0.5,
                                     rationale=rationale)
        return pred


def parse_model_json(text: str) -> dict:
    """Extract the JSON object from the model's text (tolerant of fences/prose)."""
    if not text:
        return {}
    t = text.strip()
    if "```" in t:  # strip code fences
        t = re.sub(r"```(?:json)?", "", t)
    m = _JSON_RE.search(t)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def _coerce_label(v) -> str | None:
    if not isinstance(v, str):
        return None
    v = v.strip().upper()
    return v if v in LABELS else None


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _coerce_probs(parsed: dict) -> dict[str, float] | None:
    up, stay, down = _num(parsed.get("prob_up")), _num(parsed.get("prob_stay")), _num(parsed.get("prob_down"))
    if None in (up, stay, down):
        return None
    total = up + stay + down
    if total <= 0:
        return None
    return {UP: up / total, STAY: stay / total, DOWN: down / total}
