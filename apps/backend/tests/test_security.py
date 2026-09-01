from src.core import security
import json

import pytest

from src.core.security import (
    CredentialStorageError,
    FileTokenStore,
    KeyringTokenStore,
    TokenData,
)


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


def test_keyring_store_reads_windows_credentials_only_once(monkeypatch) -> None:
    values = {
        ("larksync", "access_token"): "access",
        ("larksync", "refresh_token"): "refresh",
        ("larksync", "expires_at"): "123",
    }
    calls: list[str] = []

    def fake_get_password(service: str, key: str):
        calls.append(key)
        return values.get((service, key))

    monkeypatch.setattr(security.keyring, "get_password", fake_get_password)
    token_store = KeyringTokenStore()

    assert token_store.get() is not None
    first_call_count = len(calls)
    assert token_store.get() is not None

    assert first_call_count > 0
    assert len(calls) == first_call_count


def test_keyring_store_reload_observes_external_credential_update(monkeypatch) -> None:
    values = {
        ("larksync", "access_token"): "access-old",
        ("larksync", "refresh_token"): "refresh-old",
        ("larksync", "expires_at"): "123",
    }

    monkeypatch.setattr(
        security.keyring,
        "get_password",
        lambda service, key: values.get((service, key)),
    )
    token_store = KeyringTokenStore()

    cached = token_store.get()
    assert cached is not None
    assert cached.refresh_token == "refresh-old"

    values[("larksync", "access_token")] = "access-new"
    values[("larksync", "refresh_token")] = "refresh-new"
    values[("larksync", "expires_at")] = "456"

    assert token_store.get() == cached
    reloaded = token_store.reload()

    assert reloaded is not None
    assert reloaded.access_token == "access-new"
    assert reloaded.refresh_token == "refresh-new"
    assert reloaded.expires_at == 456.0


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


