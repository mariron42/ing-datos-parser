"""Descubrimiento y seleccion de archivos de log."""

import os
import re


def extract_date_from_filename(filename: str) -> str | None:
    """Extrae la fecha en formato YYYY-MM-DD del nombre de archivo."""
    basename = os.path.basename(filename)
    match = re.search(r"(\d{4}-\d{2}-\d{2})", basename)
    return match.group(1) if match else None


def list_available_log_files(directory: str) -> list[str]:
    """Retorna los archivos .log disponibles en el directorio ordenados por fecha."""
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".log")]
    # Ordenar por la fecha contenida en el nombre o lexicograficamente
    files.sort(key=lambda f: extract_date_from_filename(f) or os.path.basename(f))
    return files


def get_latest_log_file(directory: str) -> str | None:
    """Obtiene la ruta del archivo .log con la fecha mas reciente."""
    files = list_available_log_files(directory)
    return files[-1] if files else None


def find_log_file_by_date(directory: str, date_str: str) -> str | None:
    """Busca un archivo de log especifico para la fecha indicada (YYYY-MM-DD)."""
    expected_name = f"{date_str}.log"
    direct_path = os.path.join(directory, expected_name)
    if os.path.exists(direct_path):
        return direct_path

    # Busqueda flexible
    for log_file in list_available_log_files(directory):
        if extract_date_from_filename(log_file) == date_str:
            return log_file

    return None
