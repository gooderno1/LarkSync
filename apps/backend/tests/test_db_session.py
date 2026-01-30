from src.db.session import _sqlite_literal


def test_sqlite_literal_string() -> None:
    assert _sqlite_literal("auto") == "'auto'"
    assert _sqlite_literal("a'b") == "'a''b'"


def test_sqlite_literal_numbers_and_bool() -> None:
    assert _sqlite_literal(3) == "3"
    assert _sqlite_literal(3.5) == "3.5"
    assert _sqlite_literal(True) == "1"
    assert _sqlite_literal(False) == "0"


def test_sqlite_literal_none() -> None:
    assert _sqlite_literal(None) == "NULL"
