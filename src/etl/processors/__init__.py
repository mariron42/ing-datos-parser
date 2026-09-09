"""Procesadores de acciones (patron Strategy)."""

from .admanager import ADManagerResetUserProcessor
from .base import BaseActionProcessor
from .registry import ActionRegistry, build_default_registry
from .sap import SAPRegisterUserProcessor

__all__ = [
    "BaseActionProcessor",
    "ADManagerResetUserProcessor",
    "SAPRegisterUserProcessor",
    "ActionRegistry",
    "build_default_registry",
]
