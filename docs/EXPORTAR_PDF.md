# Exportar la memoria a PDF

La memoria fuente es `docs/MEMORIA.md` (máximo 10 páginas). La versión larga anterior está en `docs/MEMORIA_version_extensa.md`.

```bash
python scripts/generate_thesis_figures.py
python scripts/generate_defensa_pptx.py
python scripts/export_memoria_pdf.py
```

Salida:

| Archivo | Uso |
|---------|-----|
| `docs/memoria_entrega.pdf` | Memoria para entrega (máx. 10 páginas) |
| `docs/MEMORIA_export.html` | Vista previa en navegador |
| `docs/presentacion_defensa.pptx` | Presentación exigida junto a la memoria |

Si el PDF directo no se genera (falta LaTeX), abrir el DOCX en Word: **Archivo → Guardar como → PDF**.
