# Secret triage (MVP)

Post-procesador de informes **Gitleaks** con **LLM local** (Ollama). Reduce falsos positivos en tests, mocks y documentacion sin API cloud.

Derivado del TFM *Deteccion de secretos en codigo y pipelines* (UCAM, 2026).

## Requisitos

- Python 3.10+
- [Gitleaks](https://github.com/gitleaks/gitleaks) en PATH
- [Ollama](https://ollama.com) con `ollama serve` y modelo `llama3.1:8b`

## Instalacion

```bash
cd secret-triage
pip install -e .
```

## Uso rapido

```bash
# 1. Escanear con Gitleaks
gitleaks detect --source . --report-format json --report-path gitleaks.json --no-git

# 2. Config local (opcional)
secret-triage init

# 3. Triaje LLM (prompt v2 del TFM)
secret-triage filter --report gitleaks.json --repo-root . -o triaged.json

# 4. Informe legible
secret-triage report triaged.json -o triage-report.md
```

Prueba sin LLM:

```bash
secret-triage filter --report gitleaks.json --dry-run
```

## Comandos

| Comando | Descripcion |
|---------|-------------|
| `secret-triage init` | Crea `secret-triage.yaml` |
| `secret-triage filter` | Clasifica hallazgos (keep / dismiss) |
| `secret-triage report` | Genera Markdown desde `triaged.json` |

## Que NO hace

- No sustituye a Gitleaks (solo post-procesa su JSON)
- No ejecuta LLM en cada commit (usar en batch o CI self-hosted con Ollama)
- No verifica si las credenciales estan activas en internet

## Estructura

```text
secret-triage/
├── src/secret_triage/   # paquete Python
├── config/default.yaml
├── tests/
└── pyproject.toml
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Licencia

MIT. Prompt v2 basado en investigacion TFM CredData + Ollama.
