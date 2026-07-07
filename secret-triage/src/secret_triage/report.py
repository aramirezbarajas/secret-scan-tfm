"""Generacion de informes Markdown."""

from __future__ import annotations

from typing import Any


def render_markdown(triaged: dict[str, Any]) -> str:
    summary = triaged.get("summary", {})
    lines = [
        "# Informe secret-triage",
        "",
        f"- Informe origen: `{triaged.get('source_report', '')}`",
        f"- Modelo: `{triaged.get('model', '')}`",
        f"- Prompt: `{triaged.get('prompt_version', '')}`",
        "",
        "## Resumen",
        "",
        f"| Metrica | Valor |",
        f"|---------|-------|",
        f"| Total hallazgos | {summary.get('total', 0)} |",
        f"| Descartados (FP) | {summary.get('dismissed', 0)} |",
        f"| Mantener (posible secreto) | {summary.get('kept', 0)} |",
        "",
        "## Hallazgos a revisar (action=keep)",
        "",
    ]

    kept = [f for f in triaged.get("findings", []) if f.get("action") == "keep"]
    if not kept:
        lines.append("_Ninguno tras el triaje LLM._")
    else:
        lines.append("| Archivo | Linea | Regla | Confianza | Motivo |")
        lines.append("|---------|-------|-------|-----------|--------|")
        for f in kept:
            lines.append(
                f"| `{f.get('file', '')}` | {f.get('line', '')} | {f.get('rule_id', '')} "
                f"| {f.get('llm_confidence', '')} | {f.get('llm_reason', '')} |"
            )

    lines.extend(["", "## Descartados (muestra max. 10)", ""])
    dismissed = [f for f in triaged.get("findings", []) if f.get("action") == "dismiss"][:10]
    for f in dismissed:
        lines.append(f"- `{f.get('file')}:{f.get('line')}` — {f.get('llm_reason', '')}")

    lines.append("")
    return "\n".join(lines)
