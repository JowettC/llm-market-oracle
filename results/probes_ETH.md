# Lookahead / memorization probes — ETH·daily

Model `claude-opus-4-8`, prompt `P0`, 40 samples from the clean window. See PRD §7.3.

### date_masking

- n = 40
- acc_normal: 0.3
- acc_masked: 0.4
- drop: -0.10000000000000003

**Interpretation:** no material accuracy drop when dates are hidden — skill is not explained by date recognition.

### placebo_news

- n = 40
- acc_real: 0.3
- acc_placebo: 0.275
- change_rate: 0.45

**Interpretation:** predictions change on mismatched news (change_rate=45%) and placebo accuracy drops toward chance — consistent with genuine news use.

### future_trivia

- n = 40
- answer_rate: 0.0
- recall_accuracy: 0.0
- answered: 0

**Interpretation:** low/uninformative recall (rate=0.00, answered=0%) — little evidence the model has memorized these outcomes.
