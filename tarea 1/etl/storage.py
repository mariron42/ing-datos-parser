"""Almacenamiento idempotente del reporte en CSV."""

import csv
import os
from datetime import datetime, timezone

from .config import CSV_HEADER, DEFAULT_CSV_PATH


class CSVStorageManager:
    """Gestiona el almacenamiento idempotente en tabla_reporte_bot.csv.

    Asegura:
    1. Que el CSV contenga exclusivamente las columnas requeridas por el PDF.
    2. Idempotencia estricta: reejecuciones no alteran ni duplican datos existentes.
    3. Conservacion del orden cronologico de registros por timestamp.
    """

    def __init__(self, csv_path: str = DEFAULT_CSV_PATH):
        self.csv_path = csv_path

    @staticmethod
    def _make_key(record: dict) -> tuple | str:
        """Clave primaria para deduplicacion e idempotencia."""
        op_id = record.get("id", "").strip()
        if op_id:
            return op_id.lower()
        return (
            record.get("timestamp", "").strip(),
            record.get("solicitante", "").strip().lower(),
            record.get("target", "").strip().lower(),
            record.get("acción", "").strip().lower()
        )

    def load_existing_records(self) -> tuple[set, list[dict]]:
        """Carga los registros previos del CSV y retorna (claves_existentes, filas_existentes)."""
        existing_keys = set()
        existing_rows = []

        if os.path.exists(self.csv_path):
            with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = self._make_key(row)
                    if key:
                        existing_keys.add(key)
                        filtered_row = {col: row.get(col, "") for col in CSV_HEADER}
                        existing_rows.append(filtered_row)

        return existing_keys, existing_rows

    def save_records(self, new_records: list[dict]) -> int:
        """Guarda nuevos registros en el CSV de forma estrictamente idempotente.

        Retorna la cantidad de nuevos registros anadidos.
        """
        existing_keys, all_rows = self.load_existing_records()
        initial_count = len(all_rows)
        now_utc = datetime.now(timezone.utc).isoformat()

        for record in new_records:
            key = self._make_key(record)
            if key not in existing_keys:
                clean_row = {col: record.get(col, "") for col in CSV_HEADER}
                if not clean_row.get("updated_at"):
                    clean_row["updated_at"] = now_utc
                all_rows.append(clean_row)
                existing_keys.add(key)

        inserted_count = len(all_rows) - initial_count

        # Si se insertaron nuevos registros, ordenamos cronologicamente y reescribimos atomicamente
        if inserted_count > 0 or not os.path.exists(self.csv_path):
            # Ordenar por timestamp
            all_rows.sort(key=lambda r: r.get("timestamp", ""))
            self._write_atomic(all_rows)

        return inserted_count

    def _write_atomic(self, rows: list[dict]) -> None:
        """Escritura atomica para evitar corrupcion en caso de terminacion abrupta."""
        temp_path = self.csv_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            writer.writerows(rows)

        os.replace(temp_path, self.csv_path)