def test_file_token_store_isolates_accounts_when_env_path_is_configured(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("LARKSYNC_TOKEN_FILE", str(tmp_path / "tokens.json"))
    first = FileTokenStore(account_id="account-a")
    second = FileTokenStore(account_id="account-b")

    first.set(TokenData(access_token="token-a", refresh_token="", expires_at=None))
    second.set(TokenData(access_token="token-b", refresh_token="", expires_at=None))

    assert first.get() is not None and first.get().access_token == "token-a"
    assert second.get() is not None and second.get().access_token == "token-b"
    assert (tmp_path / "tokens.account-a.json").is_file()
    assert (tmp_path / "tokens.account-b.json").is_file()


def test_get_token_store_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LARKSYNC_TOKEN_STORE", "file")
    monkeypatch.setenv("LARKSYNC_TOKEN_FILE", str(tmp_path / "tokens.json"))
    token_store = security.get_token_store()
    assert isinstance(token_store, FileTokenStore)


def test_keyring_chunked_bundle_roundtrip_when_each_token_exceeds_windows_limit(
    monkeypatch,
) -> None:
    values: dict[tuple[str, str], str] = {}

    class FakeDeleteError(Exception):
        pass

    def fake_set_password(service: str, key: str, value: str) -> None:
        if len(value.encode("utf-16-le")) > 2560:
            raise OSError(1783, "CredWrite", "占位程序接收到错误数据。")
        values[(service, key)] = value

    def fake_get_password(service: str, key: str):
        return values.get((service, key))

    def fake_delete_password(service: str, key: str) -> None:
        if (service, key) not in values:
            raise FakeDeleteError()
        del values[(service, key)]

    monkeypatch.setattr(security.keyring, "set_password", fake_set_password)
    monkeypatch.setattr(security.keyring, "get_password", fake_get_password)
    monkeypatch.setattr(security.keyring, "delete_password", fake_delete_password)
    monkeypatch.setattr(security.keyring.errors, "PasswordDeleteError", FakeDeleteError)

    expected = TokenData(
        access_token="a" * 4200,
        refresh_token="r" * 4600,
        expires_at=1234.5,
        open_id="ou_long_token",
        account_name="长凭据测试账号",
        scope="drive:drive offline_access",
        refresh_expires_at=9876.5,
        auth_protocol="device_v2",
    )
    KeyringTokenStore(account_id="account-long").set(expected)

    loaded = KeyringTokenStore(account_id="account-long").get()
    assert loaded == expected
    service = "larksync.account.account-long"
    manifest = json.loads(values[(service, "token_bundle.active")])
    assert manifest["format"] == "chunked_bundle_v1"
    assert manifest["chunks"] > 1
    assert all(
        len(value.encode("utf-16-le")) <= 2560
        for (stored_service, _key), value in values.items()
        if stored_service == service
    )


def test_keyring_chunk_write_failure_keeps_previous_generation_readable(
    monkeypatch,
) -> None:
    values: dict[tuple[str, str], str] = {}
    fail_new_chunks = False
    new_chunk_writes = 0

    class FakeDeleteError(Exception):
        pass

    def fake_set_password(service: str, key: str, value: str) -> None:
        nonlocal new_chunk_writes
        if fail_new_chunks and key.startswith("token_bundle.") and key != "token_bundle.active":
            new_chunk_writes += 1
            if new_chunk_writes == 2:
                raise OSError(1783, "CredWrite", "占位程序接收到错误数据。")
        values[(service, key)] = value

    monkeypatch.setattr(security.keyring, "set_password", fake_set_password)
    monkeypatch.setattr(
        security.keyring,
        "get_password",
        lambda service, key: values.get((service, key)),
    )
    monkeypatch.setattr(
        security.keyring,
        "delete_password",
        lambda service, key: values.pop((service, key), None),
    )
    monkeypatch.setattr(security.keyring.errors, "PasswordDeleteError", FakeDeleteError)

    service = "larksync.account.account-atomic"
    previous = TokenData("old-access", "old-refresh", 100.0, auth_protocol="legacy_v1")
    token_store = KeyringTokenStore(account_id="account-atomic")
    token_store.set(previous)
    previous_manifest = values[(service, "token_bundle.active")]

    fail_new_chunks = True
    with pytest.raises(CredentialStorageError):
        token_store.set(TokenData("n" * 4200, "r" * 4200, 200.0))

    assert values[(service, "token_bundle.active")] == previous_manifest
    assert KeyringTokenStore(account_id="account-atomic").get() == previous


def test_keyring_manifest_switch_failure_keeps_legacy_split_credentials(
    monkeypatch,
) -> None:
    service = "larksync.account.account-legacy"
    values: dict[tuple[str, str], str] = {
        (service, "access_token"): "legacy-access",
        (service, "refresh_token"): "legacy-refresh",
        (service, "expires_at"): "100",
        (service, "auth_protocol"): "legacy_v1",
    }

    def fake_set_password(stored_service: str, key: str, value: str) -> None:
        if key == "token_bundle.active":
            raise OSError(1783, "CredWrite", "占位程序接收到错误数据。")
        values[(stored_service, key)] = value

    monkeypatch.setattr(security.keyring, "set_password", fake_set_password)
    monkeypatch.setattr(
        security.keyring,
        "get_password",
        lambda stored_service, key: values.get((stored_service, key)),
    )
    monkeypatch.setattr(
        security.keyring,
        "delete_password",
        lambda stored_service, key: values.pop((stored_service, key), None),
    )

    with pytest.raises(CredentialStorageError):
        KeyringTokenStore(account_id="account-legacy").set(
            TokenData("new-access", "new-refresh", 200.0)
        )

    loaded = KeyringTokenStore(account_id="account-legacy").get()
    assert loaded is not None
    assert loaded.access_token == "legacy-access"
    assert loaded.refresh_token == "legacy-refresh"
    assert loaded.auth_protocol == "legacy_v1"


def test_keyring_rejects_corrupted_active_generation(monkeypatch) -> None:
    values: dict[tuple[str, str], str] = {}
    monkeypatch.setattr(
        security.keyring,
        "set_password",
        lambda service, key, value: values.__setitem__((service, key), value),
    )
    monkeypatch.setattr(
        security.keyring,
        "get_password",
        lambda service, key: values.get((service, key)),
    )
    monkeypatch.setattr(
        security.keyring,
        "delete_password",
        lambda service, key: values.pop((service, key), None),
    )

    service = "larksync.account.account-corrupt"
    KeyringTokenStore(account_id="account-corrupt").set(
        TokenData("access", "refresh", 100.0)
    )
    manifest = json.loads(values[(service, "token_bundle.active")])
    first_chunk_key = f"token_bundle.{manifest['generation']}.0000"
    values[(service, first_chunk_key)] += "tampered"

    with pytest.raises(CredentialStorageError, match="校验失败"):
        KeyringTokenStore(account_id="account-corrupt").get()


def test_keyring_next_read_cleans_interrupted_staging_generation(monkeypatch) -> None:
    values: dict[tuple[str, str], str] = {}
    monkeypatch.setattr(
        security.keyring,
        "set_password",
        lambda service, key, value: values.__setitem__((service, key), value),
    )
    monkeypatch.setattr(
        security.keyring,
        "get_password",
        lambda service, key: values.get((service, key)),
    )
    monkeypatch.setattr(
        security.keyring,
        "delete_password",
        lambda service, key: values.pop((service, key), None),
    )

    service = "larksync.account.account-staging"
    token_store = KeyringTokenStore(account_id="account-staging")
    previous = TokenData("old-access", "old-refresh", 100.0)
    token_store.set(previous)

    interrupted = TokenData("new-access" * 500, "new-refresh" * 500, 200.0)
    encoded = token_store._encode_token(interrupted)
    chunks = [
        encoded[index : index + token_store._CHUNK_SIZE]
        for index in range(0, len(encoded), token_store._CHUNK_SIZE)
    ]
    generation = "f" * 32
    manifest = token_store._build_manifest(generation, chunks)
    manifest_raw = json.dumps(
        manifest, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    values[(service, "token_bundle.staging")] = manifest_raw
    for index, chunk in enumerate(chunks):
        values[(service, token_store._chunk_key(generation, index))] = chunk

    assert KeyringTokenStore(account_id="account-staging").get() == previous
    assert (service, "token_bundle.staging") not in values
    assert not any(
        stored_service == service and f"token_bundle.{generation}." in key
        for stored_service, key in values
    )
