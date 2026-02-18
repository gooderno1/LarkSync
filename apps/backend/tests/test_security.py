from src.core import security
from src.core.security import KeyringTokenStore, TokenData


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
