import json
from types import SimpleNamespace

import pytest

from src.core import macos_keychain, security
from src.core.security import CredentialStorageError, KeyringTokenStore, TokenData


@pytest.fixture
def memory_keychain(monkeypatch):
    values = {}
    calls = []

    def get(service, key):
        calls.append(("get", service, key))
        return values.get((service, key))

    def put(service, key, value):
        calls.append(("set", service, key))
        values[(service, key)] = value

    def delete(service, key):
        calls.append(("delete", service, key))
        values.pop((service, key), None)

    backend = SimpleNamespace(get_password=get, set_password=put, delete_password=delete,
                              ensure_available=lambda: None)
    monkeypatch.setattr(macos_keychain, "backend", backend)
    monkeypatch.setattr(security.keyring, "get_password", get)
    monkeypatch.setattr(security.keyring, "set_password", put)
    monkeypatch.setattr(security.keyring, "delete_password", delete)
    return backend, values, calls


def test_macos_long_tokens_use_one_item_and_remain_readable_after_refresh(memory_keychain):
    _backend, values, calls = memory_keychain
    store = security.MacOSKeyringTokenStore("long")
    expected = TokenData("a" * 4200, "r" * 4600, None, account_name="测试")
    store.set(expected)
    assert len(values) == 1
    assert security.MacOSKeyringTokenStore("long").get() == expected
    changed = TokenData("new", "new-refresh", 9999)
    store.set(changed)
    assert security.MacOSKeyringTokenStore("long").get() == changed
    assert len(values) == 1
    assert not any(op == "delete" for op, _, _ in calls)


def test_macos_migrates_chunked_bundle_and_then_ignores_old_items(memory_keychain):
    backend, values, calls = memory_keychain
    old = KeyringTokenStore("old")
    old._keyring = backend
    token = TokenData("a" * 4200, "r" * 4600, None)
    old.set(token)
    old_keys = set(values)
    current = security.MacOSKeyringTokenStore("old")
    assert current.get() == token
    assert old_keys <= set(values)
    calls.clear()
    assert security.MacOSKeyringTokenStore("old").get() == token
    assert len(calls) == 1
    assert "macos" in calls[0][2]


@pytest.mark.parametrize("old_format", ["split", "json"])
def test_macos_migrates_legacy_tokens_without_losing_protocol(memory_keychain, old_format):
    _backend, values, _calls = memory_keychain
    if old_format == "split":
        values[("larksync", "access_token")] = "access"
        values[("larksync", "refresh_token")] = "refresh"
        values[("larksync", "auth_protocol")] = "legacy_v1"
    else:
        values[("larksync", "oauth_tokens")] = json.dumps({"access_token": "access", "refresh_token": "refresh"})
    store = security.MacOSKeyringTokenStore()
    assert store.get().auth_protocol == "legacy_v1"
    assert security.MacOSKeyringTokenStore().get().refresh_token == "refresh"


def test_macos_corrupted_new_bundle_never_falls_back_to_old_token(memory_keychain):
    _backend, values, _calls = memory_keychain
    store = security.MacOSKeyringTokenStore()
    store.set(TokenData("new", "refresh", None))
    key = next(iter(values))
    values[key] = "invalid-json"
    values[("larksync", "access_token")] = "stale"
    with pytest.raises(CredentialStorageError):
        security.MacOSKeyringTokenStore().get()


def test_macos_failed_migration_preserves_old_token(memory_keychain, monkeypatch):
    backend, values, _calls = memory_keychain
    values[("larksync", "access_token")] = "old"

    def fail(*args):
        raise macos_keychain.KeychainAccessError("simulated-denial")

    monkeypatch.setattr(backend, "set_password", fail)
    with pytest.raises(CredentialStorageError):
        security.MacOSKeyringTokenStore().get()
    assert values == {("larksync", "access_token"): "old"}


def test_macos_logout_removes_new_and_old_token_without_resurrection(memory_keychain):
    _backend, values, _calls = memory_keychain
    values[("larksync", "access_token")] = "old"
    store = security.MacOSKeyringTokenStore()
    assert store.get() is not None
    store.clear()
    assert not values
    assert security.MacOSKeyringTokenStore().get() is None


def test_macos_secret_cache_and_explicit_reload(memory_keychain):
    _backend, values, calls = memory_keychain
    store = security.MacOSKeyringSecretStore()
    store.set("profile", "first")
    calls.clear()
    assert store.get("profile") == "first"
    assert store.get("profile") == "first"
    assert not calls
    values[(store._service, "profile")] = "external-update"
    assert store.reload("profile") == "external-update"
    assert len(calls) == 1
    store.clear("profile")
    calls.clear()
    assert store.get("profile") is None
    assert not calls


def test_factory_only_selects_macos_store_on_macos(memory_keychain, monkeypatch):
    monkeypatch.setattr(security, "_shared_token_stores", {})
    monkeypatch.setattr(security.ConfigManager, "get", lambda: SimpleNamespace(config=SimpleNamespace(token_store="keyring")))
    monkeypatch.delenv("LARKSYNC_TOKEN_STORE", raising=False)
    monkeypatch.setattr(macos_keychain, "enabled", lambda: True)
    assert isinstance(security.get_token_store("mac"), security.MacOSKeyringTokenStore)
    monkeypatch.setattr(macos_keychain, "enabled", lambda: False)
    assert type(security.get_token_store("windows")) is KeyringTokenStore


def test_installer_smoke_uses_actual_token_store_and_cleans_temporary_credentials(memory_keychain, monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3]))
    from apps.tray.launcher import _run_macos_token_store_smoke

    _backend, values, _calls = memory_keychain
    assert _run_macos_token_store_smoke("unit-test") == {
        "ok": True, "long_token_roundtrip": True, "refresh_roundtrip": True, "cleared": True,
    }
    assert not values


def test_explicit_global_namespace_is_not_replaced_by_current_account(memory_keychain, monkeypatch):
    from src.core.account_context import account_scope

    monkeypatch.setattr(security, "_shared_token_stores", {})
    monkeypatch.setattr(security.ConfigManager, "get", lambda: SimpleNamespace(config=SimpleNamespace(token_store="keyring")))
    monkeypatch.delenv("LARKSYNC_TOKEN_STORE", raising=False)
    monkeypatch.setattr(macos_keychain, "enabled", lambda: True)
    with account_scope("selected-account"):
        assert security.get_token_store("")._service == "larksync"
        assert security.get_token_store()._service == "larksync.account.selected-account"
