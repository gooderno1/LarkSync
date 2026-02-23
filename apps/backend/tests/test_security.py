from src.core import security
from src.core.security import FileTokenStore, KeyringTokenStore, TokenData


def test_keyring_roundtrip_empty_refresh_token(monkeypatch) -> None:
    store: dict[tuple[str, str], str] = {}

    class FakeDeleteError(Exception):
        pass

    def fake_set_password(service: str, key: str, value: str) -> None:
        store[(service, key)] = value

    def fake_get_password(service: str, key: str):
        return store.get((service, key))

    def fake_delete_password(service: str, key: str) -> None:
        if (service, key) not in store:
            raise FakeDeleteError()
        del store[(service, key)]

    monkeypatch.setattr(security.keyring, "set_password", fake_set_password)
    monkeypatch.setattr(security.keyring, "get_password", fake_get_password)
    monkeypatch.setattr(security.keyring, "delete_password", fake_delete_password)
    monkeypatch.setattr(security.keyring.errors, "PasswordDeleteError", FakeDeleteError)

    token_store = KeyringTokenStore()
    token_store.set(TokenData(access_token="a", refresh_token="", expires_at=None))
    loaded = token_store.get()

    assert loaded is not None
    assert loaded.access_token == "a"
    assert loaded.refresh_token == ""


def test_keyring_roundtrip_open_id(monkeypatch) -> None:
    store: dict[tuple[str, str], str] = {}

    class FakeDeleteError(Exception):
        pass

    def fake_set_password(service: str, key: str, value: str) -> None:
        store[(service, key)] = value

    def fake_get_password(service: str, key: str):
        return store.get((service, key))

    def fake_delete_password(service: str, key: str) -> None:
        if (service, key) not in store:
            raise FakeDeleteError()
        del store[(service, key)]

    monkeypatch.setattr(security.keyring, "set_password", fake_set_password)
    monkeypatch.setattr(security.keyring, "get_password", fake_get_password)
    monkeypatch.setattr(security.keyring, "delete_password", fake_delete_password)
    monkeypatch.setattr(security.keyring.errors, "PasswordDeleteError", FakeDeleteError)

    token_store = KeyringTokenStore()
    token_store.set(
        TokenData(
            access_token="a",
            refresh_token="r",
            expires_at=None,
            open_id="ou_test_user",
            account_name="测试用户",
        )
    )
    loaded = token_store.get()

    assert loaded is not None
    assert loaded.open_id == "ou_test_user"
    assert loaded.account_name == "测试用户"


def test_file_token_store_roundtrip(tmp_path) -> None:
    token_file = tmp_path / "tokens.json"
    store = FileTokenStore(path=token_file)
    store.set(
        TokenData(
            access_token="access-1",
            refresh_token="refresh-1",
            expires_at=123.0,
            open_id="ou_test",
            account_name="测试账号",
        )
    )

    loaded = store.get()
    assert loaded is not None
    assert loaded.access_token == "access-1"
    assert loaded.refresh_token == "refresh-1"
    assert loaded.expires_at == 123.0
    assert loaded.open_id == "ou_test"
    assert loaded.account_name == "测试账号"


def test_file_token_store_clear(tmp_path) -> None:
    token_file = tmp_path / "tokens.json"
    store = FileTokenStore(path=token_file)
    store.set(TokenData(access_token="a", refresh_token="", expires_at=None))
    assert token_file.exists()
    store.clear()
    assert store.get() is None


def test_get_token_store_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LARKSYNC_TOKEN_STORE", "file")
    monkeypatch.setenv("LARKSYNC_TOKEN_FILE", str(tmp_path / "tokens.json"))
    token_store = security.get_token_store()
    assert isinstance(token_store, FileTokenStore)
