"""Reglas de resultado de la Tarea 1, Parte 2."""

from .evidence import Evidence, normalize

SUCCESS = "Contraseña restablecida correctamente."
TIMEOUT = (
    "No se pudo completar el restablecimiento: ADManager superó el tiempo de espera de 35 segundos."
)


def resolve_result(status: int | None, requester: str, target: str, evidence: Evidence) -> str:
    """Combina el estado de nuestra API con evidencia del sistema destino."""
    req_key, tgt_key = normalize(requester), normalize(target)
    req, tgt = evidence.users.get(req_key), evidence.users.get(tgt_key)
    if status == 200:
        # El contrato de nuestra API garantiza el reseteo para esta respuesta.
        return SUCCESS
    if status == 202:
        return "El usuario objetivo pertenece a Corporativo y debe restablecer su contraseña por autoservicio."
    if status == 403:
        reasons = []
        if (
            req
            and tgt
            and req.office
            and tgt.office
            and normalize(req.office) != normalize(tgt.office)
        ):
            reasons.append("Los usuarios no pertenecen a la misma oficina")
        if (
            req
            and req.description
            and not normalize(req.description).startswith(("gerente", "admin"))
        ):
            reasons.append("El usuario solicitante no es gerente ni administrador de sistemas")
        if tgt and normalize(tgt.ou) == normalize("OAT/Cedis/BY"):
            reasons.append(
                "El usuario objetivo pertenece a OAT/Cedis/BY y no puede ser reseteado mediante el bot"
            )
        return (
            "; ".join(reasons) + "."
            if reasons
            else "Restablecimiento no autorizado; los logs no permiten determinar la causa específica."
        )
    if status == 404:
        req_missing = req_key in evidence.missing and req is None
        tgt_missing = tgt_key in evidence.missing and tgt is None
        if req_missing and tgt_missing:
            return "Ningún usuario se encontró en ADManager."
        if req_missing:
            return "El usuario solicitante no se encontró en ADManager."
        if tgt_missing:
            return "El usuario objetivo no se encontró en ADManager."
        return "No se encontró al menos uno de los usuarios en ADManager; los logs no permiten identificar cuál."
    if status == 429:
        return "No se pudo restablecer la contraseña porque se agotaron los tokens de ADManager."
    if status == 500:
        return "Error crítico inesperado en el proceso; requiere revisión técnica."
    if status == 503:
        detail = (
            " | ".join(evidence.reset_messages)
            or "El mensaje de error de ADManager no está disponible en los logs."
        )
        return "No se pudo restablecer la contraseña por un error de ADManager: " + detail
    if status == 504:
        return TIMEOUT
    return "No se pudo determinar el resultado con la información disponible."
