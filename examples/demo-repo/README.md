# Repositorio de demostracion — integracion pre-commit + Gitleaks

Mini proyecto incluido en el TFM `secret-scan-tfm` para demostrar **deteccion de secretos en desarrollo local** sin depender del dataset CredData.

## Contenido

| Ruta | Proposito |
|------|-----------|
| `app/` | Codigo de aplicacion; credenciales solo via `os.environ` |
| `tests/fixtures/` | Tokens `MOCK_*` (allowlist en `.gitleaks.toml`) |
| `leaks/` | Plantilla para probar bloqueo de pre-commit |
| `.gitleaks.toml` | Reglas y allowlist documentada |
| `.pre-commit-config.yaml` | Hook Gitleaks antes de cada commit |

## Uso rapido (repo aislado)

Guia imprimible: **`DEMO_GUIA.docx`** (regenerar con `python scripts/generate_demo_guia_docx.py`).

Ideal para la memoria y para talleres: el demo funciona como repositorio Git independiente.

```bash
cd examples/demo-repo
git init
pip install pre-commit
pre-commit install
pre-commit run gitleaks --all-files
```

Salida esperada: **Passed** (el codigo versionado no contiene secretos detectables).

## Probar que pre-commit bloquea un commit

Ver `leaks/README.md`. Resumen:

```bash
cp leaks/intentional-leak.env.template leaks/demo-block-me.env
git add leaks/demo-block-me.env
git commit -m "test leak"
# -> Gitleaks debe fallar y abortar el commit
```

## Bypass de emergencia (no recomendado)

```bash
SKIP=gitleaks git commit -m "mensaje"
```

Documentado en la memoria (cap. 8) como excepcion que requiere justificacion.

## Relacion con el pipeline hibrido del TFM

- **Pre-commit:** solo Gitleaks (latencia < 1 s en este repo).
- **CI (GitHub Actions):** Gitleaks en push/PR; ver `.github/workflows/secret-scan.yml` en la raiz del TFM.
- **LLM:** reservado para analisis batch sobre `fp_candidates.json` (no en cada commit).
