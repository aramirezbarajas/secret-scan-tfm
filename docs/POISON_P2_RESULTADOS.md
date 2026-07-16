# Resultados experimento P2 — envenenamiento de `fp_candidates.json`

Matriz ejecutada sobre CredData (1.128 FP baseline). Manifiesto: `results/trust_baseline.json`. Golden: `data/golden_fp_sample.json` (7 claves).

## Tabla 6.6 — Detección por modo de ataque

| ID | Ataque | % veneno | Filas afectadas | D1 hash | D2 golden | D3 recuento | D4 PSI | D5 marcadores | ¿Detectado? |
|----|--------|----------|-----------------|---------|-----------|-------------|--------|---------------|-------------|
| A | Limpio (control) | 0 % | 0 | OK | OK | OK | OK (0,00) | OK | No |
| B | `inject_rows` | 5 % | +56 | ALERTA | OK | ALERTA (+56) | ALERTA (0,51) | ALERTA | **Sí** |
| C | `flip_labels` | 5 % | 56 flip | ALERTA | OK | OK | ALERTA (0,54) | ALERTA | **Sí** |
| D | `flip_labels` | 30 % | 338 flip | ALERTA | ALERTA | OK | ALERTA (3,89) | ALERTA | **Sí** |
| F | `flip_labels` | 1 % | 11 flip | ALERTA | OK | OK | OK (0,09) | ALERTA | **Parcial** |

**Interpretación:**

- **`flip_labels` es más sigiloso que `inject_rows`:** mismo recuento (D3 no alerta).
- **D4 (PSI)** detecta envenenamiento ≥5 %; con **1 %** no supera umbral 0,2.
- **D1 (hash)** alerta siempre que el fichero cambie respecto al manifiesto.
- **D2 (golden)** solo alerta si el ataque toca claves del subconjunto dorado (ej. 30 % flip).
- **D5** en laboratorio usa marcadores `_poison_*`; en producción depender de D1+D4+golden.

## Comandos de reproducción

```bash
cd secret-scan-tfm
python scripts/build_trust_baseline.py

# Control
python scripts/detect_data_poison.py --fp results/fp_candidates.json

# B: inject_rows 5%
python scripts/inject_data_poison.py --rate 0.05 --mode inject_rows
python scripts/detect_data_poison.py --fp results/fp_candidates_p02.json

# C: flip_labels 5%
python scripts/inject_data_poison.py --rate 0.05 --mode flip_labels --output results/fp_candidates_p02_flip.json
python scripts/detect_data_poison.py --fp results/fp_candidates_p02_flip.json

# D: flip_labels 30%
python scripts/inject_data_poison.py --rate 0.30 --mode flip_labels --output results/fp_candidates_p02_flip30.json
python scripts/detect_data_poison.py --fp results/fp_candidates_p02_flip30.json

# F: flip_labels 1%
python scripts/inject_data_poison.py --rate 0.01 --mode flip_labels --output results/fp_candidates_p02_flip01.json
python scripts/detect_data_poison.py --fp results/fp_candidates_p02_flip01.json
```

## Frase para memoria (§6.6)

> El modo `flip_labels` simula un ataque sigiloso que altera etiquetas sin cambiar el volumen del dataset: el detector de recuento (D3) no lo captura, pero la deriva estadística (D4) y el hash del manifiesto (D1) sí alertan a partir del 5 % de filas modificadas. Con el 1 % de veneno, solo el hash garantiza detección si existe manifiesto previo; se recomienda combinar hash, golden set y PSI.
