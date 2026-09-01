from src.api.accounts import _refresh_requires_reauthorization
from src.services.auth_service import AuthError


def test_refresh_only_requires_reauthorization_for_terminal_credential_errors() -> None:
    assert _refresh_requires_reauthorization(
        AuthError("飞书刷新凭证已失效", code="20026")
    )
    assert _refresh_requires_reauthorization(
        AuthError("refresh_token 不可用，请重新登录")
    )
    assert not _refresh_requires_reauthorization(
        AuthError("Token 请求失败：网络暂不可用")
    )
