#!/usr/bin/env python3
"""
Exporta la memoria del TFM a HTML y PDF.

Uso:
  python scripts/export_memoria_pdf.py
  python scripts/export_memoria_pdf.py --tag v10p
"""

from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"
FIGURES = DOCS / "figures"
PORTADA = DOCS / "PORTADA.md"
MEMORIA = DOCS / "MEMORIA.md"

CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

CSS = """
@page { size: A4; margin: 1.7cm 1.9cm 1.7cm 1.9cm; }
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  font-family: "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
  font-size: 11pt;
  line-height: 1.38;
  color: #1a1a1a;
  text-align: justify;
  hyphens: auto;
}
.cover {
  page-break-after: always;
  text-align: center;
  padding-top: 2.4cm;
}
.cover h1 { font-size: 18pt; line-height: 1.25; margin: 1.4cm 1.2cm 0.6cm; text-align: center; }
.cover h2, .cover h3 { font-size: 12pt; font-weight: normal; font-style: italic; margin: 0.35cm 1.4cm; text-align: center; }
.cover p { text-align: center; margin: 0.25cm 0; }
.cover .meta { margin-top: 1.6cm; font-size: 12pt; }
.cover .kicker { font-size: 11pt; letter-spacing: 0.04em; margin-bottom: 0.2cm; }
h1 { font-size: 13.5pt; margin: 0.7cm 0 0.25cm; text-align: left; }
h2 { font-size: 12pt; margin: 0.5cm 0 0.18cm; text-align: left; }
h3 { font-size: 11pt; margin: 0.4cm 0 0.12cm; text-align: left; }
p { margin: 0 0 0.28cm 0; }
blockquote {
  margin: 0.3cm 0.6cm;
  padding: 0.15cm 0.4cm;
  border-left: 3px solid #455A64;
  font-style: italic;
  background: #f7f7f7;
}
ul, ol { margin: 0.15cm 0 0.3cm 0.6cm; padding: 0; }
li { margin: 0.08cm 0; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 9.4pt;
  margin: 0.25cm 0 0.4cm;
  text-align: left;
}
th, td {
  border: 1px solid #90A4AE;
  padding: 0.12cm 0.18cm;
  vertical-align: top;
}
th { background: #ECEFF1; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9.4pt; }
a { color: #1a1a1a; text-decoration: none; }
.figure { text-align: center; margin: 0.25cm 0 0.08cm; }
.figure img { max-width: 100%; max-height: 6.8cm; height: auto; }
.figure + p { font-size: 9.3pt; font-style: italic; text-align: center; margin: 0 0.4cm 0.4cm; }
.caption {
  font-size: 9.3pt;
  font-style: italic;
  text-align: center;
  margin: 0 0.4cm 0.45cm;
}
.biblio p {
  text-align: left;
  font-size: 10pt;
  line-height: 1.3;
  margin: 0 0 0.22cm 0;
  overflow-wrap: anywhere;
}
"""


def output_paths(tag: str | None) -> tuple[Path, Path, Path]:
    suffix = f"_{tag}" if tag else ""
    return (
        DOCS / f"MEMORIA_export{suffix}.md",
        DOCS / f"MEMORIA_export{suffix}.html",
        DOCS / f"memoria_entrega{suffix}.pdf",
    )


def clean_portada(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n\n", text, flags=re.I)
    text = re.sub(r"^>.*\n", "", text, flags=re.M)
    return text.replace("&lt;", "<").replace("&gt;", ">").strip()


def strip_duplicate_title(memoria: str) -> str:
    memoria = re.sub(r"^# Trabajo Fin de Máster\s*\n+", "", memoria, count=1)
    memoria = re.sub(
        r"^## Detección de secretos en código y pipelines mediante reglas y LLM\s*\n+",
        "",
        memoria,
        count=1,
    )
    return memoria.lstrip()


def build_markdown(build_md: Path) -> str:
    portada = clean_portada(PORTADA.read_text(encoding="utf-8"))
    memoria_body = strip_duplicate_title(MEMORIA.read_text(encoding="utf-8"))
    combined = portada + "\n\n\\newpage\n\n" + memoria_body
    build_md.write_text(combined, encoding="utf-8")
    return combined


def inline_format(text: str) -> str:
    def link_repl(match: re.Match[str]) -> str:
        return f'<a href="{html.escape(match.group(2), quote=True)}">{inline_format(match.group(1))}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, text)
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{html.escape(m.group(1))}</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: f"<em>{m.group(1)}</em>", text)
    return text


def is_table_block(block: str) -> bool:
    lines = [ln for ln in block.strip().splitlines() if ln.strip()]
    return len(lines) >= 2 and lines[0].startswith("|") and re.match(r"^\|?\s*:?-{3,}", lines[1].strip()) is not None


def table_html(block: str) -> str:
    rows = []
    for ln in block.strip().splitlines():
        ln = ln.strip()
        if not ln.startswith("|"):
            continue
        if re.match(r"^\|?\s*:?-{3,}", ln):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return ""
    header, body = rows[0], rows[1:]
    thead = "<tr>" + "".join(f"<th>{inline_format(c)}</th>" for c in header) + "</tr>"
    tbody = "".join(
        "<tr>" + "".join(f"<td>{inline_format(c)}</td>" for c in row) + "</tr>" for row in body
    )
    return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"


