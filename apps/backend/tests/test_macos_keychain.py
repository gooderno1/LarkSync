from types import SimpleNamespace

import pytest

from src.core import macos_keychain


class FakeSecurity:
    errSecSuccess = 0
    errSecItemNotFound = -25300
    errSecDuplicateItem = -25299
    kSecClass = "class"
    kSecClassGenericPassword = "generic"
    kSecAttrService = "service"
    kSecAttrAccount = "account"
    kSecValueData = "data"
    kSecReturnData = "return_data"
    kSecMatchLimit = "limit"
    kSecMatchLimitOne = "one"
    kSecUseAuthenticationUI = "ui"
    kSecUseAuthenticationUIFail = "fail"

    def __init__(self):
        self.values = {}
        self.calls = []
        self.denied = False
        self.identities = {}
        self.serial = 0

    def _call(self, operation, query):
        self.calls.append((operation, dict(query)))
        return (query["service"], query["account"])

    def SecItemCopyMatching(self, query, output):
        key = self._call("get", query)
        if self.denied:
            return -25308, None
        return (0, self.values[key]) if key in self.values else (-25300, None)

    def SecItemUpdate(self, query, attributes):
        key = self._call("update", query)
        if self.denied:
            return -128
        if key not in self.values:
            return -25300
        self.values[key] = attributes["data"]
        return 0

    def SecItemAdd(self, query, output):
        key = self._call("add", query)
        if key in self.values:
            return -25299, None
        self.serial += 1
        self.identities[key] = self.serial
        self.values[key] = query["data"]
        return 0, None

    def SecItemDelete(self, query):
        key = self._call("delete", query)
        self.values.pop(key, None)
        self.identities.pop(key, None)
        return 0


@pytest.fixture
def native(monkeypatch):
    api = FakeSecurity()
    foundation = SimpleNamespace(NSData=SimpleNamespace(dataWithBytes_length_=lambda data, length: data))
    monkeypatch.setattr(macos_keychain, "_frameworks", lambda: (api, foundation))
    return macos_keychain.MacOSKeychain(), api


def test_noninteractive_access_and_in_place_update_preserve_item_identity(native):
    backend, api = native
    backend.set_password("test", "account", "旧值")
    identity = api.identities[("test", "account")]
    backend.set_password("test", "account", "新值")
    assert backend.get_password("test", "account") == "新值"
    assert api.identities[("test", "account")] == identity
    assert all(query["ui"] == "fail" for _, query in api.calls)
    assert [op for op, _ in api.calls] == ["update", "add", "update", "get"]


def test_denial_latches_across_items_and_explicit_retry_recovers(native):
    backend, api = native
    api.denied = True
    for key in ("first", "first", "second"):
        with pytest.raises(macos_keychain.KeychainAccessError):
            backend.get_password("test", key)
    assert len(api.calls) == 1
    assert backend.status()["blocked"] is True
    api.denied = False
    with backend.interactive_retry():
        assert backend.get_password("test", "first") is None
    assert "ui" not in api.calls[-1][1]
    assert backend.status()["blocked"] is False
    backend.get_password("test", "second")
    assert api.calls[-1][1]["ui"] == "fail"


def test_cancelled_retry_stays_blocked_and_does_not_expose_secret(native):
    backend, api = native
    api.denied = True
    with pytest.raises(macos_keychain.KeychainAccessError) as error:
        with backend.interactive_retry():
            backend.set_password("test", "account", "do-not-leak-this-value")
    assert "do-not-leak" not in str(error.value)
    assert backend.status()["blocked"] is True
    assert backend.status()["retrying"] is False
    assert not any(op == "add" for op, _ in api.calls)


def test_background_access_during_interactive_retry_fails_without_waiting(native):
    from concurrent.futures import ThreadPoolExecutor

    backend, api = native
    with backend.interactive_retry():
        with ThreadPoolExecutor() as executor:
            result = executor.submit(backend.get_password, "test", "account")
            with pytest.raises(macos_keychain.KeychainAccessError):
                result.result(timeout=1)
    assert not api.calls


def test_missing_item_is_not_an_authorization_failure(native):
    backend, _api = native
    assert backend.get_password("missing", "account") is None
    assert backend.status()["blocked"] is False


def test_explicit_retry_authorizes_failed_item_even_before_database_commit(native):
    backend, api = native
    api.denied = True
    with pytest.raises(macos_keychain.KeychainAccessError):
        backend.set_password("uncommitted-profile", "secret", "value")
    api.denied = False
    with backend.interactive_retry():
        backend.retry_pending()
    assert api.calls[-1] == ("get", {"class": "generic", "service": "uncommitted-profile",
                                      "account": "secret", "return_data": True, "limit": "one"})
