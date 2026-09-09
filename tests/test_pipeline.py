"""Pruebas de integracion del pipeline y de la CLI."""

import csv
import os

import pytest

from etl import DEFAULT_CSV_PATH, list_available_log_files, run_pipeline
from etl.cli import build_parser, resolve_target_files

LOG_DIA_1 = """\
2026-09-01T00:00:01.000Z | INFO [operation_Id=aaa111] | HTTP Request: http://apitools.com:8000/v3/users_admin/resetuser?sAMAccountName_requester=admin1&sAMAccountName_target=100001 "HTTP/1.1" 200
2026-09-01T00:00:02.000Z | INFO [operation_Id=aaa111] | SearchUser: {}, Raw Response: {"UsersList":[{"SAM_ACCOUNT_NAME":"100001","FIRST_NAME":"Ana","LAST_NAME":"Ruiz","OFFICE":"Tienda 1"}]}
2026-09-01T00:00:03.000Z | INFO [operation_Id=aaa111] | ADM-Raw response | status: 200 | body: [{'statusMessage': 'Contraseña restablecida correctamente.'}]
2026-09-01T00:00:10.000Z | INFO [operation_Id=bbb222] | HTTP Request: http://apitools.com:8000/v3/users_admin/resetuser?sAMAccountName_requester=admin1&sAMAccountName_target=100002 "HTTP/1.1" 404
2026-09-01T00:00:20.000Z | INFO [operation_Id=ccc333] | HTTP Request: http://apitools.com:8000/v3/healthcheck "HTTP/1.1" 200
"""

LOG_DIA_2 = """\
2026-09-02T00:00:01.000Z | INFO [operation_Id=ddd444] | HTTP Request: http://apitools.com:8000/v3/users_admin/resetuser?sAMAccountName_requester=admin2&sAMAccountName_target=100003 "HTTP/1.1" 504
2026-09-02T00:00:05.000Z | INFO [operation_Id=ddd444] | ADM-Raw response | status: 504 | reason: ADM timed out | timeout_type: ReadTimeout
"""


@pytest.fixture
def entorno(tmp_path):
    """Directorio con dos logs diarios y una ruta de CSV limpia."""
    (tmp_path / "2026-09-01.log").write_text(LOG_DIA_1, encoding="utf-8")
    (tmp_path / "2026-09-02.log").write_text(LOG_DIA_2, encoding="utf-8")
    return tmp_path, tmp_path / "reporte.csv"


def leer_filas(path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_pipeline_procesa_solo_las_acciones_habilitadas(entorno):
    log_dir, csv_path = entorno

    inserted = run_pipeline(list_available_log_files(str(log_dir)), csv_path=str(csv_path))

    filas = leer_filas(csv_path)
    assert inserted == 3  # healthcheck no es una accion registrada
    assert [f["id"] for f in filas] == ["aaa111", "bbb222", "ddd444"]
    assert filas[0]["resultado final"] == "Contraseña restablecida correctamente."
    assert (
        filas[1]["resultado final"]
        == "No se encontró al menos uno de los usuarios en ADManager; los logs no permiten identificar cuál."
    )
    assert (
        filas[2]["resultado final"]
        == "No se pudo completar el restablecimiento: ADManager superó el tiempo de espera de 35 segundos."
    )


def test_pipeline_es_idempotente_al_reejecutarse(entorno):
    log_dir, csv_path = entorno
    log_files = list_available_log_files(str(log_dir))

    assert run_pipeline(log_files, csv_path=str(csv_path)) == 3
    contenido = csv_path.read_bytes()

    assert run_pipeline(log_files, csv_path=str(csv_path)) == 0
    assert csv_path.read_bytes() == contenido


def test_reprocesar_un_dia_anterior_no_altera_el_csv(entorno):
    log_dir, csv_path = entorno
    run_pipeline(list_available_log_files(str(log_dir)), csv_path=str(csv_path))
    contenido = csv_path.read_bytes()

    inserted = run_pipeline([str(log_dir / "2026-09-01.log")], csv_path=str(csv_path))

    assert inserted == 0
    assert csv_path.read_bytes() == contenido


def test_carga_diaria_incremental(entorno):
    log_dir, csv_path = entorno

    dia_1 = run_pipeline([str(log_dir / "2026-09-01.log")], csv_path=str(csv_path))
    dia_2 = run_pipeline([str(log_dir / "2026-09-02.log")], csv_path=str(csv_path))

    assert (dia_1, dia_2) == (2, 1)
    assert len(leer_filas(csv_path)) == 3


# ------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------


def parse(argv: list[str]):
    return build_parser().parse_args(argv)


def test_cli_modo_diario_selecciona_el_log_mas_reciente(entorno):
    log_dir, _ = entorno

    seleccion = resolve_target_files(parse([]), str(log_dir))

    assert [os.path.basename(p) for p in seleccion] == ["2026-09-02.log"]


def test_cli_modo_all_selecciona_todo_en_orden(entorno):
    log_dir, _ = entorno

    seleccion = resolve_target_files(parse(["--all"]), str(log_dir))

    assert [os.path.basename(p) for p in seleccion] == ["2026-09-01.log", "2026-09-02.log"]


def test_cli_modo_date_selecciona_una_fecha(entorno):
    log_dir, _ = entorno

    seleccion = resolve_target_files(parse(["--date", "2026-09-01"]), str(log_dir))

    assert [os.path.basename(p) for p in seleccion] == ["2026-09-01.log"]


def test_cli_modo_log_file_acepta_ruta_directa(entorno):
    log_dir, _ = entorno
    ruta = str(log_dir / "2026-09-02.log")

    assert resolve_target_files(parse(["--log-file", ruta]), str(log_dir)) == [ruta]


@pytest.mark.parametrize(
    "argv",
    [
        ["--date", "2026-12-31"],
        ["--log-file", "no_existe.log"],
    ],
)
def test_cli_reporta_cuando_no_hay_nada_que_procesar(entorno, argv):
    log_dir, _ = entorno

    assert resolve_target_files(parse(argv), str(log_dir)) is None


def test_cli_reporta_directorio_sin_logs(tmp_path):
    assert resolve_target_files(parse([]), str(tmp_path)) is None
    assert resolve_target_files(parse(["--all"]), str(tmp_path)) is None


def test_cli_usa_el_csv_del_proyecto_por_defecto():
    assert parse([]).csv_path == DEFAULT_CSV_PATH
