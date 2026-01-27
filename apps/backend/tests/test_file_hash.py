from src.services.file_hash import calculate_file_hash


def test_calculate_file_hash(tmp_path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("abc", encoding="utf-8")
    assert (
        calculate_file_hash(path)
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
