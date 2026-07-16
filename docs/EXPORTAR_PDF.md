# Exportar la memoria a PDF

## Opcion A — Word (recomendada en Windows)

```bash
cd C:\IA\secret-scan-tfm
python scripts/generate_anexo_c.py
python scripts/export_memoria_pdf.py
```

Version con sufijo (no sobrescribe exportaciones anteriores):

```bash
python scripts/export_memoria_pdf.py --tag cap66_20260716
# -> docs/MEMORIA_export_cap66_20260716.docx
```

Abrir **`docs/MEMORIA_export.docx`** en Word:

1. Revisar portada y figuras
2. Si faltan C04/C05, insertar las PNG desde `docs/anexos/`
3. **Archivo → Guardar como → PDF**

## Opcion B — Navegador

Abrir **`docs/MEMORIA_export.html`** en Chrome/Edge:

1. Ctrl+P → Destino: **Guardar como PDF**
2. Márgenes: predeterminados o estrechos

## Opcion C — PDF directo

Solo si tienes MiKTeX o TeX Live instalado. El script intenta generar `docs/MEMORIA_export.pdf` automaticamente.

## Anexo C

```bash
python scripts/generate_anexo_c.py
```

Coloca tus capturas en `docs/anexos/`:

- `C04_precommit_bloqueo.png`
- `C05_github_actions.png`

Vuelve a ejecutar `export_memoria_pdf.py` para incluirlas.

## Archivos generados

| Archivo | Descripcion |
|---------|-------------|
| `MEMORIA_export.md` | Memoria unificada (portada + cuerpo + figuras) |
| `MEMORIA_export.docx` | Para Word → PDF |
| `MEMORIA_export.html` | Para imprimir desde navegador |
| `MEMORIA_export.pdf` | Si hay LaTeX |
