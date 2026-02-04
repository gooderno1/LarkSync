import httpx
import pytest

from src.services.feishu_client import FeishuClient


class FakeAuthService:
    async def get_valid_access_token(self) -> str:
        return "token"


class FakeHttpClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.calls = 0

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        self.calls += 1
        response = self._responses[min(self.calls - 1, len(self._responses) - 1)]
        return response

    async def aclose(self) -> None:
        return None


def _response(status_code: int, payload: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://open.feishu.cn/mock")
    return httpx.Response(status_code=status_code, json=payload, request=request)


@pytest.mark.asyncio
async def test_request_with_retry_retries_on_frequency_limit_code() -> None:
    client = FeishuClient(auth_service=FakeAuthService(), max_retries=3, backoff_base=0.0)
    client._client = FakeHttpClient(  # type: ignore[assignment]
        [
            _response(400, {"code": 99991400, "msg": "request trigger frequency limit"}),
            _response(200, {"code": 0, "data": {"ok": True}}),
        ]
    )

    response = await client.request_with_retry("POST", "https://open.feishu.cn/mock")
    payload = response.json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert client._client.calls == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_request_with_retry_does_not_retry_on_normal_bad_request() -> None:
    client = FeishuClient(auth_service=FakeAuthService(), max_retries=3, backoff_base=0.0)
    client._client = FakeHttpClient(  # type: ignore[assignment]
        [_response(400, {"code": 20001, "msg": "invalid request"})]
    )

    response = await client.request_with_retry("POST", "https://open.feishu.cn/mock")
    payload = response.json()

    assert response.status_code == 400
    assert payload["code"] == 20001
    assert client._client.calls == 1  # type: ignore[attr-defined]
