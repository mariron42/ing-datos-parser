"""Reglas de resultado para el endpoint de alta SAP V2."""

import re

from .evidence import Evidence, normalize
from .sap_evidence import SAPEvidence


def _job_conflict(job: str, target_description: str, log_text: str) -> bool:
    conflict_patterns = (
        "conflicto con el puesto solicitado",
        "puesto exclusivo de city club",
        "puesto exclusivo de soriana",
        "no se puede asignar el puesto",
    )
    if any(pattern in log_text for pattern in conflict_patterns):
        return True
    normalized_job = normalize(job)
    return (
        (normalized_job == "gerente" or normalized_job.startswith("gerente "))
        and bool(target_description)
        and not normalize(target_description).startswith("gerente")
    )


def _missing_user_result(requester: str, target: str, ad: Evidence) -> str:
    requester_missing = normalize(requester) in ad.missing
    target_missing = normalize(target) in ad.missing
    if requester_missing and target_missing:
        return "No existen el usuario solicitante ni el usuario objetivo en ADManager."
    if requester_missing:
        return "No existe el usuario solicitante en ADManager."
    if target_missing:
        return "No existe el usuario objetivo en ADManager."
    return "No existe uno de los usuarios en ADManager; los logs no permiten identificar cuál."


def resolve_sap_result(
    status: int | None,
    requester: str,
    target: str,
    treatment: str,
    job: str,
    ad: Evidence,
    sap: SAPEvidence,
) -> str:
    """Identifica el caso del código usando la evidencia disponible en los logs."""
    requester_info = ad.users.get(normalize(requester))
    target_info = ad.users.get(normalize(target))

    if status == 200:
        return (
            "El usuario objetivo fue registrado exitosamente, se creó el ticket de control "
            "y se cerró."
        )
    if status == 202:
        if sap.ticket_created:
            return (
                "El usuario objetivo fue registrado exitosamente, se creó el ticket de control "
                "pero no pudo cerrarse."
            )
        return (
            "El usuario objetivo fue registrado exitosamente, pero no fue posible crear "
            "el ticket de control."
        )
    if status == 208:
        if any("ya existe" in normalize(message) for message in sap.sap_messages):
            return "El usuario objetivo ya existe en el ambiente ECC ECP de SAP."
        return (
            "SAP indicó que el alta ya había sido procesada, pero su respuesta no contiene "
            "la evidencia esperada «ya existe»."
        )
    if status == 400:
        if not re.fullmatch(r"[0-9]+", target.strip()):
            return "El número de empleado debe contener únicamente dígitos."
        if normalize(treatment) not in {"senor", "senora"}:
            return "El tratamiento debe ser «señor» o «señora»."
        invalid_job_patterns = (
            "puesto solicitado no existe",
            "puesto no existe",
            "no existe el puesto",
            "puesto invalido",
            "puesto no valido",
        )
        if any(pattern in sap.normalized_log for pattern in invalid_job_patterns):
            return "El puesto solicitado no existe."
        return (
            "Las validaciones fueron exitosas y SAP estaba disponible, pero el alta no pudo "
            "ejecutarse por una razón desconocida."
        )
    if status == 401:
        if requester_info and normalize(requester_info.description).startswith(
            ("gerente", "admin")
        ):
            return (
                "La API rechazó la autorización, aunque DESCRIPTION identifica al solicitante "
                "como gerente o administrador de sistemas; requiere revisión."
            )
        return "El usuario solicitante no es gerente ni administrador de sistemas."
    if status == 403:
        if requester_info and normalize(requester_info.office) == "corporativo":
            return "El usuario solicitante pertenece a OAT y no puede ejecutar el alta SAP."
        if (
            requester_info
            and target_info
            and requester_info.office
            and target_info.office
            and normalize(requester_info.office) != normalize(target_info.office)
        ) or "no pertenecen a la misma oficina" in sap.normalized_log:
            return "Los usuarios no pertenecen a la misma oficina."
        if _job_conflict(job, target_info.description if target_info else "", sap.normalized_log):
            return "Conflicto con el puesto solicitado."
        return "Alta SAP no autorizada; los logs no permiten determinar la causa específica."
    if status == 404:
        return _missing_user_result(requester, target, ad)
    if status == 500:
        return "Ocurrió un error desconocido durante el alta SAP."
    if status == 503:
        return "Las validaciones fueron exitosas, pero el servicio de SAP falló."
    return "No se pudo determinar el resultado del alta SAP con la información disponible."
