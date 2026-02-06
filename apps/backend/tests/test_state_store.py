from src.services.state_store import AuthStateStore


def test_auth_state_store_issue_and_consume() -> None:
    store = AuthStateStore(ttl_seconds=1)
    state = store.issue()
    valid, redirect_to = store.consume(state)
    assert valid is True
    assert redirect_to is None
    valid, redirect_to = store.consume(state)
    assert valid is False
    assert redirect_to is None


def test_auth_state_store_redirect_roundtrip() -> None:
    store = AuthStateStore(ttl_seconds=1)
    state = store.issue("http://localhost:3666")
    valid, redirect_to = store.consume(state)
    assert valid is True
    assert redirect_to == "http://localhost:3666"
