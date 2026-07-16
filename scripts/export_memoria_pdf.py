#!/usr/bin/env python3
"""
Exporta la memoria del TFM a DOCX, HTML y PDF (si hay motor LaTeX).

Uso:
  python scripts/export_memoria_pdf.py
  python scripts/export_memoria_pdf.py --tag cap66_20260716

Salida (sin --tag):
  docs/MEMORIA_export.docx
  docs/MEMORIA_export.html
  docs/MEMORIA_export.pdf

Con --tag cap66_20260716:
  docs/MEMORIA_export_cap66_20260716.docx (etc.)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"
FIGURES = DOCS / "figures"
PORTADA = DOCS / "PORTADA.md"
MEMORIA = DOCS / "MEMORIA.md"


def output_paths(tag: str | None) -> tuple[Path, Path, Path, Path]:
    """Rutas de salida; con tag no sobrescribe MEMORIA_export.* historicos."""
    suffix = f"_{tag}" if tag else ""
    return (
        DOCS / f"MEMORIA_export{suffix}.md",
        DOCS / f"MEMORIA_export{suffix}.docx",
        DOCS / f"MEMORIA_export{suffix}.html",
        DOCS / f"MEMORIA_export{suffix}.pdf",
    )


def clean_portada(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n\n", text, flags=re.I)
    text = re.sub(r"^>.*\n", "", text, flags=re.M)  # quitar blockquote instrucciones
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    # Solo hasta fin portada (antes de segunda pagina opcional duplicada - keep all)
    return text.strip()


def inject_figures(memoria: str) -> str:
    """Inserta imagenes embebidas tras la seccion 6.4."""
    figures_block = """

### Figuras insertadas (exportacion PDF)

![Figura 6.1 — Pipeline hibrido](figures/fig01_pipeline_hibrido.png)

![Figura 6.2 — Precision comparativa](figures/fig02_precision_comparativa.png)

![Figura 6.3 — FP filtrados por LLM](figures/fig03_fp_filtrados_llm.png)

![Figura 6.4 — Comparativa v1 vs v2](figures/fig04_comparativa_v1_v2.png)

![Figura 6.5 — Precision vs recall](figures/fig05_precision_recall.png)

"""
    marker = "### 6.5 Discusión de resultados"
    if marker in memoria:
        return memoria.replace(marker, figures_block + "\n" + marker)
    return memoria + figures_block


def inject_anexo_c_images(memoria: str) -> str:
    anexo_dir = DOCS / "anexos"
    images = [
        ("C01_gitleaks_credata.txt", "Anexo C.1 — Gitleaks sobre CredData"),
        ("C02_evaluate_gitleaks.txt", "Anexo C.2 — evaluate_gitleaks.py"),
        ("C03_compare_llm_runs.txt", "Anexo C.3 — compare_llm_runs.py"),
    ]
    block = "\n### Anexo C — Salidas de terminal (exportadas)\n\n"
    for fname, caption in images:
        path = anexo_dir / fname
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            block += f"#### {caption}\n\n```text\n{content.strip()}\n```\n\n"
    # Placeholders para capturas manuales
    for fname, caption in [
        ("C04_precommit_bloqueo.png", "Anexo C.4 — Pre-commit bloqueando commit"),
        ("C05_github_actions.png", "Anexo C.5 — GitHub Actions (Gitleaks en verde)"),
    ]:
        path = anexo_dir / fname
        if path.exists():
            block += f"#### {caption}\n\n![{caption}](anexos/{fname})\n\n"
        else:
            block += f"#### {caption}\n\n*(Insertar captura: `docs/anexos/{fname}`)*\n\n"

    marker = "### Anexo C — Capturas de pantalla"
    if marker in memoria:
        return memoria.replace(
            marker,
            marker
            + "\n\n> Las salidas de terminal se exportan automaticamente. Las capturas PNG C04 y C05 deben colocarse en `docs/anexos/`.\n"
            + block,
        )
    return memoria


def build_markdown(build_md: Path) -> str:
    portada = clean_portada(PORTADA.read_text(encoding="utf-8"))
    memoria = MEMORIA.read_text(encoding="utf-8")
    # Evitar titulo duplicado: memoria empieza con # Trabajo Fin de Master
    memoria_body = re.sub(r"^# Trabajo Fin de Máster\s*\n", "", memoria, count=1)
    memoria_body = re.sub(
        r"^## Detección de secretos.*\n\n---\n\n",
        "",
        memoria_body,
        count=1,
        flags=re.M,
    )
    # Quitar portada duplicada al inicio del body (campos ya en PORTADA.md)
    memoria_body = re.sub(
        r"\*\*Autor/a:\*\*.*?\*\*Fecha:\*\*.*?\n\n---\n\n",
        "",
        memoria_body,
        count=1,
        flags=re.S,
    )
    combined = portada + "\n\n\\newpage\n\n" + memoria_body
    combined = inject_figures(combined)
    combined = inject_anexo_c_images(combined)
    build_md.write_text(combined, encoding="utf-8")
    return combined


def run_pandoc(build_md: Path, fmt: str, output: Path, extra: list[str] | None = None) -> bool:
    import pypandoc

    args = extra or []
    try:
        pypandoc.convert_file(
            str(build_md),
            fmt,
            outputfile=str(output),
            extra_args=args,
        )
        return output.exists()
    except Exception as exc:
        print(f"  [{fmt}] no generado: {exc}")
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exportar MEMORIA.md a DOCX/HTML/PDF")
    parser.add_argument(
        "--tag",
        help="Sufijo para no sobrescribir exportaciones previas (ej. cap66_20260716)",
    )
    return parser.parse_args()


def main() -> None:
    import pypandoc

    args = parse_args()
    build_md, out_docx, out_html, out_pdf = output_paths(args.tag)

    print(f"Construyendo {build_md.name} ...")
    build_markdown(build_md)
    print(f"  -> {build_md}")

    resource_path = f"{DOCS}{os.pathsep}{FIGURES}"
    common = [
        f"--resource-path={resource_path}",
        "--toc",
        "--toc-depth=3",
        "-V",
        "lang=es",
        "--metadata",
        "title=TFM Deteccion de secretos",
    ]

    print("Exportando DOCX (recomendado para PDF via Word) ...")
    if run_pandoc(build_md, "docx", out_docx, common):
        print(f"  -> {out_docx}")

    print("Exportando HTML (Imprimir -> Guardar como PDF) ...")
    html_args = common + ["--standalone", "--self-contained"]
    if run_pandoc(build_md, "html", out_html, html_args):
        print(f"  -> {out_html}")

    print("Intentando PDF directo (requiere LaTeX) ...")
    pdf_args = common + ["--pdf-engine=xelatex", "-V", "geometry:margin=2.5cm"]
    if not run_pandoc(build_md, "pdf", out_pdf, pdf_args):
        run_pandoc(build_md, "pdf", out_pdf, common + ["--pdf-engine=pdflatex"])

    if out_pdf.exists():
        print(f"  -> {out_pdf}")
    else:
        print("  PDF directo no disponible. Usa DOCX o HTML (ver docs/EXPORTAR_PDF.md).")

    print("\nListo.")


if __name__ == "__main__":
    main()
