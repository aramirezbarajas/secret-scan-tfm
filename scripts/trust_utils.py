"""Utilidades compartidas para integridad de datos (experimento P2)."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_fp_candidates(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} debe ser un array JSON")
    return data


def fingerprint(entry: dict[str, Any]) -> str:
    file_path = str(entry.get("file", "")).replace("\\", "/")
    line = entry.get("line", 0)
    return f"{file_path}:{line}"


def ground_truth_distribution(entries: list[dict[str, Any]]) -> dict[str, float]:
    counts = Counter(str(item.get("ground_truth") or "null") for item in entries)
    total = sum(counts.values()) or 1
    return {label: count / total for label, count in sorted(counts.items())}


def psi(expected: dict[str, float], actual: dict[str, float], epsilon: float = 1e-6) -> float:
    """Population Stability Index entre dos distribuciones categoricas."""
    labels = set(expected) | set(actual)
    score = 0.0
    for label in labels:
        exp_pct = expected.get(label, 0.0) or epsilon
        act_pct = actual.get(label, 0.0) or epsilon
        score += (act_pct - exp_pct) * __import__("math").log(act_pct / exp_pct)
    return score


def entry_subset_hash(entries: list[dict[str, Any]], keys: list[str]) -> str:
    """Hash estable de un subconjunto de campos por fila."""
    normalized = []
    for entry in entries:
        normalized.append({key: entry.get(key) for key in keys})
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
