"""Registro extensible de procesadores de acciones."""

from .admanager import ADManagerResetUserProcessor
from .base import BaseActionProcessor
from .sap import SAPRegisterUserProcessor


class ActionRegistry:
    """Registro extensible de procesadores de acciones.

    Permite habilitar o deshabilitar procesadores en el futuro (ej. registrar SAP
    sin alterar el motor central de lectura y almacenamiento).
    """

    def __init__(self):
        self._processors = []

    def register(self, processor: BaseActionProcessor):
        self._processors.append(processor)

    def process_operations(
        self, operations: dict, enabled_actions: list[str] | None = None
    ) -> list[dict]:
        records = []
        for op_id, lines in operations.items():
            if not lines:
                continue

            for processor in self._processors:
                if enabled_actions is not None and processor.action_name not in enabled_actions:
                    continue

                if any(processor.matches(line["message"]) for line in lines):
                    record = processor.process_operation(op_id, lines)
                    if record:
                        records.append(record)
                    break

        return records


def build_default_registry() -> ActionRegistry:
    """Construye el registro con los procesadores activos de la tarea.

    Punto unico de extension: registrar aqui nuevos sistemas/acciones.
    """
    registry = ActionRegistry()
    registry.register(ADManagerResetUserProcessor())
    registry.register(SAPRegisterUserProcessor())
    return registry
