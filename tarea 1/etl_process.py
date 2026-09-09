"""Proceso ETL idempotente y extensible para tabla_reporte_bot.csv.

Materia: Ingenieria de Datos - Tarea 1.
Objetivo: Procesar logs diarios de operaciones de reseteo de contrasenas
y mantener actualizada la tabla final de forma idempotente y extensible.
"""

import os
import re
import csv
import json
import ast
import argparse
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

# Archivo de salida CSV por defecto
DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "tabla_reporte_bot.csv")

# Columnas oficiales requeridas (incluyendo las 2 columnas solicitadas posteriormente: id y updated_at)
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


# ==============================================================================
# LECTURA Y AGRUPACION DE LOGS
# ==============================================================================

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


# ==============================================================================
# PATRON STRATEGY PARA PROCESAMIENTO DE ACCIONES
# ==============================================================================

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


class ADManagerResetUserProcessor(BaseActionProcessor):
    """Procesador para la accion 'resetuser' sobre el sistema 'ADManager'."""

    @property
    def action_name(self) -> str:
        return "resetuser"

    @property
    def system_name(self) -> str:
        return "ADManager"

    def matches(self, initial_message: str) -> bool:
        return "users_admin/resetuser" in initial_message

    def process_operation(self, op_id: str, lines: list) -> dict | None:
        initial_event = None
        for item in lines:
            if self.matches(item["message"]):
                initial_event = item
                break

        if not initial_event:
            return None

        # 1. Parseo de URL y Querystring inicial
        msg = initial_event["message"]
        url_match = re.search(r"https?://[^\s\"]+", msg)
        url_str = url_match.group(0) if url_match else msg
        parsed_url = urlparse(url_str)
        query_params = parse_qs(parsed_url.query)

        solicitante = query_params.get("sAMAccountName_requester", [""])[0]
        target = query_params.get("sAMAccountName_target", [""])[0]
        timestamp = initial_event["timestamp"]

        # Codigo de estado HTTP de la peticion del cliente
        http_code_match = re.search(r'"HTTP/[0-9\.]+"\s*(\d{3})', msg)
        if not http_code_match:
            http_code_match = re.search(r'\s(\d{3})$', msg.strip())
        http_status = int(http_code_match.group(1)) if http_code_match else None

        # 2. Extraccion de informacion de usuarios (SearchUser en ADManager)
        users_info = {}
        for item in lines:
            line_txt = item["full_line"]
            if "SearchUser" in line_txt and "Raw Response:" in line_txt:
                try:
                    raw_json_str = line_txt.split("Raw Response:", 1)[1].strip()
                    if ", Raw status_code:" in raw_json_str:
                        raw_json_str = raw_json_str.split(", Raw status_code:")[0].strip()

                    if not raw_json_str:
                        continue

                    data = json.loads(raw_json_str)
                    for u_data in data.get("UsersList", []):
                        sam_name = u_data.get("SAM_ACCOUNT_NAME") or u_data.get("sAMAccountName")
                        emp_id = u_data.get("EMPLOYEE_ID")
                        first_name = (u_data.get("FIRST_NAME") or "").strip()
                        last_name = (u_data.get("LAST_NAME") or "").strip()
                        full_name = f"{first_name} {last_name}".strip()
                        office = (u_data.get("OFFICE") or "").strip()

                        info = {
                            "full_name": full_name,
                            "office": office
                        }

                        if sam_name:
                            users_info[sam_name.lower()] = info
                        if emp_id and emp_id not in ("-", "<not set>"):
                            users_info[emp_id.lower()] = info
                except Exception:
                    pass

        # 3. Determinacion precisa de 'resultado final'
        resultado_final = None
        for item in lines:
            line_txt = item["full_line"]
            if "ADM-Raw response" in line_txt:
                # Caso A: Respuesta JSON con body estructurado
                if "body:" in line_txt:
                    body_str = line_txt.split("body:", 1)[1].strip()
                    try:
                        body_data = ast.literal_eval(body_str)
                        if isinstance(body_data, list) and len(body_data) > 0:
                            msg_status = body_data[0].get("statusMessage")
                            if msg_status:
                                resultado_final = msg_status
                    except Exception:
                        pass

                # Caso B: Timeout de ADManager (HTTP 504 con campo reason)
                if not resultado_final and "reason:" in line_txt:
                    reason_match = re.search(r"reason:\s*([^\|]+)", line_txt)
                    if reason_match:
                        resultado_final = reason_match.group(1).strip()

        # Caso C: La operacion fallo antes de llamar a ResetPwd de ADManager
        if not resultado_final:
            if http_status == 200:
                resultado_final = "Password reset successful."
            elif http_status == 404:
                resultado_final = "Error 404: Target user not found in ADManager"
            elif http_status == 403:
                resultado_final = "Error 403: Forbidden (Requester not authorized / Office mismatch)"
            elif http_status == 500:
                resultado_final = "Error 500: Internal Server Error"
            elif http_status == 503:
                resultado_final = "Error 503: Service Unavailable"
            elif http_status == 504:
                resultado_final = "Error 504: Gateway Timeout"
            else:
                resultado_final = f"Error: HTTP {http_status}" if http_status else "Desconocido"

        # 4. Asignacion de nombres y oficinas
        req_info = users_info.get(solicitante.lower(), {"full_name": "", "office": ""})
        tgt_info = users_info.get(target.lower(), {"full_name": "", "office": ""})

        return {
            "id": op_id,
            "timestamp": timestamp,
            "solicitante": solicitante,
            "target": target,
            "acción": self.action_name,
            "sistema": self.system_name,
            "nombre completo del usuario solicitante": req_info["full_name"],
            "nombre completo del usuario target": tgt_info["full_name"],
            "oficina del usuario solicitante": req_info["office"],
            "oficina del usuario target": tgt_info["office"],
            "resultado final": resultado_final
        }


