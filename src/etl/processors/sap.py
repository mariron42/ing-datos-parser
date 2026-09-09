"""Procesador del endpoint de alta de usuarios en SAP V2."""

import re
from urllib.parse import parse_qs, urlparse

from .base import BaseActionProcessor
from .evidence import UserInfo, extract_evidence, normalize
from .sap_evidence import extract_sap_evidence
from .sap_results import resolve_sap_result


class SAPRegisterUserProcessor(BaseActionProcessor):
    """Transforma una operación `/v2/sap/register_user` en una fila del reporte."""

    @property
    def action_name(self) -> str:
        return "register_user"

    @property
    def system_name(self) -> str:
        return "SAP"

    def matches(self, initial_message: str) -> bool:
        return re.search(r"(?:^|/)v2/sap/register_user(?:[?\s\"]|$)", initial_message) is not None

    def process_operation(self, op_id: str, lines: list[dict]) -> dict | None:
        initial_event = next((line for line in lines if self.matches(line["message"])), None)
        if not initial_event:
            return None

        requester, target, treatment, job, status = self._parse_request(initial_event["message"])
        ad_evidence = extract_evidence(lines)
        sap_evidence = extract_sap_evidence(lines)
        requester_info = ad_evidence.users.get(normalize(requester), UserInfo())
        target_info = ad_evidence.users.get(normalize(target), UserInfo())

        return {
            "id": op_id,
            "timestamp": initial_event["timestamp"],
            "solicitante": requester,
            "target": target,
            "acción": self.action_name,
            "sistema": self.system_name,
            "nombre completo del usuario solicitante": requester_info.full_name,
            "nombre completo del usuario target": target_info.full_name,
            "oficina del usuario solicitante": requester_info.office,
            "oficina del usuario target": target_info.office,
            "resultado final": resolve_sap_result(
                status,
                requester,
                target,
                treatment,
                job,
                ad_evidence,
                sap_evidence,
            ),
        }

    @staticmethod
    def _parse_request(message: str) -> tuple[str, str, str, str, int | None]:
        url_match = re.search(r"https?://[^\s\"]+", message)
        if not url_match:
            return "", "", "", "", None
        query = parse_qs(urlparse(url_match.group()).query, keep_blank_values=True)
        status_match = re.search(r'"HTTP/[0-9.]+"\s*(\d{3})', message)
        return (
            query.get("requester_username", [""])[0],
            query.get("target_employee_id", [""])[0],
            query.get("treatment", [""])[0],
            query.get("job", [""])[0],
            int(status_match[1]) if status_match else None,
        )
