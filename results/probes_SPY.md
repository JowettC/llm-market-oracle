# Lookahead / memorization probes — SPY·daily

Model `claude-opus-4-8`, prompt `P0`, 40 samples from the clean window. See PRD §7.3.

### date_masking

- n = 40
- acc_normal: 0.2
- acc_masked: 0.375
- drop: -0.175

**Interpretation:** no material accuracy drop when dates are hidden — skill is not explained by date recognition.

### placebo_news

- n = 40
- acc_real: 0.2
- acc_placebo: 0.325
- change_rate: 0.35

**Interpretation:** predictions change on mismatched news (change_rate=35%) and placebo accuracy drops toward chance — consistent with genuine news use.

### future_trivia

- n = 40
- answer_rate: 0.0
- recall_accuracy: 0.0
- answered: 0

**Interpretation:** low/uninformative recall (rate=0.00, answered=0%) — little evidence the model has memorized these outcomes.
