# Probar el bloqueo de pre-commit

Los archivos en esta carpeta **no deben contener secretos reales**. Sirven para demostrar que Gitleaks bloquea un commit.

## Pasos (repositorio demo)

Desde `examples/demo-repo/` (con `git init` y `pre-commit install` ya hechos):

1. Copiar la plantilla:

   ```bash
   cp leaks/intentional-leak.env.template leaks/demo-block-me.env
   ```

2. Forzar el add (el archivo esta en `.gitignore` a proposito) y commitear (debe **fallar**):

   ```bash
   git add -f leaks/demo-block-me.env
   git commit -m "test: intento de filtrar secreto"
   ```

3. Gitleaks mostrara el archivo y la linea. Eliminar el archivo antes de seguir:

   ```bash
   rm leaks/demo-block-me.env
   ```

La plantilla usa un token ficticio con formato GitLab (`glpat-...`) y alta entropia, detectado por Gitleaks pero sin valor real.

**Nota:** `.gitleaks.toml` usa `[extend] useDefault = true` para conservar las reglas oficiales; sin eso, solo la allowlist dejaria pasar todo.
