"""Scoring metrics for both evaluation lenses (PRD §8.2, §10, Appendix B).

Statistical-skill lens: directional accuracy, confusion matrix / per-class F1,
Brier score, the Pesaran-Timmermann market-timing test, and the Diebold-Mariano
test for comparing two forecasters.

Economic lens helpers: Sharpe, Sortino, max drawdown, CAGR.

Overlapping horizons (weekly/monthly) induce autocorrelation, so mean-based
significance uses a Newey-West/HAC variance (PRD §8.3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from src.labeling import DOWN, LABELS, STAY, UP


# --------------------------------------------------------------------------- #
# Classification metrics
# --------------------------------------------------------------------------- #
def directional_accuracy(pred: list[str], actual: list[str]) -> float:
    """Fraction of exactly-correct 3-class labels."""
    pairs = [(p, a) for p, a in zip(pred, actual) if p is not None and a is not None]
    if not pairs:
        return float("nan")
    return sum(p == a for p, a in pairs) / len(pairs)


def confusion_matrix(pred: list[str], actual: list[str]) -> dict[str, dict[str, int]]:
    """actual (rows) x predicted (cols) counts over the 3 classes."""
    m = {a: {p: 0 for p in LABELS} for a in LABELS}
    for p, a in zip(pred, actual):
        if p in LABELS and a in LABELS:
            m[a][p] += 1
    return m


def per_class_f1(pred: list[str], actual: list[str]) -> dict[str, dict[str, float]]:
    """Precision / recall / F1 per class."""
    cm = confusion_matrix(pred, actual)
    out: dict[str, dict[str, float]] = {}
    for c in LABELS:
        tp = cm[c][c]
        fp = sum(cm[a][c] for a in LABELS if a != c)
        fn = sum(cm[c][p] for p in LABELS if p != c)
        prec = tp / (tp + fp) if (tp + fp) else float("nan")
        rec = tp / (tp + fn) if (tp + fn) else float("nan")
        f1 = (2 * prec * rec / (prec + rec)) if (prec and rec and not np.isnan(prec) and not np.isnan(rec) and (prec + rec)) else float("nan")
        out[c] = {"precision": prec, "recall": rec, "f1": f1}
    return out


def brier_score(prob_rows: list[dict[str, float]], actual: list[str]) -> float:
    """Multi-class Brier score: mean Σ_c (p_c - y_c)^2. Lower = better (PRD §10.3)."""
    total, n = 0.0, 0
    for probs, a in zip(prob_rows, actual):
        if a not in LABELS:
            continue
        for c in LABELS:
            y = 1.0 if c == a else 0.0
            total += (probs.get(c, 0.0) - y) ** 2
        n += 1
    return total / n if n else float("nan")


# --------------------------------------------------------------------------- #
# Pesaran-Timmermann market-timing test (1992) — PRD §3.5, Appendix B
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PTResult:
    statistic: float
    p_value: float          # one-sided (H1: genuine timing skill)
    n: int
    hit_rate: float         # proportion of correct up/down calls used
    note: str = ""


def pesaran_timmermann(pred: list[str], actual: list[str]) -> PTResult:
    """Test H0: predicted and realized directions are independent (no skill).

    Reduced to the binary up/down problem: rows where the model commits to a
    direction (UP or DOWN) and the outcome is directional (UP or DOWN). STAY on
    either side is excluded and reported via the confusion matrix instead. This
    is the standard, defensible reduction for a 3-class labeler.
    """
    yhat, y = [], []
    for p, a in zip(pred, actual):
        if p in (UP, DOWN) and a in (UP, DOWN):
            yhat.append(1 if p == UP else 0)
            y.append(1 if a == UP else 0)
    n = len(y)
    if n < 10:
        return PTResult(float("nan"), float("nan"), n, float("nan"),
                        "too few directional obs for PT")
    yhat = np.array(yhat)
    y = np.array(y)

    py = y.mean()          # P(actual up)
    px = yhat.mean()       # P(predicted up)
    hit = float((yhat == y).mean())            # P̂: correct-direction rate
    p_star = py * px + (1 - py) * (1 - px)     # under independence

    var_phat = p_star * (1 - p_star) / n
    var_pstar = (
        ((2 * py - 1) ** 2) * px * (1 - px) / n
        + ((2 * px - 1) ** 2) * py * (1 - py) / n
        + 4 * py * px * (1 - py) * (1 - px) / (n ** 2)
    )
    denom = var_phat - var_pstar
    if denom <= 0:
        return PTResult(float("nan"), float("nan"), n, hit,
                        "degenerate variance (constant forecast/outcome)")
    stat = (hit - p_star) / np.sqrt(denom)
    p_value = float(stats.norm.sf(stat))       # one-sided: skill => stat > 0
    return PTResult(float(stat), p_value, n, hit)


# --------------------------------------------------------------------------- #
# Diebold-Mariano test (1995) — compare two forecasters (PRD §3.5, Appendix B)
# --------------------------------------------------------------------------- #
def _newey_west_var(x: np.ndarray, maxlags: int | None) -> float:
    """HAC (Newey-West) long-run variance of the mean of ``x`` (PRD §8.3)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    xc = x - x.mean()
    if maxlags is None:
        maxlags = int(np.floor(4 * (n / 100) ** (2 / 9)))  # Newey-West rule of thumb
    gamma0 = np.dot(xc, xc) / n
    var = gamma0
    for lag in range(1, maxlags + 1):
        w = 1.0 - lag / (maxlags + 1)  # Bartlett kernel
        cov = np.dot(xc[lag:], xc[:-lag]) / n
        var += 2 * w * cov
    return var / n  # variance of the mean


