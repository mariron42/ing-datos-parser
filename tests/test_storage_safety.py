"""Protección ante fallos de escritura y ejecuciones concurrentes."""

import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from etl import CSVStorageManager


def test_invalid_csv_is_preserved(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("wrong,header\na,b\n", encoding="utf-8")
    original = path.read_bytes()
    with pytest.raises(ValueError, match="esquema"):
        CSVStorageManager(path).save_records([{"id": "abc"}])
    assert path.read_bytes() == original


def test_failed_replace_preserves_original_and_removes_temp(tmp_path, monkeypatch):
    path = tmp_path / "report.csv"
    storage = CSVStorageManager(path)
    storage.save_records([{"id": "abc"}])
    original = path.read_bytes()

    def fail(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr("etl.storage.os.replace", fail)
    with pytest.raises(OSError):
        storage.save_records([{"id": "def"}])
    assert path.read_bytes() == original
    assert {p.name for p in tmp_path.iterdir()} - {"report.csv.lock.tmp"} == {"report.csv"}


def test_concurrent_processes_keep_all_records_without_duplicates(tmp_path):
    path = tmp_path / "nested" / "report.csv"
    script = (
        "import sys; from etl import CSVStorageManager; "
        "CSVStorageManager(sys.argv[1]).save_records([{'id': sys.argv[2]}, {'id': 'shared'}])"
    )

    def run(index):
        subprocess.run([sys.executable, "-c", script, str(path), str(index)], check=True)

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(run, range(8)))
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 9
    assert {row["id"] for row in rows} == {str(i) for i in range(8)} | {"shared"}
