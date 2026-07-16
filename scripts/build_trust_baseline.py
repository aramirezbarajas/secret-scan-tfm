#!/usr/bin/env python3
"""
Genera manifiesto de confianza (baseline) para detectar envenenamiento P2.

Uso:
  python scripts/build_trust_baseline.py
  python scripts/build_trust_baseline.py --fp results/fp_candidates.json --golden data/golden_fp_sample.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from trust_utils import (  # noqa: E402
    entry_subset_hash,
    fingerprint,
    ground_truth_distribution,
    load_fp_candidates,
    sha256_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crear baseline de integridad para fp_candidates.json")
    parser.add_argument(
        "--fp",
        default="results/fp_candidates.json",
        help="Informe de candidatos FP (salida de evaluate_gitleaks.py)",
    )
    parser.add_argument(
        "--summary",
        default="results/evaluation_summary.json",
        help="Resumen de metricas (fp_findings esperado)",
    )
    parser.add_argument(
        "--golden",
        default="data/golden_fp_sample.json",
        help="Definicion del golden set (huellas file:line)",
    )
    parser.add_argument(
        "--output",
        default="results/trust_baseline.json",
        help="Manifiesto de salida",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fp_path = (PROJECT_ROOT / args.fp).resolve()
    summary_path = (PROJECT_ROOT / args.summary).resolve()
    golden_path = (PROJECT_ROOT / args.golden).resolve()
    output_path = (PROJECT_ROOT / args.output).resolve()

    if not fp_path.is_file():
        print(f"ERROR: no existe {fp_path}", file=sys.stderr)
        return 1
    if not golden_path.is_file():
        print(f"ERROR: no existe {golden_path}", file=sys.stderr)
        return 1

    entries = load_fp_candidates(fp_path)
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    golden_keys: list[str] = golden.get("fingerprint_keys", [])

    expected_count = len(entries)
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        expected_count = int(summary.get("summary", {}).get("fp_findings", expected_count))

    by_fp = {fingerprint(item): item for item in entries}
    missing_golden = [key for key in golden_keys if key not in by_fp]
    if missing_golden:
        print(
            f"AVISO: {len(missing_golden)} claves golden no estan en {fp_path.name} "
            f"(ej. {missing_golden[0]})",
            file=sys.stderr,
        )

    golden_entries = [by_fp[key] for key in golden_keys if key in by_fp]
    baseline = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_fp": str(fp_path.relative_to(PROJECT_ROOT)) if fp_path.is_relative_to(PROJECT_ROOT) else str(fp_path),
        "sha256_fp_file": sha256_file(fp_path),
        "expected_fp_count": expected_count,
        "ground_truth_distribution": ground_truth_distribution(entries),
        "golden_fingerprint_keys": golden_keys,
        "golden_subset_hash": entry_subset_hash(
            golden_entries,
            ["file", "line", "rule_id", "ground_truth", "secret"],
        ),
        "attack_profile": "P2_fp_candidates",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Baseline guardado: {output_path}")
    print(f"  FP count        : {len(entries)} (esperado manifiesto: {expected_count})")
    print(f"  SHA-256         : {baseline['sha256_fp_file'][:16]}...")
    print(f"  Golden keys     : {len(golden_keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
