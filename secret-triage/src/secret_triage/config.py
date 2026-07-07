"""Carga de configuracion YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "default.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG
    if not config_path.is_file():
        raise FileNotFoundError(f"Config no encontrada: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def find_config(start: Path | None = None) -> Path:
    """Busca secret-triage.yaml hacia arriba desde cwd."""
    cwd = start or Path.cwd()
    for directory in [cwd, *cwd.parents]:
        candidate = directory / "secret-triage.yaml"
        if candidate.is_file():
            return candidate
    return DEFAULT_CONFIG
