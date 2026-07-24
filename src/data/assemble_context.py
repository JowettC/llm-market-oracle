"""The point-in-time gate — the ONLY way news reaches a predictor (PRD §6.3).

This is the core of the whole fairness design. Every prediction is built from a
``PredictionContext`` produced here, and this module centrally enforces the one
rule that separates this study from "ChatGPT beats the market" posts:

    only news with  published_at < as_of  is admissible.

Nothing dated at or after the decision time can enter a prediction. Every
context records the exact ``news_ids`` and ``price_as_of`` it exposed, so any
prediction is auditable for leakage after the fact (PRD §7.1).

The strict ``<`` (not ``<=``) is deliberate: a headline stamped at the exact
decision instant is treated as not-yet-available, the conservative choice.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.data.market_providers import MarketDataProvider
from src.data.news_providers import NewsDataProvider, NewsItem


@dataclass(frozen=True)
class PredictionContext:
    """Everything a predictor is allowed to see for one decision.

    This object is the audit trail: ``news_ids`` and ``price_as_of`` prove
    exactly what was (and was not) visible at ``as_of``.
    """

    asset: str
    horizon: str
    as_of: pd.Timestamp
    news: list[NewsItem]
    price_history: pd.DataFrame | None = None  # only when condition == news_plus_price
    condition: str = "news_only"
    max_news: int | None = None
    theta: float | None = None  # neutral-band half-width at this bar (for prompts)
    mask_dates: bool = False    # date-masking probe: hide explicit dates (PRD §7.3)

    @property
    def news_ids(self) -> list[str]:
        return [n.news_id for n in self.news]

    @property
    def price_as_of(self) -> pd.Timestamp | None:
        if self.price_history is None or self.price_history.empty:
            return None
        return self.price_history.index[-1]

    def news_block(self) -> str:
        """Render admissible news for a prompt (newest first)."""
        lines = []
        for n in self.news:
            ts = n.published_at.strftime("%Y-%m-%d %H:%M UTC")
            text = n.headline if not n.body else f"{n.headline} — {n.body}"
            lines.append(f"[{ts}] {text}")
        return "\n".join(lines)


def assemble_context(
    as_of: pd.Timestamp | str,
    asset: str,
    horizon: str,
    news_provider: NewsDataProvider,
    market_provider: MarketDataProvider | None = None,
    condition: str = "news_only",
    max_news: int | None = None,
    price_lookback: int = 60,
) -> PredictionContext:
    """Build the point-in-time context for one prediction.

    Args:
        as_of: decision timestamp; only news with ``published_at < as_of`` is used.
        asset, horizon: what is being predicted.
        news_provider: source of candidate news items.
        market_provider: required iff ``condition == 'news_plus_price'``.
        condition: 'news_only' or 'news_plus_price' (PRD §5.6).
        max_news: keep at most this many most-recent admissible items (None = all).
        price_lookback: number of trailing bars of price context to expose.

    Returns:
        A ``PredictionContext`` containing ONLY admissible inputs.
    """
    as_of = _to_utc(as_of)

    # --- THE GATE: strict point-in-time filter, enforced in exactly one place ---
    candidates = news_provider.get_items(asset)
    admissible = [n for n in candidates if n.published_at < as_of]
    admissible.sort(key=lambda n: n.published_at, reverse=True)  # newest first
    if max_news is not None:
        admissible = admissible[:max_news]

    price_history = None
    if condition == "news_plus_price":
        if market_provider is None:
            raise ValueError("condition 'news_plus_price' requires a market_provider")
        ohlcv = market_provider.get_ohlcv(asset)
        price_history = ohlcv.loc[ohlcv.index < as_of].tail(price_lookback)
    elif condition != "news_only":
        raise ValueError(f"unknown condition: {condition!r}")

    return PredictionContext(
        asset=asset,
        horizon=horizon,
        as_of=as_of,
        news=admissible,
        price_history=price_history,
        condition=condition,
        max_news=max_news,
    )


def _to_utc(ts: pd.Timestamp | str) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
