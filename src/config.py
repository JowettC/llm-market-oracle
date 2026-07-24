"""Config loader — the single source of truth for every experiment knob.

Loads ``config/experiment.yaml`` (PRD §12.2) into a lightweight, attribute-free
dict-backed object. We keep it a plain dict on purpose: the config is data, and
every consumer reads it explicitly so there is no hidden defaulting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "experiment.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and lightly validate the experiment config."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"config not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    _require(cfg, ["seed", "assets", "horizons", "label_band", "models", "windows"])
    for asset in cfg["assets"]:
        _require(asset, ["id", "kind"], ctx=f"asset {asset.get('id', '?')}")
    return cfg


def asset_ids(cfg: dict[str, Any]) -> list[str]:
    return [a["id"] for a in cfg["assets"]]


def asset_by_id(cfg: dict[str, Any], asset_id: str) -> dict[str, Any]:
    for a in cfg["assets"]:
        if a["id"] == asset_id:
            return a
    raise KeyError(f"unknown asset: {asset_id}")


def _require(d: dict[str, Any], keys: list[str], ctx: str = "config") -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"{ctx} missing required keys: {missing}")
