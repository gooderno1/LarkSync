from src.services.state_store import AuthStateStore


def test_auth_state_store_issue_and_consume() -> None:
    store = AuthStateStore(ttl_seconds=1)
    state = store.issue()
    assert store.consume(state) is True
    assert store.consume(state) is False
