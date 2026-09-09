"""Asegura que el paquete `etl` sea importable al correr pytest desde cualquier ruta."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
