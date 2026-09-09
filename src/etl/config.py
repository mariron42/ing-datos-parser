"""Configuracion central: rutas base y esquema de columnas del reporte."""

import os

# Rutas relativas al directorio desde el que se ejecuta la CLI.
BASE_DIR = os.path.join("data", "input")
DEFAULT_CSV_PATH = os.path.join("data", "output", "tabla_reporte_bot.csv")

# Esquema conservado de la primera parte: incluye id y fecha de carga.
CSV_HEADER = [
    "id",
    "timestamp",
    "solicitante",
    "target",
    "acción",
    "sistema",
    "nombre completo del usuario solicitante",
    "nombre completo del usuario target",
    "oficina del usuario solicitante",
    "oficina del usuario target",
    "resultado final",
    "updated_at",
]
