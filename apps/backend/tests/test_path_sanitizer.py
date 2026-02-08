from src.services.path_sanitizer import sanitize_filename, sanitize_path_segment


def test_sanitize_path_segment_replaces_invalid_chars() -> None:
    result = sanitize_path_segment('bad:name*"test"?')
    assert ":" not in result
    assert "*" not in result
    assert '"' not in result
    assert "?" not in result


def test_sanitize_filename_handles_reserved_names() -> None:
    assert sanitize_filename("CON.txt") == "CON_.txt"
    assert sanitize_filename("LPT1") == "LPT1_"


def test_sanitize_filename_strips_trailing_dots_and_spaces() -> None:
    result = sanitize_filename("name. ")
    assert not result.endswith(".")
    assert not result.endswith(" ")
