"""Pruebas de lectura y agrupacion de logs."""

from etl import LogReader

LOG_SAMPLE = """\
2026-09-01T10:00:00.000Z | INFO [operation_Id=aaa111] | GET http://bot/users_admin/resetuser?sAMAccountName_requester=jperez&sAMAccountName_target=mlopez "HTTP/1.1" 200
2026-09-01T10:00:01.000Z | INFO [operation_Id=aaa111] | SearchUser Raw Response: {"UsersList": []}
    continuacion multilinea del mensaje anterior
2026-09-01T10:05:00.000Z | INFO [operation_Id=bbb222] | GET http://bot/otra_cosa "HTTP/1.1" 200
"""


def test_agrupa_lineas_por_operation_id(tmp_path):
    log_file = tmp_path / "2026-09-01.log"
    log_file.write_text(LOG_SAMPLE, encoding="utf-8")

    operations = LogReader(str(log_file)).read_operations()

    assert set(operations) == {"aaa111", "bbb222"}
    assert len(operations["aaa111"]) == 3
    assert len(operations["bbb222"]) == 1


def test_lineas_multilinea_se_adjuntan_a_la_operacion_actual(tmp_path):
    log_file = tmp_path / "2026-09-01.log"
    log_file.write_text(LOG_SAMPLE, encoding="utf-8")

    operations = LogReader(str(log_file)).read_operations()
    continuacion = operations["aaa111"][2]

    assert continuacion["timestamp"] is None
    assert continuacion["level"] is None
    assert continuacion["message"] == "continuacion multilinea del mensaje anterior"


def test_ignora_lineas_previas_a_cualquier_operacion(tmp_path):
    log_file = tmp_path / "2026-09-01.log"
    log_file.write_text("ruido sin operation_Id\n" + LOG_SAMPLE, encoding="utf-8")

    operations = LogReader(str(log_file)).read_operations()

    assert set(operations) == {"aaa111", "bbb222"}
