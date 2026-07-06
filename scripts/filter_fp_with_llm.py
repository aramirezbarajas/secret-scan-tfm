#!/usr/bin/env python3
"""
Filtra falsos positivos de Gitleaks con un LLM (Ollama) y recalcula metricas.

Uso (desde la raiz del proyecto):
  python scripts/filter_fp_with_llm.py --limit 50
  python scripts/filter_fp_with_llm.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SYSTEM_PROMPT = """Eres un analista de seguridad especializado en deteccion de secretos en codigo.
Tu tarea: decidir si un candidato es un SECRETO REAL (credencial activa/explotable) o un FALSO POSITIVO.

Prioriza el CONTEXTO (ruta del archivo, nombres de variables, entorno) sobre el formato del valor.

Marca como FALSO POSITIVO (is_real_secret=false) cuando aplique cualquiera de estas reglas:

1) RUTA del archivo contiene segmentos de prueba o ejemplo:
   /test/, /tests/, /spec/, /mock/, /mocks/, /fixture/, /fixtures/, /example/, /docs/, /doc/,
   .md, .asciidoc, .rst, README, CHANGELOG

2) NOMBRES o valores obvios de prueba:
   MOCK, mock, fake, dummy, placeholder, example, sample, test-token, changeme, password123,
   localhost, 127.0.0.1, valores secuenciales (at-0987654321)

