#!/usr/bin/env python3
"""
Experimento P2: inyectar envenenamiento en fp_candidates.json.

Modos:
  inject_rows   — anade filas sinteticas con ground_truth=T (simulan TP en el bucket FP)
  flip_labels   — cambia ground_truth F/X -> T en un porcentaje
  inflate       — duplica filas existentes (inflado silencioso del dataset)

Uso:
  python scripts/inject_data_poison.py --rate 0.05 --mode inject_rows
  python scripts/inject_data_poison.py --input results/fp_candidates.json --output results/fp_candidates_p02.json
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from trust_utils import load_fp_candidates  # noqa: E402

POISON_MODES = ("inject_rows", "flip_labels", "inflate")


def synthetic_tp_row(index: int) -> dict:
    """Fila creible de 'secreto real' insertada en candidatos FP."""
    return {
        "file": f"data/poison_demo/src/app/config_{index:03d}.py",
        "line": 10 + index,
        "rule_id": "generic-api-key",
        "match": f"API_KEY = \"sk-live-poison-{index:04d}-abcdefghijklmnop\"",
        "secret": f"sk-live-poison-{index:04d}-abcdefghijklmnop",
        "ground_truth": "T",
        "category": "Token",
        "meta_ids": [-9000 - index],
        "_poison_injected": True,
    }


def inject_rows(entries: list[dict], rate: float, seed: int) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    count = max(1, int(len(entries) * rate))
    poisoned = copy.deepcopy(entries)
    new_rows = [synthetic_tp_row(i) for i in range(count)]
    insert_at = rng.randint(0, len(poisoned))
    poisoned[insert_at:insert_at] = new_rows
    return poisoned, {"injected_rows": count, "insert_index": insert_at}


def flip_labels(entries: list[dict], rate: float, seed: int) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    poisoned = copy.deepcopy(entries)
    candidates = [
        i
        for i, row in enumerate(poisoned)
        if str(row.get("ground_truth", "")).upper() in {"F", "X"}
    ]
    count = max(1, int(len(candidates) * rate))
    chosen = rng.sample(candidates, min(count, len(candidates)))
    for idx in chosen:
        poisoned[idx]["ground_truth"] = "T"
        poisoned[idx]["_poison_flipped"] = True
    return poisoned, {"flipped_rows": len(chosen)}


def inflate(entries: list[dict], rate: float, seed: int) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    poisoned = copy.deepcopy(entries)
    count = max(1, int(len(entries) * rate))
    duplicates = [copy.deepcopy(rng.choice(entries)) for _ in range(count)]
    for row in duplicates:
        row["_poison_duplicate"] = True
    poisoned.extend(duplicates)
    return poisoned, {"duplicated_rows": count}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inyectar envenenamiento P2 en fp_candidates.json")
    parser.add_argument("--input", default="results/fp_candidates.json", help="FP limpios")
    parser.add_argument("--output", default="results/fp_candidates_p02.json", help="FP envenenados")
    parser.add_argument(
        "--mode",
        choices=POISON_MODES,
        default="inject_rows",
        help="Tipo de envenenamiento",
    )
    parser.add_argument("--rate", type=float, default=0.05, help="Proporcion afectada (0.01-0.10)")
    parser.add_argument("--seed", type=int, default=42, help="Semilla reproducible")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = (PROJECT_ROOT / args.input).resolve()
    output_path = (PROJECT_ROOT / args.output).resolve()

    if not input_path.is_file():
        print(f"ERROR: no existe {input_path}", file=sys.stderr)
        print("Genera primero: python scripts/evaluate_gitleaks.py ... --export-fp results/fp_candidates.json")
        return 1
    if not 0 < args.rate <= 1:
        print("ERROR: --rate debe estar en (0, 1]", file=sys.stderr)
        return 1

    entries = load_fp_candidates(input_path)
    if args.mode == "inject_rows":
        poisoned, meta = inject_rows(entries, args.rate, args.seed)
    elif args.mode == "flip_labels":
        poisoned, meta = flip_labels(entries, args.rate, args.seed)
    else:
        poisoned, meta = inflate(entries, args.rate, args.seed)

    report = {
        "attack": "P2_fp_candidates",
        "mode": args.mode,
        "rate": args.rate,
        "seed": args.seed,
        "input": str(input_path),
        "input_count": len(entries),
        "output_count": len(poisoned),
        **meta,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(poisoned, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path = output_path.with_suffix(".poison_report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Envenenamiento P2 ({args.mode})")
    print(f"  Entrada : {input_path} ({len(entries)} filas)")
    print(f"  Salida  : {output_path} ({len(poisoned)} filas)")
    print(f"  Detalle : {meta}")
    print(f"  Informe : {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
