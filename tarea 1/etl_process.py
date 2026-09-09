"""Punto de entrada del proceso ETL de la Tarea 1.

La implementacion vive en el paquete `etl` (ver etl/__init__.py).
Este script se conserva como entrada estable:

    python etl_process.py --all
    python etl_process.py --date 2026-09-01

Equivalente: python -m etl --all
"""

from etl.cli import main

if __name__ == "__main__":
    main()
