"""Lectura y normalizacion de informes Gitleaks JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_gitleaks_report(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("El informe Gitleaks debe ser un array JSON")
    return [normalize_finding(item) for item in data]


def normalize_finding(raw: dict[str, Any]) -> dict[str, Any]:
    """Unifica campos entre versiones de Gitleaks."""
    file_path = raw.get("File") or raw.get("file") or ""
    line = raw.get("StartLine") or raw.get("line") or raw.get("StartLineNumber")
    return {
        "file": str(file_path).replace("\\", "/"),
        "line": int(line) if line is not None else 0,
        "rule_id": raw.get("RuleID") or raw.get("rule_id") or "",
        "match": raw.get("Match") or raw.get("match") or "",
        "secret": raw.get("Secret") or raw.get("secret") or "",
        "fingerprint": raw.get("Fingerprint") or raw.get("fingerprint") or "",
        "entropy": raw.get("Entropy") or raw.get("entropy"),
        "raw": raw,
    }
