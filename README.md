# Ingeniería de Datos: ETL de ADManager

Proceso de terminal para transformar logs diarios del bot en un reporte CSV de
reseteos de usuarios de ADManager. Implementa las partes 1 y 2 de la tarea:
modularización, carga incremental idempotente, reglas de negocio y dependencias
reproducibles. No utiliza notebooks para ejecutar el proceso.

## Instalación y ejecución en Linux

Instalar [uv](https://docs.astral.sh/uv/getting-started/installation/) y ejecutar:

```bash
git clone git@github.com:mariron42/ing-datos-parser.git
cd ing-datos-parser
uv sync --locked
```

`uv` utiliza Python 3.12 según `.python-version`. Copiar los logs proporcionados
por separado a `data/input/`, con nombres `YYYY-MM-DD.log` (también se aceptan
nombres que contengan una fecha válida). Los datos no se distribuyen en Git.

```bash
# Procesar el log con la fecha más reciente
uv run etl

# Reprocesar una fecha o cargar todos los días cronológicamente
uv run etl --date 2026-09-01
uv run etl --all

# Rutas explícitas
uv run etl --input-dir /ruta/logs --all --csv-path /ruta/reportes/bot.csv
uv run etl --log-file /ruta/archivo.log --csv-path data/output/bot.csv

# Entrada equivalente
uv run python -m etl --all
```

Las rutas relativas parten del directorio de ejecución. El destino predeterminado
es `data/output/tabla_reporte_bot.csv`. Sin archivos válidos o ante un error se
retorna un código distinto de cero. La selección diaria ignora archivos sin fecha
válida; `--log-file` permite elegirlos explícitamente.

Para ejecución diaria, un programador externo debe invocar el comando desde la
raíz del proyecto. Ejemplo de crontab (ajustar rutas y hora):

```cron
0 7 * * * cd /ruta/ing-datos-parser && /ruta/uv run etl >> /ruta/etl.log 2>&1
```

## Diseño

- `src/etl/log_reader.py`: agrupa eventos por `operation_Id`.
- `src/etl/discovery.py`: selecciona archivos por fecha.
- `src/etl/processors/evidence.py`: interpreta búsquedas y respuestas de ADManager.
- `src/etl/processors/results.py`: aplica las reglas de resultado de la parte 2.
- `src/etl/processors/admanager.py`: construye el registro de reseteo.
- `src/etl/processors/registry.py`: registra estrategias para nuevas acciones.
- `src/etl/storage.py`: valida el esquema, deduplica y escribe de forma atómica,
  con bloqueo entre procesos.
- `src/etl/pipeline.py` y `cli.py`: orquestación y parámetros de terminal.

Para agregar acciones, implementar `BaseActionProcessor`, registrarlo en
`build_default_registry` y habilitarlo en la configuración del pipeline. No se
necesita modificar el lector ni el almacenamiento. Si se crean notebooks de
exploración, deben ir en `notebooks/`.

## Reglas del reporte

El esquema conserva `id`, las diez columnas de la primera parte y `updated_at`.
`id` corresponde a `operation_Id`; `updated_at` registra la primera carga en UTC.
La columna `resultado final` expresa la causa humana, sin agregar códigos HTTP:

| Respuesta de nuestra API | Interpretación |
| --- | --- |
| 200 | Reseteo exitoso, según el contrato de la API. |
| 202 | Usuario objetivo de Corporativo; requiere autoservicio. |
| 403 | Oficinas distintas, rol no permitido o OU restringida. Se enumeran las causas respaldadas por los campos. |
| 404 | Solicitante, objetivo o ambos ausentes; se usa el filtro de cada búsqueda vacía. |
| 429 | Tokens agotados. |
| 500 | Error crítico que requiere revisión técnica. |
| 503 | Error de ADManager, incluyendo literalmente su `statusMessage`. |
| 504 | Tiempo de espera de 35 segundos superado. |

Las comparaciones normalizan acentos, mayúsculas y espacios. Se conservan los
valores originales de nombres y oficinas. Si una respuesta falta o no se puede
interpretar, se registra una advertencia y se explica la incertidumbre: ausencia
de evidencia no equivale a usuario inexistente. Los mensajes originales de
ADManager se preservan incluso si contienen números propios del sistema.

## Idempotencia y migración

Reejecutar los mismos logs no modifica el CSV ni `updated_at`: solo se insertan
identificadores nuevos, ordenados por timestamp. No se actualizan filas existentes,
tal como exige la primera parte. El bloqueo puede dejar un archivo auxiliar
`*.lock.tmp`, ignorado por Git; no debe borrarse mientras haya escritores activos.

Para cambiar del reporte de la parte 1 al de la parte 2, guardar el reporte anterior
fuera de Git y ejecutar `--all` con un destino nuevo. Reprocesar sobre el CSV viejo
conservaría sus mensajes. Las operaciones deben estar completas dentro de cada
log diario; no se reconstruyen operaciones repartidas entre varios archivos.

## Calidad y contribución

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Las pruebas usan entradas sintéticas construidas en código; no requieren los datos
del curso. GitHub Actions ejecuta estas verificaciones en Linux. Para modificar
dependencias, usar `uv add` / `uv add --dev` y versionar `pyproject.toml` y `uv.lock`.
La configuración sigue la [guía de proyectos de uv](https://docs.astral.sh/uv/guides/projects/).

Usar commits semánticos: `feat:`, `fix:`, `test:`, `docs:`, `chore:` o `refactor:`.
Los logs, CSV, entornos, credenciales, cachés y contenido de `data/` están ignorados;
solo se versionan los `.gitkeep` de las carpetas de entrada y salida.
