"""Pruebas de las reglas de negocio del alta SAP V2."""

import json

import pytest

from etl import LogReader, SAPRegisterUserProcessor

PREFIX = "2026-08-25T10:00:00Z | INFO [operation_Id=abc123] | "


def search(attribute, value, found=True, **fields):
    user = {
        "SAM_ACCOUNT_NAME": value if attribute == "sAMAccountName" else "target-account",
        "EMPLOYEE_ID": value if attribute == "employeeID" else "-",
        "FIRST_NAME": "Nombre",
        "LAST_NAME": "Prueba",
        "DESCRIPTION": "Administrador de Sistemas",
        "OFFICE": "0010",
    }
    user.update(fields)
    return f"SearchUser: {{'filter': '({attribute}:equal:{value})'}}, Raw Response: " + json.dumps(
        {"UsersList": [user] if found else []}, ensure_ascii=False
    )


def process(
    tmp_path,
    status,
    *messages,
    requester="admin10",
    target="100010",
    treatment="señor",
    job="Cajero",
):
    request = (
        "GET http://bot/v2/sap/register_user"
        f"?requester_username={requester}&target_employee_id={target}"
        f'&treatment={treatment}&job={job} "HTTP/1.1" {status}'
    )
    path = tmp_path / "sap.log"
    path.write_text(
        "".join(PREFIX + message + "\n" for message in ("Inicio", request, *messages)),
        encoding="utf-8",
    )
    lines = LogReader(str(path)).read_operations()["abc123"]
    return SAPRegisterUserProcessor().process_operation("abc123", lines)


def ad_users(requester="admin10", target="100010", **target_fields):
    return (
        search("sAMAccountName", requester),
        search("employeeID", target, **target_fields),
    )


def test_builds_complete_sap_record(tmp_path):
    record = process(tmp_path, 200, *ad_users())

    assert record == {
        "id": "abc123",
        "timestamp": "2026-08-25T10:00:00Z",
        "solicitante": "admin10",
        "target": "100010",
        "acción": "register_user",
        "sistema": "SAP",
        "nombre completo del usuario solicitante": "Nombre Prueba",
        "nombre completo del usuario target": "Nombre Prueba",
        "oficina del usuario solicitante": "0010",
        "oficina del usuario target": "0010",
        "resultado final": (
            "El usuario objetivo fue registrado exitosamente, se creó el ticket de control "
            "y se cerró."
        ),
    }


@pytest.mark.parametrize(
    "messages,expected",
    [
        (
            ('HTTP Request: POST https://tickets/proactivanet/api/incidents "HTTP/1.1 200 OK"',),
            "se creó el ticket de control pero no pudo cerrarse",
        ),
        ((), "no fue posible crear el ticket de control"),
    ],
)
def test_accepted_distinguishes_ticket_creation(tmp_path, messages, expected):
    assert expected in process(tmp_path, 202, *messages)["resultado final"]


def test_failed_ticket_request_does_not_count_as_created(tmp_path):
    failed = 'HTTP Request: POST https://tickets/proactivanet/api/incidents "HTTP/1.1 503 Error"'
    assert "no fue posible crear" in process(tmp_path, 202, failed)["resultado final"]


def test_already_exists_requires_sap_message(tmp_path):
    message = (
        "SAP raw response: "
        "{'MT_RespAltaUsrResetPwd': {'Estatus': 'E', "
        "'Mensaje': 'El usuario YA EXISTE en el sistema.'}}"
    )
    assert process(tmp_path, 208, message)["resultado final"] == (
        "El usuario objetivo ya existe en el ambiente ECC ECP de SAP."
    )


@pytest.mark.parametrize(
    "kwargs,messages,expected",
    [
        ({"target": "ABC10"}, (), "número de empleado"),
        ({"treatment": "persona"}, (), "tratamiento"),
        ({}, ("El puesto solicitado no existe en el catálogo",), "puesto solicitado no existe"),
        ({}, (), "razón desconocida"),
    ],
)
def test_bad_request_cases(tmp_path, kwargs, messages, expected):
    assert expected in process(tmp_path, 400, *messages, **kwargs)["resultado final"].casefold()


def test_unauthorized_requester_uses_description(tmp_path):
    users = (
        search("sAMAccountName", "admin10", DESCRIPTION="Auxiliar"),
        search("employeeID", "100010"),
    )
    assert process(tmp_path, 401, *users)["resultado final"] == (
        "El usuario solicitante no es gerente ni administrador de sistemas."
    )


@pytest.mark.parametrize(
    "users,job,extra,expected",
    [
        (
            ad_users()[0:1] + (search("employeeID", "100010", OFFICE="0010"),),
            "Cajero",
            (),
            "pertenece a OAT",
        ),
        (
            (
                search("sAMAccountName", "admin10", OFFICE="0010"),
                search("employeeID", "100010", OFFICE="0020"),
            ),
            "Cajero",
            (),
            "misma oficina",
        ),
        (
            ad_users(),
            "Cajero",
            ("Los usuarios no pertenecen a la misma oficina según la validación del endpoint",),
            "misma oficina",
        ),
        (
            ad_users(),
            "Puesto exclusivo",
            ("El solicitante no pertenece a City Club y pidió un puesto exclusivo de City Club",),
            "Conflicto con el puesto solicitado",
        ),
        (
            ad_users(DESCRIPTION="Subgerente"),
            "Gerente Tienda",
            (),
            "Conflicto con el puesto solicitado",
        ),
    ],
)
def test_forbidden_cases(tmp_path, users, job, extra, expected):
    if "OAT" in expected:
        users = (
            search("sAMAccountName", "admin10", OFFICE=" Corpórativo "),
            users[1],
        )
    assert expected in process(tmp_path, 403, *users, *extra, job=job)["resultado final"]


@pytest.mark.parametrize(
    "requester_found,target_found,expected",
    [
        (False, True, "usuario solicitante"),
        (True, False, "usuario objetivo"),
    ],
)
def test_not_found_cases(tmp_path, requester_found, target_found, expected):
    messages = (
        search("employeeID", "100010", target_found),
        search("sAMAccountName", "admin10", requester_found),
    )
    assert expected in process(tmp_path, 404, *messages)["resultado final"]


@pytest.mark.parametrize(
    "status,expected",
    [
        (500, "error desconocido"),
        (503, "servicio de SAP falló"),
        (418, "información disponible"),
    ],
)
def test_terminal_statuses(tmp_path, status, expected):
    assert expected in process(tmp_path, status)["resultado final"]


def test_endpoint_match_is_specific():
    processor = SAPRegisterUserProcessor()
    assert processor.matches("GET /v2/sap/register_user?target_employee_id=1")
    assert not processor.matches("GET /v2/sap/register_user_backup?target_employee_id=1")
