"""Configuracion central: rutas base y esquema de columnas del reporte."""

import os

# Directorio raiz de la tarea (contiene los .log y el CSV de salida).
# Se calcula subiendo un nivel desde el paquete `etl`.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Archivo de salida CSV por defecto
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "tabla_reporte_bot.csv")

# Columnas oficiales requeridas (incluyendo las 2 columnas solicitadas
# posteriormente: id y updated_at)
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
    "updated_at"
]
