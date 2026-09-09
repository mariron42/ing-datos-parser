"""Interfaz de linea de comandos del proceso ETL."""

import argparse
import os

from .config import BASE_DIR, DEFAULT_CSV_PATH
from .discovery import find_log_file_by_date, get_latest_log_file, list_available_log_files
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pipeline ETL idempotente para actualizacion diaria de tabla_reporte_bot.csv"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--date",
        type=str,
        help="Fecha del log a procesar (formato YYYY-MM-DD). Permite reejecutar cualquier fecha anterior."
    )
    group.add_argument(
        "--log-file",
        type=str,
        help="Ruta directa al archivo .log especifico a procesar."
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Procesa todos los archivos .log disponibles en el directorio en orden cronologico."
    )

    parser.add_argument(
        "--csv-path",
        type=str,
        default=DEFAULT_CSV_PATH,
        help="Ruta de destino del CSV final (por defecto tabla_reporte_bot.csv)."
    )

    return parser


def resolve_target_files(args, target_dir: str) -> list[str] | None:
    """Traduce los argumentos de CLI a la lista de logs a procesar.

    Retorna None (e imprime el motivo) cuando no hay nada que procesar.
    """
    if args.all:
        target_files = list_available_log_files(target_dir)
        if not target_files:
            print(f"Error: No se encontraron archivos .log en '{target_dir}'.")
            return None
        print(f"Modo completo: Procesando {len(target_files)} archivos de log en orden cronológico.")
        return target_files

    if args.date:
        matched_file = find_log_file_by_date(target_dir, args.date)
        if not matched_file:
            print(f"Error: No se encontró ningún archivo de log para la fecha '{args.date}' en '{target_dir}'.")
            return None
        return [matched_file]

    if args.log_file:
        if not os.path.exists(args.log_file):
            print(f"Error: El archivo especificado no existe: '{args.log_file}'.")
            return None
        return [args.log_file]

    # Comportamiento diario por defecto: procesar el mas reciente
    latest_file = get_latest_log_file(target_dir)
    if not latest_file:
        print(f"Error: No se encontró ningún archivo .log en '{target_dir}'.")
        return None
    print(f"Modo diario por defecto: Seleccionado archivo más reciente ({os.path.basename(latest_file)}).")
    return [latest_file]


def main(argv: list[str] | None = None):
    args = build_parser().parse_args(argv)

    target_files = resolve_target_files(args, BASE_DIR)
    if target_files is None:
        return

    total_inserted = run_pipeline(target_files, csv_path=args.csv_path)
    print(f"\n==================================================")
    print(f"Ejecución completada exitosamente.")
    print(f"Total de registros nuevos insertados en CSV: {total_inserted}")
    print(f"Destino CSV: {args.csv_path}")
    print(f"==================================================")
