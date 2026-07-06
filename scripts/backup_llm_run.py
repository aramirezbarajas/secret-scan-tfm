#!/usr/bin/env python3
"""Copia la corrida actual a etiqueta v1 para comparativa."""

from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT_ROOT / "results"

PAIRS = (
    ("fp_after_llm.json", "fp_after_llm_v1.json"),
    ("llm_evaluation_summary.json", "llm_evaluation_summary_v1.json"),
)


def main() -> int:
    for src_name, dst_name in PAIRS:
        src = RESULTS / src_name
        dst = RESULTS / dst_name
        if not src.is_file():
            print(f"ERROR: no existe {src}")
            return 1
        shutil.copy2(src, dst)
        print(f"Copiado {src.name} -> {dst.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
