from src.core.account_context import account_scope, current_account_id


def test_account_scope_is_nested_and_restored() -> None:
    assert current_account_id() is None
    with account_scope("account-a"):
        assert current_account_id() == "account-a"
        with account_scope("account-b"):
            assert current_account_id() == "account-b"
        assert current_account_id() == "account-a"
    assert current_account_id() is None
