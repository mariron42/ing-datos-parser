"""Extrae evidencia de ADManager sin inferir reglas de negocio."""

import ast
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def normalize(value: str) -> str:
    """Normaliza comparaciones, conservando los originales en el reporte."""
    return " ".join(
        "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
        .casefold()
        .split()
    )


@dataclass(frozen=True)
class UserInfo:
    full_name: str = ""
    office: str = ""
    description: str = ""
    ou: str = ""


@dataclass
class Evidence:
    users: dict[str, UserInfo] = field(default_factory=dict)
    missing: set[str] = field(default_factory=set)
    reset_messages: list[str] = field(default_factory=list)


def messages(lines: list[dict]) -> list[str]:
    """Une las continuaciones multilinea a su evento anterior."""
    result = []
    for line in lines:
        if line["timestamp"] is None and result:
            result[-1] += "\n" + line["message"]
        else:
            result.append(line["message"])
    return result


def extract_evidence(lines: list[dict]) -> Evidence:
    evidence = Evidence()
    for message in messages(lines):
        if "SearchUser" in message and "Raw Response:" in message:
            query, raw = message.split("Raw Response:", 1)
            try:
                data, _ = json.JSONDecoder().raw_decode(raw.strip())
                if not isinstance(data, dict) or not isinstance(data.get("UsersList"), list):
                    raise ValueError("UsersList ausente o invalido")
                users = data["UsersList"]
                # Los logs identifican explicitamente el usuario buscado en filter.
                match = re.search(
                    r"\((?:sAMAccountName|EMPLOYEE_ID)(?::equal:|=)([^)]+)\)", query, re.I
                )
                searched = normalize(match[1]) if match else None
                if not users and searched:
                    evidence.missing.add(searched)
                for user in users:
                    if not isinstance(user, dict):
                        raise ValueError("Usuario invalido")
                    info = UserInfo(
                        full_name=" ".join(
                            str(user.get(k) or "").strip() for k in ("FIRST_NAME", "LAST_NAME")
                        ).strip(),
                        office=str(user.get("OFFICE") or "").strip(),
                        description=str(user.get("DESCRIPTION") or "").strip(),
                        ou=str(user.get("OU_NAME") or "").strip(),
                    )
                    for key in ("SAM_ACCOUNT_NAME", "sAMAccountName", "EMPLOYEE_ID"):
                        value = str(user.get(key) or "").strip()
                        if value and value not in ("-", "<not set>"):
                            evidence.users[normalize(value)] = info
            except (ValueError, TypeError):
                logger.warning("Respuesta SearchUser no interpretable; evidencia incompleta")
        if "ADM-Raw response" in message and "body:" in message:
            raw = message.split("body:", 1)[1].strip()
            try:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = ast.literal_eval(raw)
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    if isinstance(entry, dict) and isinstance(entry.get("statusMessage"), str):
                        evidence.reset_messages.append(entry["statusMessage"])
            except (ValueError, SyntaxError, TypeError):
                logger.warning("Respuesta de reseteo no interpretable")
    return evidence
