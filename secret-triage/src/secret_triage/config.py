"""Carga de configuracion YAML."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml


def default_config_text() -> str:
    """Lee la config por defecto empaquetada con el wheel (TestPyPI / pip)."""
    return resources.files("secret_triage").joinpath("default.yaml").read_text(encoding="utf-8")


def load_config(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        return yaml.safe_load(default_config_text())
    if not path.is_file():
        raise FileNotFoundError(f"Config no encontrada: {path}")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def find_config(start: Path | None = None) -> Path | None:
    """Busca secret-triage.yaml hacia arriba desde cwd; None = config empaquetada."""
    cwd = start or Path.cwd()
    for directory in [cwd, *cwd.parents]:
        candidate = directory / "secret-triage.yaml"
        if candidate.is_file():
            return candidate
    return None
