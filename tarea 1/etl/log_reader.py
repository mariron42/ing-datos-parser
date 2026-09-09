"""Lectura y agrupacion de lineas de log por operation_Id."""

import re


class LogReader:
    """Lee archivos de log y agrupa las lineas pertenecientes a cada operation_Id."""

    LINE_PATTERN = re.compile(
        r"^(\d{4}-\d{2}-\d{2}T[\d:\.]+Z)\s*\|\s*(\w+)\s*\[operation_Id=([a-f0-9]+)\]\s*\|\s*(.*)$"
    )

    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path

    def read_operations(self) -> dict:
        """Parsea el archivo y retorna un diccionario {op_id: [line_info, ...]}."""
        operations = {}
        current_op_id = None

        with open(self.log_file_path, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                line_str = raw_line.rstrip("\r\n")
                match = self.LINE_PATTERN.match(line_str)
                if match:
                    ts, level, op_id, msg = match.groups()
                    current_op_id = op_id
                    if op_id not in operations:
                        operations[op_id] = []
                    operations[op_id].append({
                        "timestamp": ts,
                        "level": level,
                        "message": msg,
                        "full_line": line_str
                    })
                elif current_op_id and line_str.strip():
                    # Lineas multilineas (p. ej. respuestas JSON o formateos extendidos)
                    operations[current_op_id].append({
                        "timestamp": None,
                        "level": None,
                        "message": line_str.strip(),
                        "full_line": line_str.strip()
                    })

        return operations
