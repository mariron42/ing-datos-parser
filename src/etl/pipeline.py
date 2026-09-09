"""Pipeline ETL principal: lectura -> procesamiento -> almacenamiento."""

import os

from .config import DEFAULT_CSV_PATH
from .log_reader import LogReader
from .processors import ActionRegistry, build_default_registry
from .storage import CSVStorageManager

# Acciones reportadas por las dos partes de la tarea.
DEFAULT_ENABLED_ACTIONS = ["resetuser", "register_user"]


def run_pipeline(
    log_files: list[str],
    csv_path: str = DEFAULT_CSV_PATH,
    enabled_actions: list[str] | None = None,
    registry: ActionRegistry | None = None,
) -> int:
    """Ejecuta el pipeline ETL para una lista de archivos de log de forma secuencial."""
    if registry is None:
        registry = build_default_registry()

    if enabled_actions is None:
        enabled_actions = DEFAULT_ENABLED_ACTIONS

    storage = CSVStorageManager(csv_path)
    total_new = 0

    for log_file in log_files:
        print(f"\n[ETL] Procesando: {os.path.basename(log_file)}")
        reader = LogReader(log_file)
        operations = reader.read_operations()
        records = registry.process_operations(operations, enabled_actions=enabled_actions)
        print(f"[ETL]   Operaciones detectadas: {len(records)}")

        inserted = storage.save_records(records)
        print(f"[ETL]   Registros nuevos insertados: {inserted}")
        total_new += inserted

    return total_new
