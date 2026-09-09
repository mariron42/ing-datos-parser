"""Procesadores de acciones (patron Strategy)."""

from .admanager import ADManagerResetUserProcessor
from .base import BaseActionProcessor
from .registry import ActionRegistry, build_default_registry

__all__ = [
    "BaseActionProcessor",
    "ADManagerResetUserProcessor",
    "ActionRegistry",
    "build_default_registry",
]
