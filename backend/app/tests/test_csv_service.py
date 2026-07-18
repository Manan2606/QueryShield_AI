import pytest

from app.services.csv_service import analyze_csv


def _write_csv(tmp_path, content: bytes):
    path = tmp_path / "sample.csv"
    path.write_bytes(content)
    return str(path)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"name,name\nAlice,Bob\n", "Duplicate CSV header"),
        (b"name,\nAlice,Bob\n", "header at position 2 is blank"),
        (b"1name,value\nAlice,1\n", "Invalid BigQuery column name"),
        (b"name,value\nAlice\n", "CSV row 2 has 1 columns; expected 2"),
        (b"name,value\nAlice,1,extra\n", "CSV row 2 has 3 columns; expected 2"),
    ],
)
def test_analyze_csv_rejects_invalid_structure(tmp_path, content, message):
    with pytest.raises(ValueError, match=message):
        analyze_csv(_write_csv(tmp_path, content))


def test_analyze_csv_rejects_invalid_utf8(tmp_path):
    with pytest.raises(ValueError, match="CSV must be valid UTF-8"):
        analyze_csv(_write_csv(tmp_path, b"name\n\xff\n"))


def test_analyze_csv_rejects_very_wide_files(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.csv_service.settings.MAX_CSV_COLUMNS", 2)

    with pytest.raises(ValueError, match="CSV has too many columns; maximum is 2"):
        analyze_csv(_write_csv(tmp_path, b"one,two,three\n1,2,3\n"))
