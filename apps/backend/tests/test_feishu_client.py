import httpx
import json
import pytest

from src.core.config import AppConfig, RuntimeProfile
from src.services.feishu_client import CloudAccessDenied, FeishuClient, cloud_root_scope


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


class FakeRateLimiter:
    def __init__(self) -> None:
        self.calls = 0

    async def acquire(self) -> None:
        self.calls += 1


def _response(status_code: int, payload: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://open.feishu.cn/mock")
    return httpx.Response(status_code=status_code, json=payload, request=request)


def _text_response(status_code: int, text: str) -> httpx.Response:
    request = httpx.Request("POST", "https://open.feishu.cn/mock")
    return httpx.Response(status_code=status_code, text=text, request=request)


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
async def test_request_with_retry_retries_on_transient_gateway_error() -> None:
    client = FeishuClient(auth_service=FakeAuthService(), max_retries=3, backoff_base=0.0)
    client._client = FakeHttpClient(  # type: ignore[assignment]
        [
            _text_response(502, "Bad Gateway"),
            _response(200, {"code": 0, "data": {"ok": True}}),
        ]
    )

    response = await client.request_with_retry("POST", "https://open.feishu.cn/mock")
    payload = response.json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert client._client.calls == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_request_with_retry_returns_last_transient_error_after_retries() -> None:
    client = FeishuClient(auth_service=FakeAuthService(), max_retries=2, backoff_base=0.0)
    client._client = FakeHttpClient(  # type: ignore[assignment]
        [
            _text_response(502, "Bad Gateway"),
            _text_response(503, "Service Unavailable"),
        ]
    )

    response = await client.request_with_retry("POST", "https://open.feishu.cn/mock")

    assert response.status_code == 503
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


@pytest.mark.asyncio
async def test_snapshot_profile_denies_cloud_reads_before_authentication() -> None:
    auth = FakeAuthService()
    client = FeishuClient(
        auth_service=auth,
        config=AppConfig(runtime_profile=RuntimeProfile.snapshot_test),
    )

    with pytest.raises(CloudAccessDenied, match="snapshot_test"):
        await client.request("GET", "https://open.feishu.cn/open-apis/drive/v1/files")


@pytest.mark.asyncio
async def test_live_readonly_profile_denies_cloud_writes() -> None:
    client = FeishuClient(
        auth_service=FakeAuthService(),
        config=AppConfig(runtime_profile=RuntimeProfile.live_readonly),
    )

    with pytest.raises(CloudAccessDenied, match="只读"):
        await client.request("POST", "https://open.feishu.cn/open-apis/drive/v1/files")


@pytest.mark.asyncio
async def test_live_readonly_allows_semantically_read_only_export_request() -> None:
    client = FeishuClient(
        auth_service=FakeAuthService(),
        config=AppConfig(runtime_profile=RuntimeProfile.live_readonly),
    )
    client._client = FakeHttpClient([_response(200, {"code": 0})])  # type: ignore[assignment]

    response = await client.request(
        "POST", "https://open.feishu.cn/open-apis/drive/v1/export_tasks"
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_live_bidirectional_requires_allowlisted_cloud_root_scope() -> None:
    client = FeishuClient(
        auth_service=FakeAuthService(),
        config=AppConfig(
            runtime_profile=RuntimeProfile.live_bidirectional,
            allowed_cloud_roots=["allowed-root"],
        ),
    )

    with pytest.raises(CloudAccessDenied, match="allowlist"):
        await client.request("POST", "https://open.feishu.cn/open-apis/drive/v1/files")

    with cloud_root_scope("allowed-root"):
        client._client = FakeHttpClient([_response(200, {"code": 0})])  # type: ignore[assignment]
        response = await client.request(
            "POST", "https://open.feishu.cn/open-apis/drive/v1/files"
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_request_acquires_rate_limit_token_before_http_call() -> None:
    limiter = FakeRateLimiter()
    client = FeishuClient(auth_service=FakeAuthService(), rate_limiter=limiter)
    client._client = FakeHttpClient([_response(200, {"code": 0})])  # type: ignore[assignment]

    await client.request("GET", "https://open.feishu.cn/open-apis/drive/v1/files")

    assert limiter.calls == 1


@pytest.mark.asyncio
async def test_request_audit_excludes_authorization_and_payload(tmp_path) -> None:
    audit_path = tmp_path / "cloud-audit.jsonl"
    client = FeishuClient(
        auth_service=FakeAuthService(),
        config=AppConfig(cloud_audit_log=str(audit_path)),
    )
    client._client = FakeHttpClient([_response(200, {"code": 0})])  # type: ignore[assignment]

    await client.request(
        "GET",
        "https://open.feishu.cn/open-apis/drive/v1/files?folder_token=secret",
        json={"secret": "must-not-be-logged"},
    )

    record = json.loads(audit_path.read_text(encoding="utf-8").strip())
    assert record["method"] == "GET"
    assert record["endpoint"] == "/open-apis/drive/v1/files"
    assert record["http_status"] == 200
    assert record["feishu_code"] == 0
    serialized = json.dumps(record)
    assert "Authorization" not in serialized
    assert "must-not-be-logged" not in serialized
    assert "folder_token" not in serialized
