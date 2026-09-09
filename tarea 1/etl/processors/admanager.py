"""Procesador de la accion 'resetuser' sobre el sistema 'ADManager'."""

import ast
import json
import re
from urllib.parse import parse_qs, urlparse

from .base import BaseActionProcessor

# Mensajes de 'resultado final' inferidos del codigo HTTP cuando la operacion
# fallo antes de que ADManager respondiera con un body estructurado.
HTTP_STATUS_MESSAGES = {
    200: "Password reset successful.",
    404: "Error 404: Target user not found in ADManager",
    403: "Error 403: Forbidden (Requester not authorized / Office mismatch)",
    500: "Error 500: Internal Server Error",
    503: "Error 503: Service Unavailable",
    504: "Error 504: Gateway Timeout",
}

EMPTY_USER_INFO = {"full_name": "", "office": ""}


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
        initial_event = self._find_initial_event(lines)
        if not initial_event:
            return None

        # 1. Parseo de URL y Querystring inicial
        solicitante, target, http_status = self._parse_request(initial_event["message"])
        timestamp = initial_event["timestamp"]

        # 2. Extraccion de informacion de usuarios (SearchUser en ADManager)
        users_info = self._extract_users_info(lines)

        # 3. Determinacion precisa de 'resultado final'
        resultado_final = self._resolve_result(lines, http_status)

        # 4. Asignacion de nombres y oficinas
        req_info = users_info.get(solicitante.lower(), EMPTY_USER_INFO)
        tgt_info = users_info.get(target.lower(), EMPTY_USER_INFO)

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

    # --------------------------------------------------------------------------
    # Etapas internas
    # --------------------------------------------------------------------------

    def _find_initial_event(self, lines: list) -> dict | None:
        """Localiza la peticion inicial que dispara la operacion."""
        for item in lines:
            if self.matches(item["message"]):
                return item
        return None

    @staticmethod
    def _parse_request(msg: str) -> tuple[str, str, int | None]:
        """Extrae (solicitante, target, codigo HTTP) de la peticion inicial."""
        url_match = re.search(r"https?://[^\s\"]+", msg)
        url_str = url_match.group(0) if url_match else msg
        parsed_url = urlparse(url_str)
        query_params = parse_qs(parsed_url.query)

        solicitante = query_params.get("sAMAccountName_requester", [""])[0]
        target = query_params.get("sAMAccountName_target", [""])[0]

        # Codigo de estado HTTP de la peticion del cliente
        http_code_match = re.search(r'"HTTP/[0-9\.]+"\s*(\d{3})', msg)
        if not http_code_match:
            http_code_match = re.search(r'\s(\d{3})$', msg.strip())
        http_status = int(http_code_match.group(1)) if http_code_match else None

        return solicitante, target, http_status

    @staticmethod
    def _extract_users_info(lines: list) -> dict:
        """Construye un indice {sAMAccountName|employee_id: {full_name, office}}."""
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

        return users_info

    @staticmethod
    def _resolve_result(lines: list, http_status: int | None) -> str:
        """Determina el 'resultado final' de la operacion."""
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

        if resultado_final:
            return resultado_final

        # Caso C: La operacion fallo antes de llamar a ResetPwd de ADManager
        if http_status in HTTP_STATUS_MESSAGES:
            return HTTP_STATUS_MESSAGES[http_status]

        return f"Error: HTTP {http_status}" if http_status else "Desconocido"
