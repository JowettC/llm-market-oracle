"""Run the three lookahead/memorization probes and interpret them (PRD §7.3).

Each probe returns a compact result with an explicit interpretation, so the
write-up can state plainly whether any LLM edge survives the memorization checks.
All probes are LLM-client-agnostic (a MockLLMClient drives them in tests).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import numpy as np

from src.backtest.metrics import directional_accuracy
from src.data.assemble_context import PredictionContext
from src.data.news_providers import NewsItem
from src.predictors.llm_predictor import LLMPredictor, parse_model_json
from src.probes.placebo import placebo_context
from src.probes.trivia import build_trivia_prompt, score_trivia


@dataclass
class ProbeResult:
    name: str
    n: int
    metrics: dict
    interpretation: str

    def summary(self) -> str:
        m = "  ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                       for k, v in self.metrics.items())
        return f"[{self.name}] n={self.n}  {m}\n   -> {self.interpretation}"


def run_masking_probe(predictor: LLMPredictor, samples: list[tuple[PredictionContext, str]],
                      drop_threshold: float = 0.10) -> ProbeResult:
    """Compare directional accuracy with vs. without explicit dates in the prompt."""
    labels = [lbl for _, lbl in samples]
    normal = [predictor.predict(ctx).prediction for ctx, _ in samples]
    masked = [predictor.predict(dataclasses.replace(ctx, mask_dates=True)).prediction
              for ctx, _ in samples]
    acc_n = directional_accuracy(normal, labels)
    acc_m = directional_accuracy(masked, labels)
    drop = acc_n - acc_m
    if drop >= drop_threshold:
        interp = (f"accuracy fell {drop:.1%} when dates were hidden — the model may be "
                  "keying on remembered dates (memorization tell). Investigate.")
    else:
        interp = ("no material accuracy drop when dates are hidden — skill is not "
                  "explained by date recognition.")
    return ProbeResult("date_masking", len(samples),
                       {"acc_normal": acc_n, "acc_masked": acc_m, "drop": drop}, interp)


def run_placebo_probe(predictor: LLMPredictor, samples: list[tuple[PredictionContext, str]],
                      pool: list[NewsItem], seed: int = 42) -> ProbeResult:
    """Compare real-news accuracy to mismatched-news accuracy; measure sensitivity."""
    rng = np.random.default_rng(seed)
    labels = [lbl for _, lbl in samples]
    real = [predictor.predict(ctx).prediction for ctx, _ in samples]
    placebo = [predictor.predict(placebo_context(ctx, pool, rng)).prediction
               for ctx, _ in samples]
    acc_real = directional_accuracy(real, labels)
    acc_plac = directional_accuracy(placebo, labels)
    change_rate = float(np.mean([r != p for r, p in zip(real, placebo)])) if real else 0.0
    if acc_plac >= acc_real - 0.02 and change_rate < 0.2:
        interp = ("mismatched news barely changes predictions and accuracy holds — the "
                  "model is largely ignoring the news content (skill, if any, is not from "
                  "reading it). Red flag for the news-driven claim.")
    else:
        interp = (f"predictions change on mismatched news (change_rate={change_rate:.0%}) and "
                  f"placebo accuracy drops toward chance — consistent with genuine news use.")
    return ProbeResult("placebo_news", len(samples),
                       {"acc_real": acc_real, "acc_placebo": acc_plac, "change_rate": change_rate},
                       interp)


def run_trivia_probe(client, model_string: str, cache, samples, theta_pct_fn,
                     baseline_rate: float = 0.5) -> ProbeResult:
    """Ask the model to recall real outcomes (no news); high recall => contamination."""
    answered = correct = 0
    for ctx, label in samples:
        system, user = build_trivia_prompt(
            ctx.asset, ctx.as_of.isoformat(), ctx.horizon, theta_pct_fn(ctx))
        key = cache.key(model_string + "::trivia", system, user, [])
        text = cache.get(key)
        if text is None:
            text = client.complete(system, user, model_string).text
            cache.put(key, text, meta={"probe": "trivia"})
        rec = parse_model_json(text).get("recall")
        s = score_trivia(rec, label)
        if s["answered"]:
            answered += 1
            correct += int(bool(s["correct"]))
    recall_rate = (correct / answered) if answered else 0.0
    answer_rate = (answered / len(samples)) if samples else 0.0
    if answered >= max(10, 0.3 * len(samples)) and recall_rate > baseline_rate + 0.15:
        interp = (f"the model recalled real outcomes {recall_rate:.0%} of the time it "
                  f"answered ({answer_rate:.0%} answer rate) — it knows this period; "
                  "treat forecasts on these dates as contaminated.")
    else:
        interp = (f"low/uninformative recall (rate={recall_rate:.2f}, answered={answer_rate:.0%}) "
                  "— little evidence the model has memorized these outcomes.")
    return ProbeResult("future_trivia", len(samples),
                       {"answer_rate": answer_rate, "recall_accuracy": recall_rate,
                        "answered": answered}, interp)
