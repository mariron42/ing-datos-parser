"""Pruebas de descubrimiento y seleccion de archivos de log."""

from etl import (
    extract_date_from_filename,
    find_log_file_by_date,
    get_latest_log_file,
    list_available_log_files,
)


def crear_logs(tmp_path, nombres: list[str]):
    for nombre in nombres:
        (tmp_path / nombre).write_text("", encoding="utf-8")


def test_extrae_la_fecha_del_nombre_de_archivo():
    assert extract_date_from_filename("/ruta/2026-09-01.log") == "2026-09-01"
    assert extract_date_from_filename("2026-09-01 Tarea 1.pdf") == "2026-09-01"
    assert extract_date_from_filename("sin_fecha.log") is None


def test_lista_solo_logs_y_en_orden_cronologico(tmp_path):
    crear_logs(tmp_path, ["2026-09-01.log", "2026-08-29.log", "2026-08-30.log", "notas.txt"])

    encontrados = [p.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for p in list_available_log_files(str(tmp_path))]

    assert encontrados == ["2026-08-29.log", "2026-08-30.log", "2026-09-01.log"]


def test_obtiene_el_log_mas_reciente(tmp_path):
    crear_logs(tmp_path, ["2026-08-29.log", "2026-09-01.log", "2026-08-30.log"])

    assert get_latest_log_file(str(tmp_path)).endswith("2026-09-01.log")


def test_directorio_sin_logs(tmp_path):
    assert list_available_log_files(str(tmp_path)) == []
    assert get_latest_log_file(str(tmp_path)) is None


def test_busca_log_por_fecha_exacta_y_flexible(tmp_path):
    crear_logs(tmp_path, ["2026-08-29.log", "logs_2026-09-01_bot.log"])

    assert find_log_file_by_date(str(tmp_path), "2026-08-29").endswith("2026-08-29.log")
    assert find_log_file_by_date(str(tmp_path), "2026-09-01").endswith("logs_2026-09-01_bot.log")
    assert find_log_file_by_date(str(tmp_path), "2026-12-31") is None
