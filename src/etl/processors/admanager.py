"""Procesador de la accion 'resetuser' sobre el sistema 'ADManager'."""

import re
from urllib.parse import parse_qs, urlparse

from .base import BaseActionProcessor
from .evidence import UserInfo, extract_evidence, normalize
from .results import resolve_result


class ADManagerResetUserProcessor(BaseActionProcessor):
    """Procesador para la accion 'resetuser' sobre el sistema 'ADManager'."""

    @property
    def action_name(self) -> str:
        return "resetuser"

    @property
    def system_name(self) -> str:
        return "ADManager"

    def matches(self, initial_message: str) -> bool:
        return re.search(r"(?:^|/)users_admin/resetuser(?:[?\s\"]|$)", initial_message) is not None

    def process_operation(self, op_id: str, lines: list) -> dict | None:
        initial_event = self._find_initial_event(lines)
        if not initial_event:
            return None

        # 1. Parseo de URL y Querystring inicial
        solicitante, target, http_status = self._parse_request(initial_event["message"])
        timestamp = initial_event["timestamp"]

        # 2. Extraccion de informacion de usuarios (SearchUser en ADManager)
        evidence = extract_evidence(lines)

        # 3. Determinacion precisa de 'resultado final'
        resultado_final = resolve_result(http_status, solicitante, target, evidence)

        # 4. Asignacion de nombres y oficinas
        req_info = evidence.users.get(normalize(solicitante), UserInfo())
        tgt_info = evidence.users.get(normalize(target), UserInfo())

        return {
            "id": op_id,
            "timestamp": timestamp,
            "solicitante": solicitante,
            "target": target,
            "acción": self.action_name,
            "sistema": self.system_name,
            "nombre completo del usuario solicitante": req_info.full_name,
            "nombre completo del usuario target": tgt_info.full_name,
            "oficina del usuario solicitante": req_info.office,
            "oficina del usuario target": tgt_info.office,
            "resultado final": resultado_final,
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
        url_str = (
            url_match.group(0)
            if url_match
            else next((part for part in msg.split() if part.startswith("/")), msg)
        )
        parsed_url = urlparse(url_str)
        query_params = parse_qs(parsed_url.query)

        solicitante = query_params.get("sAMAccountName_requester", [""])[0]
        target = query_params.get("sAMAccountName_target", [""])[0]

        # Codigo de estado HTTP de la peticion del cliente
        http_code_match = re.search(r'"HTTP/[0-9\.]+"\s*(\d{3})', msg)
        if not http_code_match:
            http_code_match = re.search(r"\s(\d{3})$", msg.strip())
        http_status = int(http_code_match.group(1)) if http_code_match else None

        return solicitante, target, http_status