class ActionRegistry:
    """Registro extensible de procesadores de acciones.
    
    Permite habilitar o deshabilitar procesadores en el futuro (ej. registrar SAP
    sin alterar el motor central de lectura y almacenamiento).
    """

    def __init__(self):
        self._processors = []

    def register(self, processor: BaseActionProcessor):
        self._processors.append(processor)

    def process_operations(self, operations: dict, enabled_actions: list[str] | None = None) -> list[dict]:
        records = []
        for op_id, lines in operations.items():
            if not lines:
                continue

            first_msg = lines[0]["message"]
            for processor in self._processors:
                if enabled_actions and processor.action_name not in enabled_actions:
                    continue

                if processor.matches(first_msg):
                    record = processor.process_operation(op_id, lines)
                    if record:
                        records.append(record)
                    break

        return records


# ==============================================================================
# ALMACENAMIENTO IDEMPOTENTE EN CSV
# ==============================================================================

class CSVStorageManager:
    """Gestiona el almacenamiento idempotente en tabla_reporte_bot.csv.
    
    Asegura:
    1. Que el CSV contenga exclusivamente las 10 columnas requeridas por el PDF.
    2. Idempotencia estricta: reejecuciones no alteran ni duplican datos existentes.
    3. Conservacion del orden cronologico de registros por timestamp.
    """

    def __init__(self, csv_path: str = DEFAULT_CSV_PATH):
        self.csv_path = csv_path

    @staticmethod
    def _make_key(record: dict) -> tuple | str:
        """Clave primaria para deduplicacion e idempotencia."""
        op_id = record.get("id", "").strip()
        if op_id:
            return op_id.lower()
        return (
            record.get("timestamp", "").strip(),
            record.get("solicitante", "").strip().lower(),
            record.get("target", "").strip().lower(),
            record.get("acción", "").strip().lower()
        )

    def load_existing_records(self) -> tuple[set, list[dict]]:
        """Carga los registros previos del CSV y retorna (claves_existentes, filas_existentes)."""
        existing_keys = set()
        existing_rows = []

        if os.path.exists(self.csv_path):
            with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = self._make_key(row)
                    if key:
                        existing_keys.add(key)
                        filtered_row = {col: row.get(col, "") for col in CSV_HEADER}
                        existing_rows.append(filtered_row)

        return existing_keys, existing_rows

    def save_records(self, new_records: list[dict]) -> int:
        """Guarda nuevos registros en el CSV de forma estrictamente idempotente.
        
        Retorna la cantidad de nuevos registros anadidos.
        """
        existing_keys, all_rows = self.load_existing_records()
        initial_count = len(all_rows)
        now_utc = datetime.now(timezone.utc).isoformat()

        for record in new_records:
            key = self._make_key(record)
            if key not in existing_keys:
                clean_row = {col: record.get(col, "") for col in CSV_HEADER}
                if not clean_row.get("updated_at"):
                    clean_row["updated_at"] = now_utc
                all_rows.append(clean_row)
                existing_keys.add(key)

        inserted_count = len(all_rows) - initial_count

        # Si se insertaron nuevos registros, ordenamos cronologicamente y reescribimos atomicamente
        if inserted_count > 0 or not os.path.exists(self.csv_path):
            # Ordenar por timestamp
            all_rows.sort(key=lambda r: r.get("timestamp", ""))

            # Escritura atomica para evitar corrupcion en caso de terminacion abrupta
            temp_path = self.csv_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
                writer.writeheader()
                writer.writerows(all_rows)

            os.replace(temp_path, self.csv_path)

        return inserted_count


