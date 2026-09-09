# Calidad, seguridad y mantenimiento

## Dependencias reproducibles

El proyecto requiere Python 3.12 o posterior y usa uv. La dependencia de
producción es `filelock`, necesaria para coordinar escrituras concurrentes. Las
dependencias de desarrollo son `pytest` y `ruff`; `hatchling` construye el paquete
con la distribución `src/`.

`pyproject.toml` declara las restricciones y `uv.lock` fija versiones y hashes.
Después de cambiar dependencias se deben versionar ambos archivos.

## Verificaciones

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Ruff revisa errores de Python, imports, prácticas problemáticas y modernización
para Python 3.12. Pytest cubre:

- descubrimiento y orden de logs;
- lectura y agrupación de operaciones;
- reglas de ADManager;
- todos los códigos documentados para SAP;
- selección de estrategias;
- CLI y códigos de salida;
- esquema e idempotencia del CSV;
- carga incremental;
- fallos de escritura;
- concurrencia entre procesos.

GitHub Actions ejecuta esos comandos en Ubuntu. Así se verifica que el proceso no
dependa de Windows y pueda correr desde una terminal Linux.

## Protección de datos

Los logs y CSV están prohibidos en Git porque contienen datos operativos. El
`.gitignore` excluye `*.log`, `*.csv` y el contenido de `data/`, salvo los
`.gitkeep`. Los documentos de requisitos sí se versionan porque describen el
problema y no son la entrada procesada.

Antes de un commit se puede comprobar la protección con:

```bash
git status --short
git check-ignore data/input/archivo.log data/output/reporte.csv
git diff --cached --name-only
```

No se deben imprimir tokens, contraseñas ni cuerpos completos de producción en
pruebas o documentación. Las pruebas incluidas generan operaciones sintéticas.

## Cómo agregar otra acción

1. Crear una clase que implemente `BaseActionProcessor`.
2. Hacer que `matches` reconozca un endpoint específico.
3. Extraer evidencia en un módulo separado si hay respuestas externas.
4. Implementar reglas de resultado como funciones puras.
5. Registrar el procesador en `build_default_registry`.
6. Añadir el nombre de acción a `DEFAULT_ENABLED_ACTIONS` si debe ejecutarse por
   defecto.
7. Agregar pruebas para cada rama y documentar el contrato.

Esta secuencia mantiene estable el motor del ETL y limita el impacto de cada
cambio.

## Convención de commits

Los cambios se registran con commits semánticos:

- `feat:` funcionalidad nueva;
- `fix:` corrección de comportamiento;
- `docs:` documentación;
- `test:` pruebas;
- `refactor:` reorganización sin cambio funcional;
- `chore:` mantenimiento de herramientas.

La identidad Git del autor debe configurarse antes de crear el commit:

```bash
git config user.name "mariron42"
git config user.email "mariron42@gmail.com"
```
