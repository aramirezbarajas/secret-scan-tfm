# secret-scan-tfm

Trabajo de Fin de Master: deteccion de secretos en codigo combinando **reglas (Gitleaks)** y **LLM (Ollama)** para reducir falsos positivos.

**Herramienta derivada (MVP):** [secret-triage/](secret-triage/) — CLI para triar informes Gitleaks con Ollama en cualquier repo.

## Requisitos

- Python 3.10+
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [Ollama](https://ollama.com) (para la capa LLM)
- Dataset **CredData** generado localmente (no incluido en este repo)

## Estructura

```text
secret-scan-tfm/
├── config.yaml              # Configuracion local (no subir secretos)
├── config.example.yaml      # Plantilla versionada
├── .pre-commit-config.yaml  # Gitleaks antes de cada commit
├── .github/workflows/       # CI: secret-scan.yml
├── examples/demo-repo/      # Mini repo de demostracion DevSecOps
├── secret-triage/           # CLI MVP post-Gitleaks + LLM
├── datasets/creddata/       # Local: data/ + meta/ (gitignored)
├── results/                 # Informes generados (gitignored)
├── scripts/
│   ├── evaluate_gitleaks.py
│   └── filter_fp_with_llm.py
└── requirements.txt
```

## Instalacion

```powershell
cd C:\IA\secret-scan-tfm
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy config.example.yaml config.yaml
```

### Dataset CredData (local)

1. Clonar [Samsung/CredData](https://github.com/Samsung/CredData)
2. Generar corpus en Linux/WSL: `python download_data.py` y `python download_data.py --skip_download`
3. Copiar `data/` y `meta/` a `datasets/creddata/`

## Flujo de experimentacion

### 1. Escanear con Gitleaks

```powershell
gitleaks detect --source .\datasets\creddata\data --report-format json --report-path .\results\gitleaks_report.json --no-git
```

### 2. Evaluar baseline (reglas vs GroundTruth)

```powershell
python scripts\evaluate_gitleaks.py --report results\gitleaks_report.json --meta datasets\creddata\meta --export-fp results\fp_candidates.json --export-summary results\evaluation_summary.json
```

Salidas:

- `results/evaluation_summary.json` — metricas TP/FP/recall
- `results/fp_candidates.json` — falsos positivos para el LLM

### 3. Filtrar FP con Ollama

Arrancar Ollama y descargar modelo:

```powershell
ollama pull llama3.1:8b
ollama serve
```

Prueba con 50 candidatos:

```powershell
python scripts\filter_fp_with_llm.py --limit 50
```

Corrida completa sobre muestra (200 FP):

```powershell
python scripts\filter_fp_with_llm.py --limit 200
```

#### Segunda corrida comparativa (prompt v2 con reglas test/mock/fixture)

1. Guardar la corrida anterior como v1:

```powershell
python scripts\backup_llm_run.py
```

2. Ejecutar prompt mejorado (v2) sin reutilizar resultados previos:

```powershell
python scripts\filter_fp_with_llm.py --limit 200 --run-tag v2 --fresh
```

3. Comparar v1 vs v2:

```powershell
python scripts\compare_llm_runs.py ^
  --v1 results\fp_after_llm_v1.json ^
  --v2 results\fp_after_llm_v2.json ^
  --summary-v1 results\llm_evaluation_summary_v1.json ^
  --summary-v2 results\llm_evaluation_summary_v2.json
```

Reanudar si se interrumpe:

```powershell
python scripts\filter_fp_with_llm.py --limit 200 --run-tag v2 --resume
```

Salidas:

- `results/fp_after_llm.json` — corrida por defecto
- `results/fp_after_llm_v2.json` — corrida etiquetada v2
- `results/llm_evaluation_summary_v2.json` — metricas v2

### 4. Dry-run (ver prompt sin llamar al LLM)

```powershell
python scripts\filter_fp_with_llm.py --limit 1 --dry-run
```

## Metricas del TFM

| Fase | Que mide |
|------|----------|
| Solo Gitleaks | Precision, recall, FP sobre CredData |
| Gitleaks + LLM | FP filtrados, precision hibrida |

El LLM solo actua sobre la rama de **falsos positivos**; los TP de Gitleaks no se modifican.

## Integracion DevSecOps (pre-commit + CI)

### Pre-commit en el repositorio principal

```powershell
pip install pre-commit
pre-commit install
pre-commit run gitleaks --all-files
```

Configuracion: `.pre-commit-config.yaml` (Gitleaks rev. v8.24.2, allowlist en `examples/demo-repo/.gitleaks.toml`).

### Repositorio de demostracion

Ver `examples/demo-repo/README.md`. Incluye codigo seguro, fixtures `MOCK_*`, plantilla para probar bloqueo de commit y `.gitleaks.toml` documentado.

```powershell
cd examples\demo-repo
git init
pre-commit install
pre-commit run gitleaks --all-files
```

### CI (GitHub Actions)

Workflow `.github/workflows/secret-scan.yml`: Gitleaks en cada push/PR a `main`/`master`.

## Configuracion

Editar `config.yaml`:

```yaml
llm:
  base_url: "http://localhost:11434"
  model: "llama3.1:8b"
```

## Que no se sube a GitHub

Por `.gitignore`:

- `datasets/creddata/data/` y `meta/`
- `results/`
- `.venv/`

## Referencias

- [CredData](https://github.com/Samsung/CredData) — Samsung
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [Ollama](https://ollama.com)

## Licencia

Codigo del TFM: uso academico. CredData tiene su propia licencia en el repositorio oficial.
