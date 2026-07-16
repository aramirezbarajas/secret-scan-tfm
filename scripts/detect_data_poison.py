#!/usr/bin/env python3
"""
Detectores D1-D4 de envenenamiento sobre fp_candidates.json (experimento P2).

Detectores:
  D1_integrity_hash   — SHA-256 del fichero vs manifiesto
  D2_golden_subset    — hash del subconjunto golden vs manifiesto
  D3_count_drift      — recuento FP vs expected_fp_count
  D4_label_psi        — deriva PSI en ground_truth
  D5_synthetic_markers— filas con meta_ids negativos o rutas poison_demo (lab)

Uso:
  python scripts/build_trust_baseline.py
  python scripts/inject_data_poison.py --rate 0.05
  python scripts/detect_data_poison.py --fp results/fp_candidates_p02.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from trust_utils import (  # noqa: E402
    entry_subset_hash,
    fingerprint,
    ground_truth_distribution,
    load_fp_candidates,
    psi,
    sha256_file,
)

PSI_ALERT_THRESHOLD = 0.2


def load_baseline(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_d1(file_hash: str, baseline: dict[str, Any]) -> dict[str, Any]:
    expected = baseline.get("sha256_fp_file", "")
    ok = file_hash == expected
    return {
        "id": "D1_integrity_hash",
        "alert": not ok,
        "severity": "critical" if not ok else "ok",
        "detail": "Hash del fichero coincide con manifiesto" if ok else "Hash distinto al manifiesto",
        "expected": expected,
        "actual": file_hash,
    }


def detect_d2(entries: list[dict], baseline: dict[str, Any]) -> dict[str, Any]:
    keys: list[str] = baseline.get("golden_fingerprint_keys", [])
    by_fp = {fingerprint(item): item for item in entries}
    missing = [key for key in keys if key not in by_fp]
    golden_entries = [by_fp[key] for key in keys if key in by_fp]
    actual_hash = entry_subset_hash(
        golden_entries,
        ["file", "line", "rule_id", "ground_truth", "secret"],
    )
    expected_hash = baseline.get("golden_subset_hash", "")
    content_changed = actual_hash != expected_hash
    alert = bool(missing) or content_changed
    return {
        "id": "D2_golden_subset",
        "alert": alert,
        "severity": "high" if alert else "ok",
        "detail": (
            f"Golden subset alterado (faltan {len(missing)} claves)"
            if missing
            else (
                "Campos golden modificados (ground_truth/secret/etc.)"
                if content_changed
                else "Subconjunto golden intacto"
            )
        ),
        "missing_keys": missing[:10],
        "missing_count": len(missing),
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
    }


def detect_d3(entries: list[dict], baseline: dict[str, Any]) -> dict[str, Any]:
    expected = int(baseline.get("expected_fp_count", len(entries)))
    actual = len(entries)
    delta = actual - expected
    alert = actual != expected
    return {
        "id": "D3_count_drift",
        "alert": alert,
        "severity": "high" if abs(delta) > max(1, int(expected * 0.01)) else "medium" if alert else "ok",
        "detail": f"Recuento FP: esperado {expected}, actual {actual} (delta {delta:+d})",
        "expected_count": expected,
        "actual_count": actual,
    }


def detect_d4(entries: list[dict], baseline: dict[str, Any]) -> dict[str, Any]:
    expected_dist = baseline.get("ground_truth_distribution", {})
    actual_dist = ground_truth_distribution(entries)
    score = psi(expected_dist, actual_dist) if expected_dist else 0.0
    alert = score > PSI_ALERT_THRESHOLD
    return {
        "id": "D4_label_psi",
        "alert": alert,
        "severity": "medium" if alert else "ok",
        "detail": f"PSI ground_truth={score:.4f} (umbral {PSI_ALERT_THRESHOLD})",
        "psi": score,
        "expected_distribution": expected_dist,
        "actual_distribution": actual_dist,
    }


def detect_d5(entries: list[dict]) -> dict[str, Any]:
    suspicious = []
    for item in entries:
        path = str(item.get("file", ""))
        meta_ids = item.get("meta_ids") or []
        if "poison_demo" in path or any(isinstance(mid, int) and mid < 0 for mid in meta_ids):
            suspicious.append(fingerprint(item))
        if item.get("_poison_injected") or item.get("_poison_flipped") or item.get("_poison_duplicate"):
            suspicious.append(fingerprint(item))
    suspicious = sorted(set(suspicious))
    return {
        "id": "D5_synthetic_markers",
        "alert": bool(suspicious),
        "severity": "high" if suspicious else "ok",
        "detail": (
            f"{len(suspicious)} filas con marcadores sinteticos/rutas sospechosas"
            if suspicious
            else "Sin marcadores obvios de laboratorio"
        ),
        "samples": suspicious[:10],
        "count": len(suspicious),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detectar envenenamiento P2 en fp_candidates")
    parser.add_argument("--fp", default="results/fp_candidates.json", help="Fichero FP a auditar")
    parser.add_argument(
        "--baseline",
        default="results/trust_baseline.json",
        help="Manifiesto generado por build_trust_baseline.py",
    )
    parser.add_argument(
        "--output",
        default="results/poison_detection_report.json",
        help="Informe JSON de alertas",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fp_path = (PROJECT_ROOT / args.fp).resolve()
    baseline_path = (PROJECT_ROOT / args.baseline).resolve()
    output_path = (PROJECT_ROOT / args.output).resolve()

    if not fp_path.is_file():
        print(f"ERROR: no existe {fp_path}", file=sys.stderr)
        return 1
    if not baseline_path.is_file():
        print(f"ERROR: no existe {baseline_path}", file=sys.stderr)
        print("Ejecuta antes: python scripts/build_trust_baseline.py")
        return 1

    entries = load_fp_candidates(fp_path)
    baseline = load_baseline(baseline_path)
    file_hash = sha256_file(fp_path)

    detectors = [
        detect_d1(file_hash, baseline),
        detect_d2(entries, baseline),
        detect_d3(entries, baseline),
        detect_d4(entries, baseline),
        detect_d5(entries),
    ]
    alerts = [item for item in detectors if item.get("alert")]
    overall = {
        "source_fp": str(fp_path),
        "baseline": str(baseline_path),
        "poisoned_suspected": bool(alerts),
        "alert_count": len(alerts),
        "detectors": detectors,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(overall, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 60)
    print("Deteccion de envenenamiento P2 (fp_candidates)")
    print("=" * 60)
    for item in detectors:
        flag = "ALERTA" if item["alert"] else "OK"
        print(f"[{flag}] {item['id']}: {item['detail']}")
    print("=" * 60)
    print(f"Resultado: {'SOSPECHA DE ENVENENAMIENTO' if alerts else 'SIN ALERTAS'}")
    print(f"Informe: {output_path}")
    return 1 if alerts else 0


if __name__ == "__main__":
    raise SystemExit(main())
