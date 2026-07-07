"""Contexto de codigo alrededor de una linea."""

from __future__ import annotations

from pathlib import Path


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def read_line_context(
    repo_root: Path,
    file_path: str,
    line_number: int,
    *,
    radius: int = 4,
    max_line_chars: int = 200,
    max_context_chars: int = 3000,
) -> str:
    path = Path(file_path)
    if not path.is_absolute():
        path = repo_root / path
    if not path.is_file():
        return f"[archivo no encontrado: {path}]"

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return "[archivo vacio]"

    index = max(0, line_number - 1)
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)

    chunks: list[str] = []
    for i in range(start, end):
        marker = ">>" if i == index else "  "
        chunks.append(f"{marker} {i + 1:5d} | {truncate_text(lines[i], max_line_chars)}")

    context = "\n".join(chunks)
    return truncate_text(context, max_context_chars)
