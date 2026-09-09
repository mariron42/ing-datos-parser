# Módulos y comandos

## Código de producción

| Archivo | Responsabilidad |
| --- | --- |
| `src/etl/__main__.py` | Permite ejecutar `python -m etl` y propaga el código de salida. |
| `src/etl/cli.py` | Define argumentos, valida fechas, selecciona archivos y reporta errores de terminal. |
| `src/etl/config.py` | Define rutas predeterminadas y el esquema oficial del CSV. |
| `src/etl/discovery.py` | Encuentra logs, valida fechas en sus nombres y los ordena cronológicamente. |
| `src/etl/log_reader.py` | Lee texto UTF-8 y agrupa líneas por `operation_Id`, incluidas continuaciones multilínea. |
| `src/etl/pipeline.py` | Coordina lectura, transformación y almacenamiento para cada archivo. |
| `src/etl/storage.py` | Valida el CSV, deduplica registros, bloquea escritores y realiza el reemplazo atómico. |
| `src/etl/processors/base.py` | Define la interfaz que toda acción debe implementar. |
| `src/etl/processors/registry.py` | Contiene los procesadores disponibles y selecciona el que reconoce cada operación. |
| `src/etl/processors/evidence.py` | Interpreta respuestas `SearchUser` y normaliza acentos, mayúsculas y espacios. |
| `src/etl/processors/admanager.py` | Procesa `/users_admin/resetuser` y construye la fila de ADManager. |
| `src/etl/processors/results.py` | Traduce los casos de reseteo a mensajes humanos. |
| `src/etl/processors/sap.py` | Procesa `/v2/sap/register_user` y construye la fila de SAP. |
| `src/etl/processors/sap_evidence.py` | Extrae el mensaje de SAP y detecta creación y cierre del ticket. |
| `src/etl/processors/sap_results.py` | Clasifica los casos 200, 202, 208, 400, 401, 403, 404, 500 y 503. |

## Archivos de soporte

| Archivo o carpeta | Uso |
| --- | --- |
| `pyproject.toml` | Metadatos, dependencias, comando `etl`, configuración de pytest y Ruff. |
| `uv.lock` | Versiones y hashes reproducibles de las dependencias. |
| `.python-version` | Versión de Python esperada por uv. |
| `.gitignore` | Impide versionar logs, CSV, entornos, cachés y secretos locales. |
| `.gitattributes` | Normaliza finales de línea para trabajar en Windows y Linux. |
| `.github/workflows/quality.yml` | Ejecuta instalación, Ruff y pruebas en Linux con cada push o pull request. |
| `data/input/.gitkeep` | Conserva vacía la carpeta donde se colocan logs privados. |
| `data/output/.gitkeep` | Conserva vacía la carpeta donde se genera el CSV privado. |
| `tests/` | Casos sintéticos, integración, idempotencia, concurrencia y errores. |

## Comandos utilizados

La instalación reproduce exactamente el entorno fijado en `uv.lock`:

```bash
uv sync --locked
```

El proyecto instala un comando llamado `etl`. Internamente apunta a
`etl.cli:main`, de modo que estas dos entradas son equivalentes:

```bash
uv run etl --all
uv run python -m etl --all
```

Formas de seleccionar la entrada:

```bash
# Log más reciente de data/input
uv run etl

# Una fecha concreta
uv run etl --date 2026-09-01

# Todos los logs válidos, en orden
uv run etl --all

# Archivo y salida explícitos
uv run etl --log-file /ruta/eventos.log --csv-path /ruta/reporte.csv

# Directorio diferente
uv run etl --input-dir /ruta/logs --all
```

La CLI devuelve `0` cuando termina correctamente y un valor distinto de cero si
faltan archivos, la fecha es inválida, el CSV no cumple el esquema o ocurre un
error controlado.
