"""Interfaz base del patron Strategy para el procesamiento de acciones."""

from abc import ABC, abstractmethod


class BaseActionProcessor(ABC):
    """Interfaz base para procesar distintas acciones/sistemas encontrados en los logs."""

    @property
    @abstractmethod
    def action_name(self) -> str:
        """Nombre normalizado de la accion (ej. 'resetuser', 'register_user')."""
        pass

    @property
    @abstractmethod
    def system_name(self) -> str:
        """Nombre del sistema donde se ejecuta la accion (ej. 'ADManager', 'SAP')."""
        pass

    @abstractmethod
    def matches(self, initial_message: str) -> bool:
        """Determina si la peticion inicial corresponde a esta accion."""
        pass

    @abstractmethod
    def process_operation(self, op_id: str, lines: list) -> dict | None:
        """Extrae el registro estructurado de la operacion segun el esquema de columnas."""
        pass
