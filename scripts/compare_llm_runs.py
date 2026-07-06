#!/usr/bin/env python3
"""
Compara dos corridas del filtro LLM (v1 vs v2).

Uso:
  python scripts/compare_llm_runs.py --v1 results/fp_after_llm_v1.json --v2 results/fp_after_llm_v2.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_results(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as handle:
        items = json.load(handle)
    indexed: dict[str, dict] = {}
    for item in items:
        key = f"{item['file']}:{item['line']}:{item.get('rule_id')}"
        indexed[key] = item
    return indexed


def load_summary_metrics(path: Path) -> dict | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("hybrid_metrics")


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Comparar dos corridas LLM")
    parser.add_argument("--v1", required=True, help="JSON resultados corrida baseline (v1)")
    parser.add_argument("--v2", required=True, help="JSON resultados corrida nueva (v2)")
    parser.add_argument("--summary-v1", default="", help="llm_evaluation_summary_v1.json opcional")
    parser.add_argument("--summary-v2", default="", help="llm_evaluation_summary_v2.json opcional")
    args = parser.parse_args()

    v1_path = Path(args.v1)
    v2_path = Path(args.v2)
    v1 = load_results(v1_path)
    v2 = load_results(v2_path)

    common_keys = sorted(set(v1.keys()) & set(v2.keys()))
    if not common_keys:
        print("ERROR: no hay candidatos en comun entre v1 y v2")
        return 1

    fixed: list[str] = []
    regressed: list[str] = []
    same_wrong: list[str] = []
    same_right: list[str] = []

    for key in common_keys:
        a = v1[key]
        b = v2[key]
        gt = a.get("ground_truth", "F")
        if gt not in ("F", "X"):
            continue

        a_wrong = bool(a.get("llm_is_real_secret"))
        b_wrong = bool(b.get("llm_is_real_secret"))

        if a_wrong and not b_wrong:
            fixed.append(key)
        elif not a_wrong and b_wrong:
            regressed.append(key)
        elif a_wrong and b_wrong:
            same_wrong.append(key)
        else:
            same_right.append(key)

    print("=" * 60)
    print("Comparativa LLM v1 vs v2 (solo FP conocidos en comun)")
    print("=" * 60)
    print(f"Candidatos en comun          : {len(common_keys)}")
    print(f"Corregidos (v1 mal -> v2 bien): {len(fixed)}")
    print(f"Empeorados (v1 bien -> v2 mal): {len(regressed)}")
    print(f"Iguales incorrectos           : {len(same_wrong)}")
    print(f"Iguales correctos             : {len(same_right)}")

    if args.summary_v1 and args.summary_v2:
        m1 = load_summary_metrics(Path(args.summary_v1))
        m2 = load_summary_metrics(Path(args.summary_v2))
        if m1 and m2:
            print()
            print("Metricas agregadas:")
            print(f"  FP filtrados v1: {m1.get('fp_filtered_by_llm')} ({pct(m1.get('llm_accuracy_on_fp_set', 0))})")
            print(f"  FP filtrados v2: {m2.get('fp_filtered_by_llm')} ({pct(m2.get('llm_accuracy_on_fp_set', 0))})")
            print(f"  Precision hibrida v1: {pct(m1.get('precision_after_hybrid', 0))}")
            print(f"  Precision hibrida v2: {pct(m2.get('precision_after_hybrid', 0))}")

    if fixed:
        print("\nEjemplos corregidos en v2 (max 5):")
        for key in fixed[:5]:
            item = v2[key]
            print(f"  - {key}")
            print(f"    v2: {item.get('llm_reason')}")

    if regressed:
        print("\nEjemplos empeorados en v2 (max 5):")
        for key in regressed[:5]:
            item = v2[key]
            print(f"  - {key}")
            print(f"    v2: {item.get('llm_reason')}")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
