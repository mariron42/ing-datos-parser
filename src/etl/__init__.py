"""Proceso ETL idempotente y extensible para tabla_reporte_bot.csv.

Materia: Ingenieria de Datos - Tarea 1.
Objetivo: Procesar logs diarios de reseteos de ADManager y altas de SAP,
y mantener actualizada la tabla final de forma idempotente y extensible.

Modulos:
    config      Rutas base y esquema de columnas del CSV.
    log_reader  Lectura de logs y agrupacion por operation_Id.
    processors  Procesadores por accion/sistema (patron Strategy) y su registro.
    storage     Escritura idempotente y atomica del CSV.
    discovery   Descubrimiento y seleccion de archivos .log.
    pipeline    Orquestacion del ETL.
    cli         Interfaz de linea de comandos.
"""

from .config import BASE_DIR, CSV_HEADER, DEFAULT_CSV_PATH
from .discovery import (
    extract_date_from_filename,
    find_log_file_by_date,
    get_latest_log_file,
    list_available_log_files,
)
from .log_reader import LogReader
from .pipeline import DEFAULT_ENABLED_ACTIONS, run_pipeline
from .processors import (
    ActionRegistry,
    ADManagerResetUserProcessor,
    BaseActionProcessor,
    SAPRegisterUserProcessor,
    build_default_registry,
)
from .storage import CSVStorageManager

__all__ = [
    "BASE_DIR",
    "CSV_HEADER",
    "DEFAULT_CSV_PATH",
    "LogReader",
    "BaseActionProcessor",
    "ADManagerResetUserProcessor",
    "SAPRegisterUserProcessor",
    "ActionRegistry",
    "build_default_registry",
    "CSVStorageManager",
    "extract_date_from_filename",
    "list_available_log_files",
    "get_latest_log_file",
    "find_log_file_by_date",
    "DEFAULT_ENABLED_ACTIONS",
    "run_pipeline",
]