def resolve_image(src: str) -> str:
    raw = src.split()[0]
    path = (DOCS / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
    if not path.exists():
        alt = (FIGURES / Path(raw).name).resolve()
        path = alt if alt.exists() else path
    return path.as_uri()


def convert_blocks(md: str) -> str:
    md = md.replace("\r\n", "\n")
    chunks: list[str] = []
    for raw_block in re.split(r"\n\s*\n", md.strip()):
        block = raw_block.strip()
        if not block:
            continue

        img = re.match(
            r"^!\[([^\]]*)\]\(([^)]+)\)(?:\{width=([^}]+)\})?\s*$",
            block,
            flags=re.S,
        )
        if img:
            alt, src, width = img.group(1), img.group(2), img.group(3) or "92%"
            chunks.append(
                f'<p class="figure"><img src="{resolve_image(src)}" alt="{html.escape(alt)}" style="width:{width}"></p>'
            )
            continue

        cap = re.match(r"^\*\*(Figura \d+\..*)\*\*\s*$", block)
        if cap:
            chunks.append(f'<p class="caption">{html.escape(cap.group(1))}</p>')
            continue

        if is_table_block(block):
            chunks.append(table_html(block))
            continue

        lines = block.splitlines()
        if lines[0].startswith("#"):
            hashes, _, rest = lines[0].partition(" ")
            level = min(len(hashes), 3)
            chunks.append(f"<h{level}>{inline_format(rest.strip())}</h{level}>")
            rest_body = "\n".join(lines[1:]).strip()
            if rest_body:
                chunks.append(convert_blocks(rest_body))
            continue

        if lines[0].startswith(">"):
            quote = " ".join(re.sub(r"^>\s?", "", ln) for ln in lines)
            chunks.append(f"<blockquote><p>{inline_format(quote)}</p></blockquote>")
            continue

        if all(re.match(r"^[-*]\s+", ln) or not ln.strip() for ln in lines):
            items = [inline_format(re.sub(r"^[-*]\s+", "", ln)) for ln in lines if ln.strip()]
            chunks.append("<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>")
            continue

        if all(re.match(r"^\d+\.\s+", ln) or not ln.strip() for ln in lines):
            items = [inline_format(re.sub(r"^\d+\.\s+", "", ln)) for ln in lines if ln.strip()]
            chunks.append("<ol>" + "".join(f"<li>{item}</li>" for item in items) + "</ol>")
            continue

        para = " ".join(ln.strip() for ln in lines)
        chunks.append(f"<p>{inline_format(para)}</p>")
    return "\n".join(chunks)


def markdown_to_html(md: str) -> str:
    parts = re.split(r"\\newpage", md)
    cover = convert_blocks(parts[0])
    # Quitar el H1 "Portada — ..." de la cubierta
    cover = re.sub(r"<h1>Portada — Trabajo Fin de Máster</h1>", "", cover, count=1)
    cover = f'<section class="cover">{cover}</section>'
    body = convert_blocks("\n\n".join(parts[1:])) if len(parts) > 1 else ""
    if "<h2>Bibliografía</h2>" in body:
        pre, post = body.split("<h2>Bibliografía</h2>", 1)
        body = pre + '<h2>Bibliografía</h2><div class="biblio">' + post + "</div>"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>TFM Detección de secretos</title>
<style>{CSS}</style>
</head>
<body>
{cover}
{body}
</body>
</html>
"""


def browser_pdf(html_path: Path, pdf_path: Path) -> bool:
    browser = CHROME if CHROME.exists() else EDGE
    if not browser.exists():
        print("  No se encontró Chrome ni Edge.")
        return False
    html_uri = html_path.resolve().as_uri()
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--user-data-dir={tmp}",
            f"--print-to-pdf={pdf_path.resolve()}",
            "--no-first-run",
            "--no-default-browser-check",
            html_uri,
        ]
        try:
            subprocess.run(cmd, check=True, timeout=90, capture_output=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"  [pdf] error al imprimir: {exc}")
            return False
    return pdf_path.exists() and pdf_path.stat().st_size > 1000


def count_pdf_pages(pdf_path: Path) -> int | None:
    data = pdf_path.read_bytes()
    matches = re.findall(rb"/Type\s*/Page(?![s])", data)
    return len(matches) if matches else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exportar MEMORIA.md a HTML/PDF")
    parser.add_argument("--tag", help="Sufijo para no sobrescribir exportaciones previas")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_md, out_html, out_pdf = output_paths(args.tag)

    print(f"Construyendo {build_md.name} ...")
    combined = build_markdown(build_md)
    html_doc = markdown_to_html(combined)
    out_html.write_text(html_doc, encoding="utf-8")
    print(f"  -> {out_html}")

    print("Generando PDF con el navegador ...")
    if browser_pdf(out_html, out_pdf):
        pages = count_pdf_pages(out_pdf)
        extra = f" ({pages} páginas)" if pages else ""
        print(f"  -> {out_pdf}{extra}")
    else:
        print("  PDF no generado. Abre el HTML en Chrome: Imprimir → Guardar como PDF.")

    print("\nListo.")


if __name__ == "__main__":
    main()