# ==============================================================================
# DESCUBRIMIENTO Y SELECCION DE ARCHIVOS DE LOG
# ==============================================================================

def extract_date_from_filename(filename: str) -> str | None:
    """Extrae la fecha en formato YYYY-MM-DD del nombre de archivo."""
    basename = os.path.basename(filename)
    match = re.search(r"(\d{4}-\d{2}-\d{2})", basename)
    return match.group(1) if match else None


def list_available_log_files(directory: str) -> list[str]:
    """Retorna los archivos .log disponibles en el directorio ordenados por fecha."""
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".log")]
    # Ordenar por la fecha contenida en el nombre o lexicograficamente
    files.sort(key=lambda f: extract_date_from_filename(f) or os.path.basename(f))
    return files


def get_latest_log_file(directory: str) -> str | None:
    """Obtiene la ruta del archivo .log con la fecha mas reciente."""
    files = list_available_log_files(directory)
    return files[-1] if files else None


def find_log_file_by_date(directory: str, date_str: str) -> str | None:
    """Busca un archivo de log especifico para la fecha indicada (YYYY-MM-DD)."""
    expected_name = f"{date_str}.log"
    direct_path = os.path.join(directory, expected_name)
    if os.path.exists(direct_path):
        return direct_path

    # Busqueda flexible
    for log_file in list_available_log_files(directory):
        if extract_date_from_filename(log_file) == date_str:
            return log_file

    return None


# ==============================================================================
# PIPELINE ETL PRINCIPAL
# ==============================================================================

def run_pipeline(
    log_files: list[str],
    csv_path: str = DEFAULT_CSV_PATH,
    enabled_actions: list[str] | None = None
) -> int:
    """Ejecuta el pipeline ETL para una lista de archivos de log de forma secuencial."""
    registry = ActionRegistry()
    # Registro de procesadores activos
    registry.register(ADManagerResetUserProcessor())

    # Por defecto en esta tarea, solo procesamos reseteos de ADManager
    if enabled_actions is None:
        enabled_actions = ["resetuser"]

    storage = CSVStorageManager(csv_path)
    total_new = 0

    for log_file in log_files:
        print(f"\n[ETL] Procesando: {os.path.basename(log_file)}")
        reader = LogReader(log_file)
        operations = reader.read_operations()
        records = registry.process_operations(operations, enabled_actions=enabled_actions)
        print(f"[ETL]   Operaciones detectadas: {len(records)}")

        inserted = storage.save_records(records)
        print(f"[ETL]   Registros nuevos insertados: {inserted}")
        total_new += inserted

    return total_new


def main():
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

    args = parser.parse_args()
    target_dir = os.path.dirname(os.path.abspath(__file__))

    # Determinar lista de archivos a procesar
    if args.all:
        target_files = list_available_log_files(target_dir)
        if not target_files:
            print(f"Error: No se encontraron archivos .log en '{target_dir}'.")
            return
        print(f"Modo completo: Procesando {len(target_files)} archivos de log en orden cronológico.")
    elif args.date:
        matched_file = find_log_file_by_date(target_dir, args.date)
        if not matched_file:
            print(f"Error: No se encontró ningún archivo de log para la fecha '{args.date}' en '{target_dir}'.")
            return
        target_files = [matched_file]
    elif args.log_file:
        if not os.path.exists(args.log_file):
            print(f"Error: El archivo especificado no existe: '{args.log_file}'.")
            return
        target_files = [args.log_file]
    else:
        # Comportamiento diario por defecto: procesar el mas reciente
        latest_file = get_latest_log_file(target_dir)
        if not latest_file:
            print(f"Error: No se encontró ningún archivo .log en '{target_dir}'.")
            return
        print(f"Modo diario por defecto: Seleccionado archivo más reciente ({os.path.basename(latest_file)}).")
        target_files = [latest_file]

    total_inserted = run_pipeline(target_files, csv_path=args.csv_path)
    print(f"\n==================================================")
    print(f"Ejecución completada exitosamente.")
    print(f"Total de registros nuevos insertados en CSV: {total_inserted}")
    print(f"Destino CSV: {args.csv_path}")
    print(f"==================================================")


if __name__ == "__main__":
    main()
