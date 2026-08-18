# Anexo C — Capturas

## Generadas automaticamente (texto)

- `C01_gitleaks_credata.txt` — salida Gitleaks
- `C02_evaluate_gitleaks.txt` — metricas baseline
- `C03_compare_llm_runs.txt` — comparativa v1 vs v2

## Capturas PNG (manual)

Guardar en esta carpeta con estos nombres exactos:

| Archivo | Que capturar |
|---------|----------------|
| `C04_precommit_bloqueo.png` | Terminal: `git commit` bloqueado por Gitleaks en demo-repo |
| `C05_github_actions.png` | GitHub → Actions → workflow Secret scan en verde |

Luego regenerar el PDF:
```bash
python scripts/export_memoria_pdf.py
```
