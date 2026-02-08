from pathlib import Path

from src.services.log_reader import read_log_entries


def test_read_log_entries_supports_pagination_and_filters(tmp_path: Path) -> None:
    log_file = tmp_path / "larksync.log"
    log_file.write_text(
        "\n".join(
            [
                "2026-02-08 10:00:00.000 | INFO | first line",
                "traceback line 1",
                "2026-02-08 10:00:01.000 | ERROR | second line",
                "2026-02-08 10:00:02.000 | WARNING | third line",
            ]
        ),
        encoding="utf-8",
    )

    total, entries = read_log_entries(
        log_file,
        limit=2,
        offset=0,
        level="",
        search="",
        order="desc",
    )
    assert total == 3
    assert entries[0][1] == "WARNING"
    assert entries[1][1] == "ERROR"

    total, entries = read_log_entries(
        log_file,
        limit=1,
        offset=1,
        level="",
        search="",
        order="desc",
    )
    assert total == 3
    assert entries[0][1] == "ERROR"

    total, entries = read_log_entries(
        log_file,
        limit=5,
        offset=0,
        level="",
        search="traceback",
        order="desc",
    )
    assert total == 1
    assert entries[0][2] == "first line"

    total, entries = read_log_entries(
        log_file,
        limit=2,
        offset=0,
        level="",
        search="",
        order="asc",
    )
    assert total == 3
    assert entries[0][1] == "INFO"
    assert entries[1][1] == "ERROR"
