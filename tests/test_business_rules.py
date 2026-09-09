"""Casos sintéticos de aceptación de la segunda parte; sin datos reales."""

import json
import subprocess
import sys

import pytest

from etl import LogReader, build_default_registry


def search(user, found=True, **fields):
    record = {"SAM_ACCOUNT_NAME": user, "DESCRIPTION": "Administrador", "OFFICE": "Tienda"}
    record.update(fields)
    return (
        f"SearchUser: {{'filter': '(sAMAccountName:equal:{user})'}}, Raw Response: "
        + json.dumps({"UsersList": [record] if found else []}, ensure_ascii=False)
    )


def process(tmp_path, status, *messages):
    request = (
        "GET http://bot/users_admin/resetuser?sAMAccountName_requester=admin"
        f'&sAMAccountName_target=target "HTTP/1.1" {status}'
    )
    path = tmp_path / "input.log"
    path.write_text(
        "".join(
            f"2026-09-01T00:00:00Z | INFO [operation_Id=abc123] | {m}\n"
            for m in ("Inicio de operación", request, *messages)
        ),
        encoding="utf-8",
    )
    records = build_default_registry().process_operations(LogReader(str(path)).read_operations())
    assert len(records) == 1  # La petición no tiene que ser la primera línea.
    return records[0]["resultado final"]


@pytest.mark.parametrize(
    "req,tgt,expected",
    [
        (False, True, "El usuario solicitante no se encontró en ADManager."),
        (True, False, "El usuario objetivo no se encontró en ADManager."),
        (False, False, "Ningún usuario se encontró en ADManager."),
    ],
)
def test_missing_users(tmp_path, req, tgt, expected):
    # Las búsquedas pueden llegar en cualquier orden.
    assert process(tmp_path, 404, search("target", tgt), search("admin", req)) == expected


@pytest.mark.parametrize(
    "requester,target,expected",
    [
        ({"OFFICE": "A"}, {"OFFICE": "B"}, "Los usuarios no pertenecen a la misma oficina."),
        (
            {"DESCRIPTION": "Cajero"},
            {},
            "El usuario solicitante no es gerente ni administrador de sistemas.",
        ),
        (
            {},
            {"OU_NAME": " oat/CÉDIS/by "},
            "El usuario objetivo pertenece a OAT/Cedis/BY y no puede ser reseteado mediante el bot.",
        ),
    ],
)
def test_forbidden_causes(tmp_path, requester, target, expected):
    assert (
        process(tmp_path, 403, search("admin", **requester), search("target", **target)) == expected
    )


@pytest.mark.parametrize("role", [" GÉRENTE de tienda ", " ÁDMINISTRADOR "])
def test_normalization_does_not_invent_forbidden_causes(tmp_path, role):
    result = process(
        tmp_path,
        403,
        search("admin", DESCRIPTION=role, OFFICE=" ÁREA Norte "),
        search("target", OFFICE="area norte"),
    )
    assert "no permiten determinar" in result


@pytest.mark.parametrize("office", ["Corporativo", "CORPORATIVO", " corpórativo "])
def test_corporate(tmp_path, office):
    assert "autoservicio" in process(tmp_path, 202, search("target", OFFICE=office))


@pytest.mark.parametrize(
    "status,fragment",
    [
        (200, "correctamente"),
        (429, "agotaron los tokens"),
        (500, "crítico"),
        (504, "35 segundos"),
    ],
)
def test_result_has_no_api_status(tmp_path, status, fragment):
    result = process(tmp_path, status)
    assert fragment in result
    assert str(status) not in result


@pytest.mark.parametrize("serialize", [json.dumps, repr])
def test_preserves_exact_admanager_error(tmp_path, serialize):
    detail = "Usuario inválido: atributo LDAP ausente. Contacte a soporte."
    body = serialize([{"statusMessage": detail, "status": "0"}])
    result = process(tmp_path, 503, "ADM-Raw response | status: 200 | body: " + body)
    assert result == "No se pudo restablecer la contraseña por un error de ADManager: " + detail


def test_multiline_json_and_missing_search(tmp_path):
    multiline = search("admin").replace('{"UsersList":', '{\n"UsersList":')
    assert (
        process(tmp_path, 404, multiline, search("target", False))
        == "El usuario objetivo no se encontró en ADManager."
    )


def test_corrupt_search_is_not_evidence_of_missing_user(tmp_path, caplog):
    result = process(tmp_path, 404, "SearchUser: {}, Raw Response: broken")
    assert "no permiten identificar" in result
    assert "evidencia incompleta" in caplog.text


def test_empty_actions_disable_processing(tmp_path):
    assert (
        build_default_registry().process_operations(
            {"abc": [{"message": "GET /users_admin/resetuser"}]}, enabled_actions=[]
        )
        == []
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ["--log-file", "missing.log"],
        ["--date", "2026-02-30"],
    ],
)
def test_cli_process_exit_code(arguments):
    result = subprocess.run([sys.executable, "-m", "etl", *arguments], capture_output=True)
    assert result.returncode != 0
