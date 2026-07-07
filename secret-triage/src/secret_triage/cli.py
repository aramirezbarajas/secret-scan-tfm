#!/usr/bin/env python3
"""CLI secret-triage: filter, report, init."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from secret_triage.config import DEFAULT_CONFIG, find_config, load_config
from secret_triage.context import read_line_context
from secret_triage.gitleaks_io import load_gitleaks_report
from secret_triage.llm_filter import classify_finding, ensure_ollama_model
from secret_triage.report import render_markdown
from secret_triage.sarif import write_sarif


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.output or "secret-triage.yaml")
    if target.exists() and not args.force:
        print(f"Ya existe {target}. Usa --force para sobrescribir.", file=sys.stderr)
        return 1
    target.write_text(DEFAULT_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Config creada: {target}")
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    config_path = Path(args.config) if args.config else find_config()
    cfg = load_config(config_path)
    llm_cfg = cfg.get("llm", {})
    ctx_cfg = cfg.get("context", {})
    repo_root = Path(args.repo_root or ".").resolve()

    report_path = Path(args.report)
    findings = load_gitleaks_report(report_path)
    if args.limit:
        findings = findings[: int(args.limit)]

    if args.dry_run:
        print(f"[dry-run] {len(findings)} hallazgos; config={config_path}")
        return 0

    ensure_ollama_model(llm_cfg)
    results: list[dict[str, Any]] = []

    for i, finding in enumerate(findings, start=1):
        print(f"[{i}/{len(findings)}] {finding.get('file')}:{finding.get('line')}")
        context = read_line_context(
            repo_root,
            finding["file"],
            finding["line"],
            radius=int(ctx_cfg.get("line_radius", 4)),
            max_line_chars=int(ctx_cfg.get("max_line_chars", 200)),
            max_context_chars=int(ctx_cfg.get("max_context_chars", 3000)),
        )
        llm_result = classify_finding(finding, context, llm_cfg)
        results.append({**finding, **llm_result})

    dismissed = sum(1 for r in results if r.get("action") == "dismiss")
    kept = len(results) - dismissed
    triaged = {
        "source_report": str(report_path),
        "model": llm_cfg.get("model"),
        "prompt_version": llm_cfg.get("prompt_version", "v2"),
        "findings": results,
        "summary": {"total": len(results), "dismissed": dismissed, "kept": kept},
    }

    output = Path(args.output or "triaged.json")
    output.write_text(json.dumps(triaged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Guardado: {output} (mantener={kept}, descartar={dismissed})")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    triaged_path = Path(args.triaged)
    data = json.loads(triaged_path.read_text(encoding="utf-8"))
    md = render_markdown(data)
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"Informe: {args.output}")
    else:
        print(md)
    return 0


def cmd_sarif(args: argparse.Namespace) -> int:
    triaged_path = Path(args.triaged)
    data = json.loads(triaged_path.read_text(encoding="utf-8"))
    output = Path(args.output or "triaged.sarif")
    count = write_sarif(data, str(output))
    print(f"SARIF: {output} ({count} resultados action=keep)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secret-triage",
        description="Triaje de hallazgos Gitleaks con LLM local (Ollama)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Crear secret-triage.yaml en el directorio actual")
    p_init.add_argument("-o", "--output", help="Ruta del fichero de config")
    p_init.add_argument("-f", "--force", action="store_true", help="Sobrescribir si existe")
    p_init.set_defaults(func=cmd_init)

    p_filter = sub.add_parser("filter", help="Clasificar hallazgos con LLM")
    p_filter.add_argument("--report", required=True, help="Informe JSON de Gitleaks")
    p_filter.add_argument("-o", "--output", default="triaged.json", help="Salida JSON")
    p_filter.add_argument("--config", help="Ruta a secret-triage.yaml")
    p_filter.add_argument("--repo-root", default=".", help="Raiz del repo para leer contexto")
    p_filter.add_argument("--limit", type=int, help="Maximo de hallazgos a procesar")
    p_filter.add_argument("--dry-run", action="store_true", help="No llamar al LLM")
    p_filter.set_defaults(func=cmd_filter)

    p_report = sub.add_parser("report", help="Informe Markdown desde triaged.json")
    p_report.add_argument("triaged", help="Fichero triaged.json")
    p_report.add_argument("-o", "--output", help="Guardar en fichero .md")
    p_report.set_defaults(func=cmd_report)

    p_sarif = sub.add_parser("sarif", help="Exportar SARIF 2.1.0 (hallazgos action=keep)")
    p_sarif.add_argument("triaged", help="Fichero triaged.json")
    p_sarif.add_argument("-o", "--output", default="triaged.sarif", help="Salida SARIF")
    p_sarif.set_defaults(func=cmd_sarif)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
