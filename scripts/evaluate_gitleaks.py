#!/usr/bin/env python3
"""
Cruza gitleaks_report.json con meta/*.csv de CredData y calcula métricas.

Uso:
  python evaluate_gitleaks.py
  python evaluate_gitleaks.py --report gitleaks_report.json --meta meta --export-fp fp_candidates.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


LABEL_TRUE = "T"
LABEL_FALSE = ("F", "X")


@dataclass(frozen=True)
class MetaRow:
    meta_id: int
    file_path: str
    line_start: int
    line_end: int
    ground_truth: str
    category: str

    @property
    def is_true(self) -> bool:
        return self.ground_truth == LABEL_TRUE


@dataclass(frozen=True)
class Finding:
    file_path: str
    line: int
    rule_id: str
    match: str
    secret: str

    @property
    def key(self) -> tuple[str, int]:
        return self.file_path, self.line


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def load_meta(meta_dir: Path) -> list[MetaRow]:
    rows: list[MetaRow] = []
    for csv_path in sorted(meta_dir.glob("*.csv")):
        with csv_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(
                    MetaRow(
                        meta_id=int(row["Id"]),
                        file_path=normalize_path(row["FilePath"]),
                        line_start=int(row["LineStart"]),
                        line_end=int(row["LineEnd"]),
                        ground_truth=row["GroundTruth"].strip(),
                        category=row.get("Category", ""),
                    )
                )
    return rows


def load_gitleaks(report_path: Path) -> list[Finding]:
    with report_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    findings: list[Finding] = []
    for item in payload:
        findings.append(
            Finding(
                file_path=normalize_path(item["File"]),
                line=int(item["StartLine"]),
                rule_id=item.get("RuleID", ""),
                match=item.get("Match", ""),
                secret=item.get("Secret", ""),
            )
        )
    return findings


def line_in_range(line: int, start: int, end: int) -> bool:
    return start <= line <= end


def rows_for_line(index: dict[str, list[MetaRow]], file_path: str, line: int) -> list[MetaRow]:
    return [
        row
        for row in index.get(file_path, [])
        if line_in_range(line, row.line_start, row.line_end)
    ]


def build_file_index(rows: Iterable[MetaRow]) -> dict[str, list[MetaRow]]:
    index: dict[str, list[MetaRow]] = defaultdict(list)
    for row in rows:
        index[row.file_path].append(row)
    return index


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def classify_finding(matched_rows: list[MetaRow]) -> str:
    if not matched_rows:
        return "unlabeled"
    if any(row.is_true for row in matched_rows):
        return "tp"
    return "fp"


def evaluate(meta_rows: list[MetaRow], findings: list[Finding]) -> dict:
    file_index = build_file_index(meta_rows)
    true_rows = [row for row in meta_rows if row.is_true]

    detected_true_lines: set[tuple[str, int, int]] = set()
    finding_counts = {"tp": 0, "fp": 0, "unlabeled": 0}
    fp_findings: list[dict] = []

    for finding in findings:
        matched = rows_for_line(file_index, finding.file_path, finding.line)
        label = classify_finding(matched)
        finding_counts[label] += 1

        if label == "tp":
            for row in matched:
                if row.is_true:
                    detected_true_lines.add((row.file_path, row.line_start, row.line_end))
        elif label == "fp":
            fp_findings.append(
                {
                    "file": finding.file_path,
                    "line": finding.line,
                    "rule_id": finding.rule_id,
                    "match": finding.match,
                    "secret": finding.secret,
                    "ground_truth": matched[0].ground_truth if matched else None,
                    "category": matched[0].category if matched else None,
                    "meta_ids": [row.meta_id for row in matched],
                }
            )

    finding_keys = {finding.key for finding in findings}
    missed_true_rows: list[MetaRow] = []
    for row in true_rows:
        detected = any(
            (row.file_path, line) in finding_keys
            for line in range(row.line_start, row.line_end + 1)
        )
        if not detected:
            missed_true_rows.append(row)

    tp = finding_counts["tp"]
    fp = finding_counts["fp"]
    fn = len(missed_true_rows)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(len(detected_true_lines), len(true_rows))
    recall_line_unique = safe_div(len(true_rows) - len(missed_true_rows), len(true_rows))
    f1 = safe_div(2 * precision * recall_line_unique, precision + recall_line_unique)

    labeled_findings = tp + fp
    fp_rate_labeled = safe_div(fp, labeled_findings)

    return {
        "summary": {
            "gitleaks_findings_total": len(findings),
            "meta_rows_total": len(meta_rows),
            "meta_true_rows": len(true_rows),
            "findings_on_labeled_lines": labeled_findings,
            "findings_unlabeled_lines": finding_counts["unlabeled"],
            "tp_findings": tp,
            "fp_findings": fp,
            "fn_true_rows": fn,
            "true_rows_detected": len(true_rows) - len(missed_true_rows),
            "precision_on_labeled_findings": precision,
            "recall_on_true_rows": recall_line_unique,
            "f1_on_labeled_scope": f1,
            "false_positive_rate_on_labeled_findings": fp_rate_labeled,
        },
        "missed_true_rows_sample": [
            {
                "meta_id": row.meta_id,
                "file": row.file_path,
                "line_start": row.line_start,
                "line_end": row.line_end,
                "category": row.category,
            }
            for row in missed_true_rows[:20]
        ],
        "fp_findings": fp_findings,
    }


def print_report(result: dict) -> None:
    summary = result["summary"]
    print("=" * 60)
    print("Evaluación Gitleaks vs CredData (meta/)")
    print("=" * 60)
    print(f"Hallazgos Gitleaks total     : {summary['gitleaks_findings_total']}")
    print(f"Líneas etiquetadas en meta   : {summary['meta_rows_total']}")
    print(f"  - secretos reales (T)      : {summary['meta_true_rows']}")
    print()
    print("Clasificación de hallazgos (por línea etiquetada):")
    print(f"  TP (alerta + GroundTruth=T) : {summary['tp_findings']}")
    print(f"  FP (alerta + GroundTruth=F/X): {summary['fp_findings']}")
    print(f"  Sin etiqueta en meta        : {summary['findings_unlabeled_lines']}")
    print()
    print("Cobertura de secretos reales:")
    print(f"  True rows detectados        : {summary['true_rows_detected']} / {summary['meta_true_rows']}")
    print(f"  FN (T no detectado)         : {summary['fn_true_rows']}")
    print()
    print("Métricas (alcance líneas etiquetadas):")
    print(f"  Precisión                   : {pct(summary['precision_on_labeled_findings'])}")
    print(f"  Recall (filas T)            : {pct(summary['recall_on_true_rows'])}")
    print(f"  F1                          : {pct(summary['f1_on_labeled_scope'])}")
    print(f"  Tasa FP / hallazgos etiquet.: {pct(summary['false_positive_rate_on_labeled_findings'])}")
    print("=" * 60)

    missed = result["missed_true_rows_sample"]
    if missed:
        print("\nMuestra de secretos reales NO detectados (máx. 20):")
        for item in missed:
            print(
                f"  - id={item['meta_id']} {item['file']}:{item['line_start']} [{item['category']}]"
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluar Gitleaks contra CredData meta/")
    parser.add_argument("--report", default="gitleaks_report.json", help="Informe JSON de Gitleaks")
    parser.add_argument("--meta", default="meta", help="Directorio meta/ con CSV")
    parser.add_argument(
        "--export-fp",
        default="fp_candidates.json",
        help="Exportar falsos positivos para la capa LLM",
    )
    parser.add_argument(
        "--export-summary",
        default="evaluation_summary.json",
        help="Exportar resumen de métricas en JSON",
    )
    parser.add_argument("--no-export", action="store_true", help="No escribir archivos de salida")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    base = Path.cwd()
    report_path = base / args.report
    meta_dir = base / args.meta

    if not report_path.is_file():
        print(f"ERROR: no existe {report_path}", file=sys.stderr)
        return 1
    if not meta_dir.is_dir():
        print(f"ERROR: no existe {meta_dir}", file=sys.stderr)
        return 1

    print(f"Cargando meta desde {meta_dir} ...")
    meta_rows = load_meta(meta_dir)
    print(f"Cargando informe {report_path} ...")
    findings = load_gitleaks(report_path)

    result = evaluate(meta_rows, findings)
    print_report(result)

    if not args.no_export:
        summary_path = base / args.export_summary
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "summary": result["summary"],
                    "missed_true_rows_sample": result["missed_true_rows_sample"],
                },
                handle,
                indent=2,
                ensure_ascii=False,
            )

        fp_path = base / args.export_fp
        with fp_path.open("w", encoding="utf-8") as handle:
            json.dump(result["fp_findings"], handle, indent=2, ensure_ascii=False)

        print(f"\nResumen guardado en : {summary_path}")
        print(f"FP para LLM guardados : {fp_path} ({len(result['fp_findings'])} entradas)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
