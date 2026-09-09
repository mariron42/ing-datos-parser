"""Extracción de evidencia de SAP y del ticket de control."""

import ast
import json
import logging
import re
from dataclasses import dataclass, field

from .evidence import messages, normalize

logger = logging.getLogger(__name__)


@dataclass
class SAPEvidence:
    """Hechos observables durante una operación de alta SAP."""

    sap_messages: list[str] = field(default_factory=list)
    ticket_created: bool = False
    ticket_closed: bool = False
    normalized_log: str = ""


def _response_code(message: str) -> int | None:
    match = re.search(r'"HTTP/[0-9.]+\s+(\d{3})', message)
    return int(match[1]) if match else None


def _successful_http_event(message: str, method: str, path_pattern: str) -> bool:
    if not re.search(rf"HTTP Request:\s*{method}\s+\S*{path_pattern}", message, re.I):
        return False
    code = _response_code(message)
    return code is not None and 200 <= code < 300


def _find_sap_messages(message: str) -> list[str]:
    if "SAP raw response:" not in message:
        return []
    raw = message.split("SAP raw response:", 1)[1].strip()
    try:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = ast.literal_eval(raw)
    except (ValueError, SyntaxError, TypeError):
        logger.warning("Respuesta de SAP no interpretable")
        return []

    found = []
    pending = [data]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                if normalize(str(key)) == "mensaje" and isinstance(child, str):
                    found.append(child)
                elif isinstance(child, (dict, list)):
                    pending.append(child)
        elif isinstance(value, list):
            pending.extend(value)
    return found


def extract_sap_evidence(lines: list[dict]) -> SAPEvidence:
    """Extrae respuestas de SAP y el ciclo de vida del ticket de control."""
    operation_messages = messages(lines)
    evidence = SAPEvidence(
        normalized_log="\n".join(normalize(message) for message in operation_messages)
    )
    for message in operation_messages:
        evidence.sap_messages.extend(_find_sap_messages(message))
        if _successful_http_event(message, "POST", r"/proactivanet/api/incidents(?:[?\s\"]|$)"):
            evidence.ticket_created = True
        if _successful_http_event(message, "PUT", r"/proactivanet/api/incidents/\S+/close"):
            evidence.ticket_closed = True
    return evidence
