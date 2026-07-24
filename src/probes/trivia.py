"""Future-event trivia probe (PRD §7.3).

Directly ask the model to *recall* the actual outcome for a date in the test
period — no news given. If it can name the realized direction better than a
naive baseline, it already knows the test period from training, and any apparent
forecasting skill on those dates is suspect (contamination). We discount / flag
overlapping periods accordingly.

This is the most direct memorization check: it measures what the model knows,
not what it can reason.
"""

from __future__ import annotations

from src.labeling import LABELS

_SYSTEM = (
    "You are a finance historian answering from memory. If you genuinely recall "
    "the actual market outcome for the stated date, answer it. If you do not know, "
    "answer UNKNOWN — do not guess or reason from priors."
)


def build_trivia_prompt(asset: str, as_of_iso: str, horizon: str, theta_pct: str) -> tuple[str, str]:
    """A prompt asking the model to recall the realized direction (memorization test)."""
    user = (
        f"Asset: {asset}\n"
        f"From your training knowledge, what was {asset}'s ACTUAL close-to-close move "
        f"over the {horizon} period beginning {as_of_iso}? "
        f"UP if it rose more than {theta_pct}, DOWN if it fell more than {theta_pct}, "
        f"STAY if roughly flat.\n\n"
        'Respond with ONLY this JSON: {"recall":"UP|DOWN|STAY|UNKNOWN",'
        '"confidence":<0..1>}'
    )
    return _SYSTEM, user


def score_trivia(recalled: str, realized_label: str) -> dict:
    """Compare a recalled answer to the truth. UNKNOWN is neither right nor wrong."""
    r = (recalled or "").strip().upper()
    if r not in LABELS:  # UNKNOWN / unparseable
        return {"answered": False, "correct": None}
    return {"answered": True, "correct": r == realized_label}
