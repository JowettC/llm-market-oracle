"""LLM clients behind one interface (PRD §13.4).

The Claude client drives the **Claude Max subscription** via Claude Code headless
mode — `claude -p ... --output-format json` as a subprocess — so there is **no
API key** and no per-token billing; usage draws from the subscription's limits.

A MockLLMClient with scripted responses lets the whole harness (prompting,
caching, parsing, walk-forward) be tested offline and deterministically, with
zero subscription usage.
"""

from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


class LLMUsageLimitError(RuntimeError):
    """Raised when the subscription usage limit is hit (triggers backoff/resume)."""


class BudgetExceededError(RuntimeError):
    """Raised when a self-imposed usage budget (calls or $) would be exceeded.

    We cannot query remaining subscription quota (no CLI/API exposes it), so this
    is a *client-side* ceiling: we count what we spend and stop before a target
    the user sets (e.g. 90% of what tripped the limit last time)."""


@dataclass
class UsageBudget:
    """A local spend meter. ``max_calls`` / ``max_cost_usd`` are hard ceilings on
    NEW (uncached) Claude calls; either or both may be set (None = unlimited).

    WINDOW-AWARE: if ``state_file`` is given, the call count is loaded from and
    persisted to that file, so the ceiling holds across process restarts *within
    one rolling-limit window* (the subscription limit is per rolling window, not
    per run). The driver clears the file after each 5h wait to start a fresh
    window. Without a state_file the meter is per-process only.
    """

    max_calls: int | None = None
    max_cost_usd: float | None = None
    calls: int = 0
    cost_usd: float = 0.0
    state_file: str | None = None

    def __post_init__(self) -> None:
        if self.state_file and Path(self.state_file).exists():
            try:
                self.calls = int(Path(self.state_file).read_text().strip() or 0)
            except (ValueError, OSError):
                self.calls = 0

    def check(self) -> None:
        """Raise if making one more call would cross a ceiling."""
        if self.max_calls is not None and self.calls >= self.max_calls:
            raise BudgetExceededError(
                f"call budget reached: {self.calls}/{self.max_calls} calls this window")
        if self.max_cost_usd is not None and self.cost_usd >= self.max_cost_usd:
            raise BudgetExceededError(
                f"cost budget reached: ${self.cost_usd:.2f}/${self.max_cost_usd:.2f}")

    def record(self, cost_usd: float) -> None:
        self.calls += 1
        self.cost_usd += float(cost_usd or 0.0)
        if self.state_file:
            try:
                Path(self.state_file).write_text(str(self.calls))
            except OSError:
                pass


@dataclass
class LLMResponse:
    text: str          # the model's raw text (expected to be our JSON contract)
    model: str = ""
    raw: dict | None = None
    cost_usd: float = 0.0   # this call's API-equivalent cost, from the CLI envelope


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, model: str) -> LLMResponse:
        raise NotImplementedError


class ClaudeCLIClient(LLMClient):
    """Calls `claude -p` (subscription auth). No API key.

    Notes:
      * temperature is not exposed by the CLI; determinism is provided by the
        response cache keyed on (model, prompt, news_ids) (PRD §13.2).
      * a usage-limit reply surfaces as LLMUsageLimitError so the runner can
        back off and resume (PRD §13.3).
    """

    def __init__(self, binary: str = "claude", timeout_s: int = 180):
        self.binary = binary
        self.timeout_s = timeout_s

    def complete(self, system: str, user: str, model: str) -> LLMResponse:
        cmd = [
            self.binary, "-p", user,
            "--system-prompt", system,
            "--output-format", "json",
        ]
        if model:
            cmd += ["--model", model]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"claude CLI timed out after {self.timeout_s}s") from exc

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            if _looks_like_usage_limit(err):
                raise LLMUsageLimitError(err[:200])
            raise RuntimeError(f"claude CLI failed (rc={proc.returncode}): {err[:200]}")

        envelope = _parse_envelope(proc.stdout)
        if envelope.get("is_error"):
            msg = str(envelope.get("result") or envelope.get("api_error_status") or "")
            if _looks_like_usage_limit(msg):
                raise LLMUsageLimitError(msg[:200])
            raise RuntimeError(f"claude returned is_error: {msg[:200]}")
        model_used = next(iter(envelope.get("modelUsage", {})), model)
        return LLMResponse(text=str(envelope.get("result", "")), model=model_used,
                           raw=envelope, cost_usd=float(envelope.get("total_cost_usd", 0.0) or 0.0))


class MockLLMClient(LLMClient):
    """Deterministic offline client. Either a fixed response, a callable, or a
    per-call scripted list — for tests and dry demonstrations (no usage)."""

    def __init__(self, response="", *, script=None, fn=None):
        self.response = response
        self.script = list(script) if script else None
        self.fn = fn
        self.calls: list[tuple[str, str, str]] = []

    def complete(self, system: str, user: str, model: str) -> LLMResponse:
        self.calls.append((system, user, model))
        if self.fn is not None:
            text = self.fn(system, user, model)
        elif self.script is not None:
            text = self.script[(len(self.calls) - 1) % len(self.script)]
        else:
            text = self.response
        return LLMResponse(text=text, model=model or "mock")


def _parse_envelope(stdout: str) -> dict:
    stdout = (stdout or "").strip()
    if not stdout:
        raise RuntimeError("claude CLI returned empty output")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"claude CLI non-JSON output: {stdout[:160]}") from exc


def _looks_like_usage_limit(msg: str) -> bool:
    m = (msg or "").lower()
    return any(s in m for s in ("usage limit", "rate limit", "429", "quota", "limit reached"))
