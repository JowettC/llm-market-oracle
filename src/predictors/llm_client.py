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
from dataclasses import dataclass


class LLMUsageLimitError(RuntimeError):
    """Raised when the subscription usage limit is hit (triggers backoff/resume)."""


@dataclass
class LLMResponse:
    text: str          # the model's raw text (expected to be our JSON contract)
    model: str = ""
    raw: dict | None = None


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
        return LLMResponse(text=str(envelope.get("result", "")), model=model_used, raw=envelope)


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