def diebold_mariano(
    loss_a: list[float], loss_b: list[float], maxlags: int | None = None
) -> tuple[float, float]:
    """DM test of equal predictive accuracy. Returns (statistic, two-sided p).

    ``loss_*`` are per-observation losses (e.g. 0/1 misclassification or Brier).
    Positive statistic => model A has higher loss (worse) than model B.
    """
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    n = len(d)
    if n < 8 or np.allclose(d, 0):
        return float("nan"), float("nan")
    var_mean = _newey_west_var(d, maxlags)
    if var_mean <= 0:
        return float("nan"), float("nan")
    stat = d.mean() / np.sqrt(var_mean)
    p_value = float(2 * stats.norm.sf(abs(stat)))
    return float(stat), p_value


def zero_one_loss(pred: list[str], actual: list[str]) -> list[float]:
    """Per-obs misclassification loss (1 wrong, 0 right); None outcomes -> skipped upstream."""
    return [0.0 if p == a else 1.0 for p, a in zip(pred, actual)]


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR-adjusted q-values (PRD §7.6).

    Controls the false-discovery rate across the many asset×horizon×model cells,
    so a lone lucky p-value (e.g. a random baseline at p≈0.007 among 21 cells)
    does not read as a real discovery. NaN inputs pass through as NaN and are
    excluded from the correction's denominator.
    """
    idx = [i for i, p in enumerate(pvalues) if p is not None and not (isinstance(p, float) and np.isnan(p))]
    m = len(idx)
    q = [float("nan")] * len(pvalues)
    if m == 0:
        return q
    order = sorted(idx, key=lambda i: pvalues[i])
    prev = 1.0
    for rank in range(m, 0, -1):           # walk from largest p to smallest
        i = order[rank - 1]
        adj = pvalues[i] * m / rank
        prev = min(prev, adj)              # enforce monotonic non-decreasing q
        q[i] = min(prev, 1.0)
    return q


# --------------------------------------------------------------------------- #
# Economic metrics (PRD §10.2, Appendix B)
# --------------------------------------------------------------------------- #
def sharpe(returns: np.ndarray, periods_per_year: int, rf: float = 0.0) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 2:
        return float("nan")
    excess = r - rf / periods_per_year
    sd = excess.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(excess.mean() / sd * np.sqrt(periods_per_year))


def sortino(returns: np.ndarray, periods_per_year: int, rf: float = 0.0) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 2:
        return float("nan")
    excess = r - rf / periods_per_year
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float("inf")
    dd = np.sqrt((downside ** 2).mean())
    if dd == 0:
        return float("nan")
    return float(excess.mean() / dd * np.sqrt(periods_per_year))


def max_drawdown(equity_curve: np.ndarray) -> float:
    """Largest peak-to-trough decline as a negative fraction (e.g. -0.23)."""
    eq = np.asarray(equity_curve, dtype=float)
    if len(eq) == 0:
        return float("nan")
    running_max = np.maximum.accumulate(eq)
    drawdown = eq / running_max - 1.0
    return float(drawdown.min())


def cagr(equity_curve: np.ndarray, periods_per_year: int) -> float:
    eq = np.asarray(equity_curve, dtype=float)
    if len(eq) < 2 or eq[0] <= 0:
        return float("nan")
    total_return = eq[-1] / eq[0]
    years = (len(eq) - 1) / periods_per_year
    if years <= 0:
        return float("nan")
    return float(total_return ** (1 / years) - 1)
