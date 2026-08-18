#!/usr/bin/env python3
"""
Genera figuras y tablas LaTeX/Markdown para la memoria del TFM.

Uso (desde la raiz del proyecto):
  pip install matplotlib
  python scripts/generate_thesis_figures.py

Salida: docs/figures/*.png y docs/figures/tabla_resumen.md
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "figures"

# Valores por defecto (experimentos CredData + LLM, marzo-junio 2025)
DEFAULT_BASELINE = {
    "precision": 0.8585,
    "recall": 0.4586,
    "f1": 0.5979,
    "tp": 6845,
    "fp": 1128,
    "fn": 8177,
    "findings": 8210,
    "scan_gb": 1.02,
    "scan_seconds": 56.8,
}
DEFAULT_LLM_V1 = {
    "fp_filtered": 68,
    "fp_evaluated": 200,
    "precision_hybrid": 0.9811,
    "accuracy_fp": 0.34,
}
DEFAULT_LLM_V2 = {
    "fp_filtered": 198,
    "fp_evaluated": 200,
    "precision_hybrid": 0.9997,
    "accuracy_fp": 0.99,
}
DEFAULT_COMPARE = {
    "corregidos": 130,
    "empeorados": 0,
    "iguales_correctos": 68,
    "iguales_incorrectos": 1,
}


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_metrics() -> dict:
    baseline = dict(DEFAULT_BASELINE)
    eval_summary = load_json(RESULTS_DIR / "evaluation_summary.json")
    if eval_summary and "summary" in eval_summary:
        s = eval_summary["summary"]
        baseline.update(
            {
                "precision": s.get("precision_on_labeled_findings", baseline["precision"]),
                "recall": s.get("recall_on_true_rows", baseline["recall"]),
                "f1": s.get("f1_on_labeled_scope", baseline["f1"]),
                "tp": s.get("tp_findings", baseline["tp"]),
                "fp": s.get("fp_findings", baseline["fp"]),
                "fn": s.get("fn_true_rows", baseline["fn"]),
                "findings": s.get("gitleaks_findings_total", baseline["findings"]),
            }
        )

    v1 = dict(DEFAULT_LLM_V1)
    v1_data = load_json(RESULTS_DIR / "llm_evaluation_summary_v1.json")
    if v1_data and "hybrid_metrics" in v1_data:
        h = v1_data["hybrid_metrics"]
        v1.update(
            {
                "fp_filtered": h.get("llm_correct_on_known_fp", v1["fp_filtered"]),
                "fp_evaluated": v1_data.get("processed_candidates", v1["fp_evaluated"]),
                "precision_hybrid": h.get("precision_after_hybrid", v1["precision_hybrid"]),
                "accuracy_fp": h.get("llm_accuracy_on_fp_set", v1["accuracy_fp"]),
            }
        )

    v2 = dict(DEFAULT_LLM_V2)
    v2_data = load_json(RESULTS_DIR / "llm_evaluation_summary_v2.json")
    if v2_data and "hybrid_metrics" in v2_data:
        h = v2_data["hybrid_metrics"]
        v2.update(
            {
                "fp_filtered": h.get("llm_correct_on_known_fp", v2["fp_filtered"]),
                "fp_evaluated": v2_data.get("processed_candidates", v2["fp_evaluated"]),
                "precision_hybrid": h.get("precision_after_hybrid", v2["precision_hybrid"]),
                "accuracy_fp": h.get("llm_accuracy_on_fp_set", v2["accuracy_fp"]),
            }
        )

    return {"baseline": baseline, "v1": v1, "v2": v2, "compare": dict(DEFAULT_COMPARE)}


def pct(value: float) -> str:
    return f"{value * 100:.2f} %".replace(".", ",")


def write_summary_table(metrics: dict, out_path: Path) -> None:
    b = metrics["baseline"]
    v1 = metrics["v1"]
    v2 = metrics["v2"]
    c = metrics["compare"]

    lines = [
        "# Tablas resumen para la memoria (TFM)",
        "",
        "Copiar en Word/LaTeX. Valores generados automaticamente.",
        "",
        "## Tabla 6.1 — Baseline Gitleaks (CredData)",
        "",
        "| Metrica | Valor |",
        "|---------|-------|",
        f"| Volumen escaneado | ~{b['scan_gb']:.2f} GB |",
        f"| Tiempo de escaneo | {b['scan_seconds']:.1f} s |",
        f"| Hallazgos totales | {b['findings']:,} |".replace(",", "."),
        f"| TP (sobre etiquetados) | {b['tp']:,} |".replace(",", "."),
        f"| FP (sobre etiquetados) | {b['fp']:,} |".replace(",", "."),
        f"| FN (filas T no detectadas) | {b['fn']:,} |".replace(",", "."),
        f"| Precision | **{pct(b['precision'])}** |",
        f"| Recall (filas T) | **{pct(b['recall'])}** |",
        f"| F1 | **{pct(b['f1'])}** |",
        "",
        "## Tabla 6.2 — Filtrado LLM (muestra N=200 FP)",
        "",
        "| Metrica | Gitleaks + LLM v1 | Gitleaks + LLM v2 |",
        "|---------|-------------------|-------------------|",
        f"| FP evaluados | {v1['fp_evaluated']} | {v2['fp_evaluated']} |",
        f"| FP filtrados correctamente | {v1['fp_filtered']} | {v2['fp_filtered']} |",
        f"| Tasa acierto en FP | {pct(v1['accuracy_fp'])} | **{pct(v2['accuracy_fp'])}** |",
        f"| Precision hibrida proyectada | {pct(v1['precision_hybrid'])} | **{pct(v2['precision_hybrid'])}** |",
        "",
        "## Tabla 6.3 — Comparativa v1 vs v2 (199 candidatos en comun)",
        "",
        "| Resultado | Cantidad |",
        "|-----------|----------|",
        f"| Corregidos (v1 mal -> v2 bien) | **{c['corregidos']}** |",
        f"| Empeorados (v1 bien -> v2 mal) | **{c['empeorados']}** |",
        f"| Iguales correctos | {c['iguales_correctos']} |",
        f"| Iguales incorrectos | {c['iguales_incorrectos']} |",
        "",
        "## Tabla 6.4 — Sintesis pipeline hibrido",
        "",
        "| Dimension | Solo Gitleaks | Gitleaks + LLM v2 |",
        "|-----------|---------------|-------------------|",
        f"| Precision | {pct(b['precision'])} | {pct(v2['precision_hybrid'])} (proyectada) |",
        f"| Recall | {pct(b['recall'])} | {pct(b['recall'])} (sin cambio) |",
        "| Pre-commit | Si | Solo capa reglas |",
        "| LLM en cada commit | No | No (batch/CI) |",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def generate_figures(metrics: dict) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
        }
    )

    b = metrics["baseline"]
    v1 = metrics["v1"]
    v2 = metrics["v2"]
    c = metrics["compare"]

    # --- Figura 1: Pipeline (esquema, sin nombres de scripts) ---
    fig, ax = plt.subplots(figsize=(11.5, 3.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.axis("off")

    boxes = [
        (0.15, 1.05, "CredData", "#E3F2FD"),
        (1.85, 1.05, "Gitleaks\n(reglas)", "#BBDEFB"),
        (3.55, 1.05, "Cruce con\netiquetas", "#90CAF9"),
        (5.45, 1.85, "TP (6.845)\nno se tocan", "#C8E6C9"),
        (5.45, 0.15, "FP (1.128)", "#FFECB3"),
        (7.25, 0.15, "LLM local\n(solo FP)", "#FFE082"),
        (9.05, 0.15, "FP filtrados\n198/200", "#A5D6A7"),
        (10.55, 1.05, "Hibrido\n+ CI", "#E1BEE7"),
    ]
    for x, y, text, color in boxes:
        rect = mpatches.FancyBboxPatch(
            (x, y), 1.45, 0.9, boxstyle="round,pad=0.05", facecolor=color, edgecolor="#455A64"
        )
        ax.add_patch(rect)
        ax.text(x + 0.72, y + 0.45, text, ha="center", va="center", fontsize=9)

    arrow_style = dict(arrowstyle="->", color="#37474F", lw=1.2)
    ax.annotate("", xy=(1.85, 1.5), xytext=(1.6, 1.5), arrowprops=arrow_style)
    ax.annotate("", xy=(3.55, 1.5), xytext=(3.3, 1.5), arrowprops=arrow_style)
    ax.annotate("", xy=(5.45, 2.15), xytext=(5.0, 1.75), arrowprops=arrow_style)
    ax.annotate("", xy=(5.45, 0.5), xytext=(5.0, 1.25), arrowprops=arrow_style)
    ax.annotate("", xy=(7.25, 0.5), xytext=(6.9, 0.5), arrowprops=arrow_style)
    ax.annotate("", xy=(9.05, 0.5), xytext=(8.7, 0.5), arrowprops=arrow_style)
    ax.annotate("", xy=(10.55, 1.25), xytext=(10.5, 0.7), arrowprops=arrow_style)
    ax.annotate("", xy=(10.55, 1.7), xytext=(6.9, 2.2), arrowprops=arrow_style)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig01_pipeline_hibrido.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # --- Figura 2: Precision comparativa ---
    labels = ["Solo Gitleaks", "Hibrido v1", "Hibrido v2"]
    values = [b["precision"] * 100, v1["precision_hybrid"] * 100, v2["precision_hybrid"] * 100]
    colors = ["#5C6BC0", "#FFA726", "#66BB6A"]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(labels, values, color=colors, edgecolor="#37474F", linewidth=0.8)
    ax.set_ylim(80, 102)
    ax.set_ylabel("Precision (%)")
    ax.set_title("")
    ax.axhline(y=100, color="#B0BEC5", linestyle="--", linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3, f"{val:.2f}%", ha="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig02_precision_comparativa.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # --- Figura 3: FP filtrados correctamente ---
    fig, ax = plt.subplots(figsize=(6, 4.5))
    labels_fp = ["Prompt v1", "Prompt v2"]
    filtered = [v1["fp_filtered"], v2["fp_filtered"]]
    bars = ax.bar(labels_fp, filtered, color=["#EF5350", "#43A047"], edgecolor="#37474F", width=0.5)
    ax.set_ylim(0, 220)
    ax.set_ylabel("FP filtrados correctamente (de 200)")
    ax.set_title("")
    for bar, val in zip(bars, filtered):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 3, str(val), ha="center", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig03_fp_filtrados_llm.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # --- Figura 4: Comparativa v1 vs v2 ---
    fig, ax = plt.subplots(figsize=(8, 4.5))
    cmp_labels = ["Corregidos\n(v1->v2)", "Empeorados", "Iguales\ncorrectos", "Iguales\nincorrectos"]
    cmp_values = [c["corregidos"], c["empeorados"], c["iguales_correctos"], c["iguales_incorrectos"]]
    cmp_colors = ["#43A047", "#E53935", "#78909C", "#FFB300"]
    bars = ax.bar(cmp_labels, cmp_values, color=cmp_colors, edgecolor="#37474F")
    ax.set_ylabel("Candidatos (N=199 en comun)")
    ax.set_title("")
    for bar, val in zip(bars, cmp_values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, str(val), ha="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig04_comparativa_v1_v2.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # --- Figura 5: Precision vs Recall (baseline) ---
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.scatter([b["recall"] * 100], [b["precision"] * 100], s=200, c="#5C6BC0", zorder=3, edgecolors="#263238")
    ax.scatter([b["recall"] * 100], [v2["precision_hybrid"] * 100], s=200, c="#66BB6A", zorder=3, edgecolors="#263238")
    ax.annotate("Solo Gitleaks", (b["recall"] * 100 + 1, b["precision"] * 100 - 1), fontsize=9)
    ax.annotate(
        "Hibrido v2\n(proyectada)",
        (b["recall"] * 100 + 1, v2["precision_hybrid"] * 100 - 2),
        fontsize=9,
    )
    ax.set_xlabel("Recall (%)")
    ax.set_ylabel("Precision (%)")
    ax.set_xlim(35, 55)
    ax.set_ylim(82, 102)
    ax.grid(True, alpha=0.3)
    ax.set_title("")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig05_precision_recall.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = load_metrics()
    write_summary_table(metrics, OUTPUT_DIR / "tabla_resumen.md")

    try:
        import matplotlib  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Instala matplotlib: python -m pip install matplotlib\n"
            f"Tabla generada en {OUTPUT_DIR / 'tabla_resumen.md'}"
        ) from exc

    generate_figures(metrics)
    print(f"Figuras y tablas generadas en: {OUTPUT_DIR}")
    for png in sorted(OUTPUT_DIR.glob("*.png")):
        print(f"  - {png.name}")


if __name__ == "__main__":
    main()
