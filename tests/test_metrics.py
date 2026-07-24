"""Tests for scoring metrics (PRD §8.2, §10, Appendix B)."""

from __future__ import annotations

import numpy as np

from src.backtest import metrics as M
from src.labeling import DOWN, STAY, UP


def test_directional_accuracy():
    assert M.directional_accuracy([UP, DOWN, STAY], [UP, DOWN, UP]) == 2 / 3


def test_pt_detects_perfect_skill():
    # a predictor that nails up/down on a balanced series must be significant.
    pred = ([UP, DOWN] * 20)
    actual = ([UP, DOWN] * 20)
    res = M.pesaran_timmermann(pred, actual)
    assert res.hit_rate == 1.0
    assert res.p_value < 0.01


def test_pt_no_skill_is_insignificant():
    rng = np.random.default_rng(0)
    labels = [UP, DOWN]
    actual = [labels[i] for i in rng.integers(0, 2, 200)]
    pred = [labels[i] for i in rng.integers(0, 2, 200)]  # independent of actual
    res = M.pesaran_timmermann(pred, actual)
    assert res.p_value > 0.05


def test_pt_degenerate_constant_forecast():
    # always-UP never commits to DOWN -> degenerate; must not crash, returns nan.
    res = M.pesaran_timmermann([UP] * 50, ([UP, DOWN] * 25))
    assert np.isnan(res.statistic)


def test_brier_perfect_and_worst():
    perfect = [{"UP": 1.0, "STAY": 0.0, "DOWN": 0.0}]
    assert M.brier_score(perfect, [UP]) == 0.0
    worst = [{"UP": 0.0, "STAY": 0.0, "DOWN": 1.0}]
    assert abs(M.brier_score(worst, [UP]) - 2.0) < 1e-9


def test_diebold_mariano_prefers_better_model():
    # A is wrong more often than B, but with variation so the loss differential
    # has non-zero variance (a constant differential leaves DM undefined).
    rng = np.random.default_rng(3)
    loss_a = rng.binomial(1, 0.7, 120).astype(float)  # ~70% error rate
    loss_b = rng.binomial(1, 0.2, 120).astype(float)  # ~20% error rate
    stat, p = M.diebold_mariano(loss_a, loss_b)
    assert stat > 0        # A has higher loss (worse) than B
    assert p < 0.05        # and significantly so


def test_diebold_mariano_constant_diff_is_undefined():
    # zero-variance loss differential -> DM undefined, must return nan not crash.
    stat, p = M.diebold_mariano([1.0] * 40, [0.0] * 40)
    assert np.isnan(stat) and np.isnan(p)


def test_sharpe_and_sortino_signs():
    up = np.full(60, 0.01)
    down_mix = np.array([0.02, -0.03] * 30)
    assert M.sharpe(up, 252) > 0
    assert np.isnan(M.sharpe(np.zeros(10), 252))  # zero variance
    assert M.sortino(down_mix, 252) is not None


def test_max_drawdown_known_curve():
    eq = np.array([1.0, 1.2, 0.9, 1.1])  # peak 1.2 -> trough 0.9 = -25%
    assert abs(M.max_drawdown(eq) - (0.9 / 1.2 - 1.0)) < 1e-9


def test_cagr_doubling_in_one_year():
    eq = np.concatenate([np.linspace(1.0, 2.0, 253)])  # ~1 year daily, doubles
    assert abs(M.cagr(eq, 252) - 1.0) < 0.05


def test_newey_west_var_positive():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 100)
    v = M._newey_west_var(x, maxlags=4)
    assert v > 0
