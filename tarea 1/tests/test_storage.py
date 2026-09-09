"""Pruebas de idempotencia y formato del almacenamiento CSV."""

import csv

from etl import CSV_HEADER, CSVStorageManager


def make_record(op_id: str, timestamp: str, **overrides) -> dict:
    record = {
        "id": op_id,
        "timestamp": timestamp,
        "solicitante": "admsistemas520",
        "target": "520000228",
        "acción": "resetuser",
        "sistema": "ADManager",
        "nombre completo del usuario solicitante": "Nombre_admin Apellido_admin",
        "nombre completo del usuario target": "Nombre_target Apellido_target",
        "oficina del usuario solicitante": "Tienda 520",
        "oficina del usuario target": "Tienda 520",
        "resultado final": "Password reset successful.",
    }
    record.update(overrides)
    return record


def read_csv(path) -> tuple[list[str], list[dict]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames), list(reader)


def test_escribe_exactamente_las_columnas_del_esquema(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    storage = CSVStorageManager(str(csv_path))

    inserted = storage.save_records([make_record("aaa1", "2026-09-01T00:00:00Z")])

    header, rows = read_csv(csv_path)
    assert inserted == 1
    assert header == CSV_HEADER
    assert len(rows) == 1


def test_reejecucion_no_duplica_ni_modifica_el_csv(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    storage = CSVStorageManager(str(csv_path))
    records = [
        make_record("aaa1", "2026-09-01T00:00:00Z"),
        make_record("bbb2", "2026-09-01T01:00:00Z"),
    ]

    assert storage.save_records(records) == 2
    contenido_original = csv_path.read_bytes()

    # Segunda y tercera corrida con la misma entrada: cero inserciones, archivo intacto
    assert storage.save_records(records) == 0
    assert storage.save_records(records) == 0
    assert csv_path.read_bytes() == contenido_original


def test_carga_incremental_solo_agrega_lo_nuevo(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    storage = CSVStorageManager(str(csv_path))
    storage.save_records([make_record("aaa1", "2026-09-01T00:00:00Z")])

    inserted = storage.save_records([
        make_record("aaa1", "2026-09-01T00:00:00Z"),
        make_record("bbb2", "2026-09-02T00:00:00Z"),
    ])

    _, rows = read_csv(csv_path)
    assert inserted == 1
    assert [r["id"] for r in rows] == ["aaa1", "bbb2"]


def test_las_filas_quedan_ordenadas_cronologicamente(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    storage = CSVStorageManager(str(csv_path))

    storage.save_records([
        make_record("ccc3", "2026-09-03T00:00:00Z"),
        make_record("aaa1", "2026-09-01T00:00:00Z"),
        make_record("bbb2", "2026-09-02T00:00:00Z"),
    ])

    _, rows = read_csv(csv_path)
    assert [r["id"] for r in rows] == ["aaa1", "bbb2", "ccc3"]


def test_el_id_es_la_clave_de_idempotencia_sin_importar_mayusculas(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    storage = CSVStorageManager(str(csv_path))
    storage.save_records([make_record("AAA1", "2026-09-01T00:00:00Z")])

    inserted = storage.save_records([make_record("aaa1", "2026-09-01T00:00:00Z")])

    assert inserted == 0


def test_sin_id_la_clave_es_timestamp_solicitante_target_accion(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    storage = CSVStorageManager(str(csv_path))
    storage.save_records([make_record("", "2026-09-01T00:00:00Z")])

    repetido = storage.save_records([make_record("", "2026-09-01T00:00:00Z")])
    distinto = storage.save_records([make_record("", "2026-09-01T00:00:00Z", target="otro")])

    assert repetido == 0
    assert distinto == 1


def test_se_asigna_updated_at_y_se_respeta_el_provisto(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    storage = CSVStorageManager(str(csv_path))

    storage.save_records([
        make_record("aaa1", "2026-09-01T00:00:00Z"),
        make_record("bbb2", "2026-09-02T00:00:00Z", updated_at="2020-01-01T00:00:00+00:00"),
    ])

    _, rows = read_csv(csv_path)
    por_id = {r["id"]: r for r in rows}
    assert por_id["aaa1"]["updated_at"]
    assert por_id["bbb2"]["updated_at"] == "2020-01-01T00:00:00+00:00"


def test_se_descartan_columnas_ajenas_al_esquema(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    storage = CSVStorageManager(str(csv_path))

    storage.save_records([make_record("aaa1", "2026-09-01T00:00:00Z", columna_extra="basura")])

    header, _ = read_csv(csv_path)
    assert header == CSV_HEADER


def test_no_deja_archivos_temporales(tmp_path):
    csv_path = tmp_path / "reporte.csv"
    CSVStorageManager(str(csv_path)).save_records([make_record("aaa1", "2026-09-01T00:00:00Z")])

    assert [p.name for p in tmp_path.iterdir()] == ["reporte.csv"]


def test_csv_vacio_se_crea_con_solo_el_encabezado(tmp_path):
    csv_path = tmp_path / "reporte.csv"

    inserted = CSVStorageManager(str(csv_path)).save_records([])

    header, rows = read_csv(csv_path)
    assert inserted == 0
    assert header == CSV_HEADER
    assert rows == []