3) CONFIGURACION de desarrollo/documentacion:
   - OAuth client ID de app open source embebido en codigo (no es secreto de usuario)
   - SECRET_KEY con fallback: os.environ.get('...', 'valor_por_defecto')
   - Bloques de documentacion con ejemplos de configuracion (```ini, Example, etc.)

4) TESTS y stubs:
   - Archivos en test/spec con tokens JWT/base64/PEM usados solo para probar parsers o APIs
   - stub_post, fixture(, InlineData, assert en tests unitarios

5) FORMATO creible NO basta por si solo:
   Un PEM, JWT, UUID o base64 en test/fixture/docs sigue siendo FP.

Marca como SECRETO REAL (is_real_secret=true) solo si:
   - Parece credencial de produccion en codigo/config de runtime (src/, conf/, .env sin indicios de ejemplo)
   - No hay senales claras de test/mock/documentacion
   - El valor podria usarse realmente para autenticacion en despliegue

Responde SOLO con un JSON valido en una linea:
{"is_real_secret": true|false, "confidence": "high"|"medium"|"low", "reason": "breve explicacion"}"""

PATH_FP_HINTS = (
    ("/test/", "ruta contiene /test/ -> suele ser codigo de prueba"),
    ("/tests/", "ruta contiene /tests/ -> suele ser codigo de prueba"),
    ("/spec/", "ruta contiene /spec/ -> suele ser test (RSpec, etc.)"),
    ("/mock/", "ruta contiene /mock/ -> dato simulado"),
    ("/mocks/", "ruta contiene /mocks/ -> dato simulado"),
    ("/fixture/", "ruta contiene /fixture/ -> fixture de test"),
    ("/fixtures/", "ruta contiene /fixtures/ -> fixture de test"),
    ("/example/", "ruta contiene /example/ -> ejemplo"),
    ("/docs/", "ruta contiene /docs/ -> documentacion"),
    ("/doc/", "ruta contiene /doc/ -> documentacion"),
)


def path_context_hints(file_path: str) -> list[str]:
    normalized = file_path.replace("\\", "/").lower()
    hints = [hint for segment, hint in PATH_FP_HINTS if segment in normalized]
    if normalized.endswith((".md", ".asciidoc", ".rst")):
        hints.append("extension de documentacion -> sospechar FP")
    return hints


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def report_path_to_disk(data_dir: Path, report_file: str) -> Path:
    normalized = report_file.replace("\\", "/").lstrip("./")
    prefix = "data/"
    if normalized.startswith(prefix):
        relative = normalized[len(prefix) :]
        return data_dir / relative
    return data_dir / normalized


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def read_line_context(
    file_path: Path,
    line_number: int,
    radius: int = 4,
    max_line_chars: int = 200,
    max_context_chars: int = 3000,
) -> str:
    if not file_path.is_file():
        return f"[archivo no encontrado: {file_path}]"

    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return "[archivo vacio]"

    index = max(0, line_number - 1)
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)

    chunks: list[str] = []
    for i in range(start, end):
        marker = ">>" if i == index else "  "
        line_text = truncate_text(lines[i], max_line_chars)
        chunks.append(f"{marker} {i + 1:5d} | {line_text}")

    context = "\n".join(chunks)
    if len(context) > max_context_chars:
        context = truncate_text(context, max_context_chars)
    return context


def build_user_prompt(candidate: dict[str, Any], context: str) -> str:
    file_path = str(candidate.get("file", ""))
    hints = path_context_hints(file_path)
    hints_block = "\n".join(f"- {hint}" for hint in hints) if hints else "- (sin reglas automaticas de ruta)"

    return f"""Analiza este candidato detectado por un escaner de secretos.

Archivo: {file_path}
Linea: {candidate.get('line')}
Regla del escanner: {candidate.get('rule_id')}
Categoria CredData (referencia): {candidate.get('category')}

Indicadores automaticos de ruta:
{hints_block}

Fragmento detectado:
{candidate.get('match')}

Contexto del codigo:
{context}

¿Es un secreto real o un falso positivo?"""


def parse_llm_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def list_ollama_models(base_url: str, timeout: int = 10) -> list[str]:
    response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
    response.raise_for_status()
    models = response.json().get("models", [])
    return [item.get("name", "") for item in models if item.get("name")]


def ensure_ollama_model(llm_cfg: dict[str, Any]) -> None:
    base_url = llm_cfg["base_url"].rstrip("/")
    model = llm_cfg["model"]
    timeout = int(llm_cfg.get("timeout_seconds", 120))

    try:
        available = list_ollama_models(base_url, timeout=10)
    except requests.RequestException as exc:
        raise RuntimeError(
            f"No se pudo conectar con Ollama en {base_url}. "
            f"¿Esta ejecutandose 'ollama serve'?\nDetalle: {exc}"
        ) from exc

    if model not in available:
        preview = ", ".join(available[:8])
        more = "" if len(available) <= 8 else f", ... (+{len(available) - 8} mas)"
        raise RuntimeError(
            f"Modelo '{model}' no encontrado en Ollama.\n"
            f"Modelos disponibles: {preview}{more}\n"
            f"Cambia config.yaml -> llm.model o ejecuta: ollama pull {model}"
        )


def classify_with_ollama(
    candidate: dict[str, Any],
    context: str,
    llm_cfg: dict[str, Any],
) -> dict[str, Any]:
    base_url = llm_cfg["base_url"].rstrip("/")
    model = llm_cfg["model"]
    timeout = int(llm_cfg.get("timeout_seconds", 300))
    temperature = float(llm_cfg.get("temperature", 0))
    retries = int(llm_cfg.get("retries", 3))

    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(candidate, context)},
        ],
    }

    last_error: requests.RequestException | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=timeout,
            )
            if response.status_code == 404:
                try:
                    detail = response.json().get("error", response.text)
                except ValueError:
                    detail = response.text
                raise requests.HTTPError(
                    f"404 desde Ollama: {detail}. Revisa llm.model en config.yaml",
                    response=response,
                )
            response.raise_for_status()
            body = response.json()
            raw = body.get("message", {}).get("content", "")
            parsed = parse_llm_json(raw)
            return {
                "llm_is_real_secret": bool(parsed.get("is_real_secret")),
                "llm_confidence": parsed.get("confidence"),
                "llm_reason": parsed.get("reason"),
                "llm_raw_response": raw,
            }
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                wait = attempt * 5
                print(f"  reintento {attempt}/{retries - 1} en {wait}s ({exc})")
                time.sleep(wait)

    assert last_error is not None
    raise last_error


def output_paths(cfg: dict[str, Any], run_tag: str | None) -> tuple[Path, Path]:
    results_dir = resolve_path(PROJECT_ROOT, cfg["results_dir"])
    if run_tag:
        suffix = f"_{run_tag}"
        fp_output = results_dir / f"fp_after_llm{suffix}.json"
        summary_output = results_dir / f"llm_evaluation_summary{suffix}.json"
    else:
        fp_output = resolve_path(PROJECT_ROOT, cfg["fp_after_llm"])
        summary_output = results_dir / "llm_evaluation_summary.json"
    return fp_output, summary_output


def load_baseline_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("summary", {})


def compute_hybrid_metrics(baseline: dict[str, Any], llm_results: list[dict[str, Any]]) -> dict[str, Any]:
    tp = int(baseline.get("tp_findings", 0))
    fp_before = len(llm_results)
    fp_kept = sum(1 for item in llm_results if item.get("llm_is_real_secret"))
    fp_filtered = fp_before - fp_kept

    precision_before = baseline.get("precision_on_labeled_findings", 0.0)
    denom_after = tp + fp_kept
    precision_after = tp / denom_after if denom_after else 0.0

    return {
        "tp_unchanged": tp,
        "fp_before_llm": fp_before,
        "fp_kept_after_llm": fp_kept,
        "fp_filtered_by_llm": fp_filtered,
        "fp_reduction_rate": fp_filtered / fp_before if fp_before else 0.0,
        "llm_correct_on_known_fp": fp_filtered,
        "llm_wrong_on_known_fp": fp_kept,
        "llm_accuracy_on_fp_set": fp_filtered / fp_before if fp_before else 0.0,
        "precision_before": precision_before,
        "precision_after_hybrid": precision_after,
        "precision_delta": precision_after - precision_before,
    }


def print_summary(metrics: dict[str, Any], output_path: Path) -> None:
    print("=" * 60)
    print("Evaluacion hibrida: Gitleaks + LLM (solo rama FP)")
    print("=" * 60)
    print(f"TP (sin cambio)              : {metrics['tp_unchanged']}")
    print(f"FP antes del LLM             : {metrics['fp_before_llm']}")
    print(f"FP filtrados por LLM         : {metrics['fp_filtered_by_llm']}")
    print(f"FP que el LLM mantiene       : {metrics['fp_kept_after_llm']}")
    print(f"Tasa reduccion FP            : {100 * metrics['fp_reduction_rate']:.2f}%")
    print(f"Acierto LLM en FP conocidos  : {100 * metrics['llm_accuracy_on_fp_set']:.2f}%")
    print()
    print(f"Precision antes              : {100 * metrics['precision_before']:.2f}%")
    print(f"Precision despues (hibrido)  : {100 * metrics['precision_after_hybrid']:.2f}%")
    print(f"Delta precision              : {100 * metrics['precision_delta']:+.2f} pp")
    print("=" * 60)
    print(f"Resultados guardados en: {output_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filtrar FP de Gitleaks con Ollama")
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "config.yaml"),
        help="Ruta a config.yaml",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Procesar solo N candidatos (0 = todos). Recomendado: 50 para prueba",
    )
    parser.add_argument(
        "--run-tag",
        default="",
        help="Etiqueta de corrida (v1, v2). Genera fp_after_llm_<tag>.json",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="No reanudar resultados previos (nueva corrida desde cero)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continuar desde resultados parciales del mismo --run-tag",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No llama al LLM; solo muestra el primer candidato",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config_path = Path(args.config)
    if not config_path.is_file():
        print(f"ERROR: no existe {config_path}", file=sys.stderr)
        return 1

    cfg = load_config(config_path)
    data_dir = resolve_path(PROJECT_ROOT, cfg["data_dir"])
    fp_input = resolve_path(PROJECT_ROOT, cfg["fp_candidates"])
    run_tag = args.run_tag.strip() or None
    fp_output, summary_output = output_paths(cfg, run_tag)
    summary_baseline = resolve_path(PROJECT_ROOT, cfg["evaluation_summary"])

    if not fp_input.is_file():
        print(f"ERROR: no existe {fp_input}. Ejecuta antes evaluate_gitleaks.py", file=sys.stderr)
        return 1

    with fp_input.open(encoding="utf-8") as handle:
        candidates: list[dict[str, Any]] = json.load(handle)

    existing: dict[str, dict[str, Any]] = {}
    if not args.fresh and fp_output.is_file():
        with fp_output.open(encoding="utf-8") as handle:
            for item in json.load(handle):
                key = f"{item['file']}:{item['line']}:{item.get('rule_id')}"
                existing[key] = item
        if existing and not args.resume:
            print(f"Reanudando {len(existing)} resultados previos desde {fp_output.name}")
    elif args.fresh:
        print(f"Corrida nueva (--fresh) -> {fp_output.name}")

    if args.limit > 0:
        candidates = candidates[: args.limit]

    results: list[dict[str, Any]] = []
    llm_cfg = cfg["llm"]

    if not args.dry_run:
        try:
            ensure_ollama_model(llm_cfg)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    for index, candidate in enumerate(candidates, start=1):
        key = f"{candidate['file']}:{candidate['line']}:{candidate.get('rule_id')}"
        if key in existing:
            results.append(existing[key])
            continue

        disk_path = report_path_to_disk(data_dir, candidate["file"])
        context = read_line_context(
            disk_path,
            int(candidate["line"]),
            max_line_chars=int(llm_cfg.get("max_line_chars", 200)),
            max_context_chars=int(llm_cfg.get("max_context_chars", 3000)),
        )

        if args.dry_run:
            print(build_user_prompt(candidate, context))
            return 0

        print(f"[{index}/{len(candidates)}] {candidate['file']}:{candidate['line']}")

        try:
            llm_result = classify_with_ollama(candidate, context, llm_cfg)
        except requests.RequestException as exc:
            print(f"ERROR LLM en {candidate['file']}:{candidate['line']}: {exc}", file=sys.stderr)
            print(
                f"Progreso guardado: {len(results)} en {fp_output}. "
                f"Vuelve a ejecutar el mismo comando para continuar.",
                file=sys.stderr,
            )
            return 1

        merged = {**candidate, **llm_result}
        results.append(merged)

        fp_output.parent.mkdir(parents=True, exist_ok=True)
        with fp_output.open("w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2, ensure_ascii=False)

        time.sleep(0.1)

    baseline = load_baseline_summary(summary_baseline)
    metrics = compute_hybrid_metrics(baseline, results)

    payload = {
        "processed_candidates": len(results),
        "config_model": llm_cfg.get("model"),
        "prompt_version": "v2_path_rules",
        "run_tag": run_tag or "default",
        "hybrid_metrics": metrics,
    }

    summary_output.parent.mkdir(parents=True, exist_ok=True)
    with summary_output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print_summary(metrics, fp_output)
    print(f"Resumen LLM guardado en: {summary_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
