"""Pre-registered prompt templates P0–P3 (PRD §5.5, Appendix A).

A small, FROZEN set — not an open-ended search — so we don't prompt-overfit.
Each template renders a (system, user) pair from a point-in-time PredictionContext.
The user block always ends with the strict JSON response contract so every
model's output parses uniformly into the shared Prediction schema (§5.4).

All templates emphasize: use ONLY the provided news, assume no knowledge of
events after the cutoff.
"""

from __future__ import annotations

from src.data.assemble_context import PredictionContext

RESPONSE_CONTRACT = (
    'Respond with ONLY this JSON and nothing else:\n'
    '{"prediction":"UP|DOWN|STAY","prob_up":<0..1>,"prob_stay":<0..1>,'
    '"prob_down":<0..1>,"confidence":<0..1>,"rationale":"<=40 words"}\n'
    "prob_up+prob_stay+prob_down must sum to 1. confidence is your probability "
    "for the chosen class. Choose STAY if the move is likely within the flat band."
)

_SYSTEM_BASE = (
    "You are a disciplined financial analyst. You only use the information "
    "provided. You never assume knowledge of events after the stated cutoff. "
    "You do not hedge into vague answers — you commit to a directional call."
)


def _theta_pct(context: PredictionContext) -> str:
    if context.theta is None:
        return "a small asset-specific band"
    return f"±{context.theta * 100:.2f}%"


def _price_block(context: PredictionContext) -> str:
    """Compact trailing price context, only under the news+price condition."""
    if context.condition != "news_plus_price" or context.price_history is None:
        return ""
    ph = context.price_history.tail(10)
    rows = [f"  {ts.date()}: close {row.close:.2f}" for ts, row in ph.iterrows()]
    return "\nRecent closes (most recent last):\n" + "\n".join(rows) + "\n"


def _header(context: PredictionContext) -> str:
    return (
        f"Asset: {context.asset}\n"
        f"Decision time (cutoff): {context.as_of.isoformat()}\n"
        f"Horizon: over the next {context.horizon}, will the CLOSE be higher, lower, "
        f"or roughly flat (within {_theta_pct(context)}) versus now?"
    )


def _news_section(context: PredictionContext, limit: int = 60) -> str:
    if not context.news:
        return "--- NEWS ---\n(no admissible news before the cutoff)\n------------"
    block = context.news_block()
    lines = block.split("\n")[:limit]
    return "--- NEWS (all published on or before the cutoff) ---\n" + "\n".join(lines) + "\n------------"


def render_p0(context: PredictionContext) -> tuple[str, str]:
    """P0 — zero-shot direct (Lopez-Lira style)."""
    user = (
        f"{_header(context)}\n{_price_block(context)}\n"
        f"{_news_section(context)}\n\n{RESPONSE_CONTRACT}"
    )
    return _SYSTEM_BASE, user


def render_p1(context: PredictionContext) -> tuple[str, str]:
    """P1 — chain-of-thought: reason step by step, then the final JSON."""
    system = _SYSTEM_BASE + (
        " Think step by step about the news' likely market impact BEFORE deciding, "
        "but your visible output must be ONLY the final JSON."
    )
    user = (
        f"{_header(context)}\n{_price_block(context)}\n"
        f"{_news_section(context)}\n\n"
        "Reason internally about macro backdrop, sentiment, and positioning, then "
        f"commit.\n\n{RESPONSE_CONTRACT}"
    )
    return system, user


def render_p2(context: PredictionContext) -> tuple[str, str]:
    """P2 — structured/analyst: a light template to fill before deciding."""
    user = (
        f"{_header(context)}\n{_price_block(context)}\n"
        f"{_news_section(context)}\n\n"
        "Consider, briefly and internally: (a) macro backdrop, (b) sector/asset-specific "
        "drivers, (c) net news sentiment, (d) positioning/flow. Weigh them, then commit.\n\n"
        f"{RESPONSE_CONTRACT}"
    )
    return _SYSTEM_BASE, user


def render_p3(context: PredictionContext) -> tuple[str, str]:
    """P3 — sentiment-only ablation: headline tone only, no reasoning."""
    system = (
        "You are a fast news-sentiment classifier. Judge ONLY the aggregate tone of "
        "the headlines for the asset's next-period direction. Do not reason about "
        "macro or fundamentals. Use only the provided headlines."
    )
    user = (
        f"{_header(context)}\n\n{_news_section(context)}\n\n"
        f"Base your call purely on headline sentiment.\n\n{RESPONSE_CONTRACT}"
    )
    return system, user


PROMPTS = {"P0": render_p0, "P1": render_p1, "P2": render_p2, "P3": render_p3}


def render(prompt_id: str, context: PredictionContext) -> tuple[str, str]:
    try:
        return PROMPTS[prompt_id](context)
    except KeyError as exc:
        raise ValueError(f"unknown prompt id {prompt_id!r}; valid: {list(PROMPTS)}") from exc
