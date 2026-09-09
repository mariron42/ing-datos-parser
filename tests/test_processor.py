"""Pruebas del procesador ADManager/resetuser."""

import pytest

from etl import ADManagerResetUserProcessor, LogReader

PREFIX = "2026-09-01T00:02:39.862105Z | INFO [operation_Id=abc123] | "

REQUEST = (
    "HTTP Request: http://apitools.com:8000/v3/users_admin/resetuser"
    "?sAMAccountName_requester=admsistemas520&sAMAccountName_target=520000228"
    ' "HTTP/1.1" {status}'
)

SEARCH_USER = (
    "SearchUser: {'domainName': 'retailstore.com'}, Raw Response: "
    '{"UsersList":[{"EMPLOYEE_ID":"520000228","SAM_ACCOUNT_NAME":"520000228",'
    '"FIRST_NAME":"Nombre_target","LAST_NAME":"Apellido_target","OFFICE":"Tienda 520"}]}'
)

SEARCH_REQUESTER = (
    "SearchUser: {'domainName': 'retailstore.com'}, Raw Response: "
    '{"UsersList":[{"EMPLOYEE_ID":"-","SAM_ACCOUNT_NAME":"admsistemas520",'
    '"FIRST_NAME":"Nombre_admin","LAST_NAME":"Apellido_admin","OFFICE":"Tienda 520"}]}'
)

ADM_OK = (
    "ADM-Raw response | status: 200 | body: "
    "[{'sAMAccountName': '520000228', 'status': '0', "
    "'statusMessage': 'Contraseña restablecida correctamente.'}]"
)

ADM_TIMEOUT = (
    "ADM-Raw response | status: 504 | reason: ADM timed out "
    "| timeout_type: ReadTimeout | url: https://admanager.retailstore.com/RestAPI/ResetPwd"
)


def build_operation(tmp_path, messages: list[str]) -> list[dict]:
    """Construye las lineas de una operacion pasandolas por el LogReader real."""
    log_file = tmp_path / "sample.log"
    log_file.write_text("".join(PREFIX + m + "\n" for m in messages), encoding="utf-8")
    return LogReader(str(log_file)).read_operations()["abc123"]


@pytest.fixture
def processor():
    return ADManagerResetUserProcessor()


def test_metadatos_del_procesador(processor):
    assert processor.action_name == "resetuser"
    assert processor.system_name == "ADManager"
    assert processor.matches("GET /v3/users_admin/resetuser?x=1")
    assert not processor.matches("GET /v3/users_admin/register_user?x=1")


def test_operacion_exitosa_completa(tmp_path, processor):
    lines = build_operation(
        tmp_path,
        [
            REQUEST.format(status=200),
            SEARCH_REQUESTER,
            SEARCH_USER,
            ADM_OK,
        ],
    )

    record = processor.process_operation("abc123", lines)

    assert record["id"] == "abc123"
    assert record["timestamp"] == "2026-09-01T00:02:39.862105Z"
    assert record["solicitante"] == "admsistemas520"
    assert record["target"] == "520000228"
    assert record["acción"] == "resetuser"
    assert record["sistema"] == "ADManager"
    assert record["nombre completo del usuario solicitante"] == "Nombre_admin Apellido_admin"
    assert record["nombre completo del usuario target"] == "Nombre_target Apellido_target"
    assert record["oficina del usuario solicitante"] == "Tienda 520"
    assert record["oficina del usuario target"] == "Tienda 520"
    assert record["resultado final"] == "Contraseña restablecida correctamente."


def test_timeout_de_admanager_usa_el_campo_reason(tmp_path, processor):
    lines = build_operation(tmp_path, [REQUEST.format(status=504), ADM_TIMEOUT])

    record = processor.process_operation("abc123", lines)

    assert (
        record["resultado final"]
        == "No se pudo completar el restablecimiento: ADManager superó el tiempo de espera de 35 segundos."
    )


@pytest.mark.parametrize(
    "status, esperado",
    [
        (200, "Contraseña restablecida correctamente."),
        (
            403,
            "Restablecimiento no autorizado; los logs no permiten determinar la causa específica.",
        ),
        (
            404,
            "No se encontró al menos uno de los usuarios en ADManager; los logs no permiten identificar cuál.",
        ),
        (500, "Error crítico inesperado en el proceso; requiere revisión técnica."),
        (
            503,
            "No se pudo restablecer la contraseña por un error de ADManager: El mensaje de error de ADManager no está disponible en los logs.",
        ),
        (
            504,
            "No se pudo completar el restablecimiento: ADManager superó el tiempo de espera de 35 segundos.",
        ),
        (418, "No se pudo determinar el resultado con la información disponible."),
    ],
)
def test_resultado_inferido_del_codigo_http(tmp_path, processor, status, esperado):
    """Sin respuesta de ADManager, el resultado se infiere del codigo HTTP."""
    lines = build_operation(tmp_path, [REQUEST.format(status=status)])

    record = processor.process_operation("abc123", lines)

    assert record["resultado final"] == esperado


def test_sin_codigo_http_el_resultado_es_desconocido(tmp_path, processor):
    lines = build_operation(
        tmp_path,
        [
            "HTTP Request: http://apitools.com:8000/v3/users_admin/resetuser?sAMAccountName_requester=a&sAMAccountName_target=b"
        ],
    )

    record = processor.process_operation("abc123", lines)

    assert (
        record["resultado final"]
        == "No se pudo determinar el resultado con la información disponible."
    )


def test_usuarios_desconocidos_dejan_nombre_y_oficina_vacios(tmp_path, processor):
    lines = build_operation(tmp_path, [REQUEST.format(status=200), ADM_OK])

    record = processor.process_operation("abc123", lines)

    assert record["nombre completo del usuario solicitante"] == ""
    assert record["oficina del usuario target"] == ""


def test_json_de_searchuser_corrupto_no_rompe_el_procesamiento(tmp_path, processor):
    lines = build_operation(
        tmp_path,
        [
            REQUEST.format(status=200),
            "SearchUser: {}, Raw Response: {esto no es json",
            ADM_OK,
        ],
    )

    record = processor.process_operation("abc123", lines)

    assert record["resultado final"] == "Contraseña restablecida correctamente."
    assert record["nombre completo del usuario target"] == ""


def test_operacion_sin_peticion_inicial_se_descarta(tmp_path, processor):
    lines = build_operation(tmp_path, [ADM_OK])

    assert processor.process_operation("abc123", lines) is None
