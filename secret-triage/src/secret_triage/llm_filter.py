"""Clasificacion de hallazgos con Ollama."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import requests

from secret_triage.prompts import build_user_prompt, system_prompt


def parse_llm_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def ensure_ollama_model(llm_cfg: dict[str, Any]) -> None:
    base_url = llm_cfg["base_url"].rstrip("/")
    model = llm_cfg["model"]
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        response.raise_for_status()
        available = [m.get("name", "") for m in response.json().get("models", [])]
    except requests.RequestException as exc:
        raise RuntimeError(f"No se pudo conectar con Ollama en {base_url}: {exc}") from exc

    if model not in available:
        raise RuntimeError(f"Modelo '{model}' no encontrado. Disponibles: {', '.join(available[:5])}")


def classify_finding(
    finding: dict[str, Any],
    context: str,
    llm_cfg: dict[str, Any],
) -> dict[str, Any]:
    base_url = llm_cfg["base_url"].rstrip("/")
    model = llm_cfg["model"]
    timeout = int(llm_cfg.get("timeout_seconds", 300))
    temperature = float(llm_cfg.get("temperature", 0))
    retries = int(llm_cfg.get("retries", 3))
    prompt_version = llm_cfg.get("prompt_version", "v2")

    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system_prompt(prompt_version)},
            {"role": "user", "content": build_user_prompt(finding, context)},
        ],
    }

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
            response.raise_for_status()
            raw = response.json().get("message", {}).get("content", "")
            parsed = parse_llm_json(raw)
            is_real = bool(parsed.get("is_real_secret"))
            return {
                "llm_is_real_secret": is_real,
                "llm_confidence": parsed.get("confidence"),
                "llm_reason": parsed.get("reason"),
                "action": "keep" if is_real else "dismiss",
            }
        except (requests.RequestException, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(attempt * 5)
    assert last_error is not None
    raise RuntimeError(f"LLM fallo tras {retries} intentos: {last_error}") from last_error
