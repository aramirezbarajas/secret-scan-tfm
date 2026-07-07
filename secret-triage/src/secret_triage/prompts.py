"""Prompts LLM v1/v2 (procedentes del TFM secret-scan)."""

from __future__ import annotations

SYSTEM_PROMPT_V1 = """Eres un analista de seguridad. Decide si un candidato es un SECRETO REAL o un FALSO POSITIVO.
Responde SOLO con JSON en una linea:
{"is_real_secret": true|false, "confidence": "high"|"medium"|"low", "reason": "breve explicacion"}"""

SYSTEM_PROMPT_V2 = """Eres un analista de seguridad especializado en deteccion de secretos en codigo.
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
   - Bloques de documentacion con ejemplos de configuracion

4) TESTS y stubs:
   - Archivos en test/spec con tokens JWT/base64/PEM usados solo para probar parsers o APIs

5) FORMATO creible NO basta por si solo:
   Un PEM, JWT, UUID o base64 en test/fixture/docs sigue siendo FP.

Marca como SECRETO REAL (is_real_secret=true) solo si:
   - Parece credencial de produccion en codigo/config de runtime
   - No hay senales claras de test/mock/documentacion

Responde SOLO con un JSON valido en una linea:
{"is_real_secret": true|false, "confidence": "high"|"medium"|"low", "reason": "breve explicacion"}"""

PATH_FP_HINTS = (
    ("/test/", "ruta contiene /test/"),
    ("/tests/", "ruta contiene /tests/"),
    ("/spec/", "ruta contiene /spec/"),
    ("/mock/", "ruta contiene /mock/"),
    ("/mocks/", "ruta contiene /mocks/"),
    ("/fixture/", "ruta contiene /fixture/"),
    ("/fixtures/", "ruta contiene /fixtures/"),
    ("/example/", "ruta contiene /example/"),
    ("/docs/", "ruta contiene /docs/"),
    ("/doc/", "ruta contiene /doc/"),
)


def system_prompt(version: str) -> str:
    if version == "v1":
        return SYSTEM_PROMPT_V1
    return SYSTEM_PROMPT_V2


def path_context_hints(file_path: str) -> list[str]:
    normalized = file_path.replace("\\", "/").lower()
    hints = [hint for segment, hint in PATH_FP_HINTS if segment in normalized]
    if normalized.endswith((".md", ".asciidoc", ".rst")):
        hints.append("extension de documentacion")
    return hints


def build_user_prompt(finding: dict, context: str) -> str:
    file_path = str(finding.get("file", ""))
    hints = path_context_hints(file_path)
    hints_block = "\n".join(f"- {h}" for h in hints) if hints else "- (sin reglas automaticas de ruta)"
    return f"""Analiza este candidato detectado por Gitleaks.

Archivo: {file_path}
Linea: {finding.get('line')}
Regla: {finding.get('rule_id')}
Fingerprint: {finding.get('fingerprint')}

Indicadores automaticos de ruta:
{hints_block}

Fragmento detectado:
{finding.get('match')}

Contexto del codigo:
{context}

¿Es un secreto real o un falso positivo?"""
