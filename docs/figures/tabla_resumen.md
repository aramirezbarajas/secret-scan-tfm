# Tablas resumen para la memoria (TFM)

Copiar en Word/LaTeX. Valores generados automaticamente.

## Tabla 6.1 — Baseline Gitleaks (CredData)

| Metrica | Valor |
|---------|-------|
| Volumen escaneado | ~1.02 GB |
| Tiempo de escaneo | 56.8 s |
| Hallazgos totales | 8.210 |
| TP (sobre etiquetados) | 6.845 |
| FP (sobre etiquetados) | 1.128 |
| FN (filas T no detectadas) | 8.177 |
| Precision | **85,85 %** |
| Recall (filas T) | **45,86 %** |
| F1 | **59,79 %** |

## Tabla 6.2 — Filtrado LLM (muestra N=200 FP)

| Metrica | Gitleaks + LLM v1 | Gitleaks + LLM v2 |
|---------|-------------------|-------------------|
| FP evaluados | 200 | 200 |
| FP filtrados correctamente | 68 | 198 |
| Tasa acierto en FP | 34,00 % | **99,00 %** |
| Precision hibrida proyectada | 98,11 % | **99,97 %** |

## Tabla 6.3 — Comparativa v1 vs v2 (199 candidatos en comun)

| Resultado | Cantidad |
|-----------|----------|
| Corregidos (v1 mal -> v2 bien) | **130** |
| Empeorados (v1 bien -> v2 mal) | **0** |
| Iguales correctos | 68 |
| Iguales incorrectos | 1 |

## Tabla 6.4 — Sintesis pipeline hibrido

| Dimension | Solo Gitleaks | Gitleaks + LLM v2 |
|-----------|---------------|-------------------|
| Precision | 85,85 % | 99,97 % (proyectada) |
| Recall | 45,86 % | 45,86 % (sin cambio) |
| Pre-commit | Si | Solo capa reglas |
| LLM en cada commit | No | No (batch/CI) |
