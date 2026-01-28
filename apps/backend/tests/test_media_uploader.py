import httpx
import pytest

from src.services.media_uploader import MediaUploader


class FakeClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str, dict]] = []

    async def request_with_retry(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        payload = self._responses.pop(0)
        request = httpx.Request(method, url)
        return httpx.Response(200, json=payload, request=request)

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_upload_image_uses_media_upload_all(tmp_path) -> None:
    responses = [{"code": 0, "data": {"file_token": "img-123"}}]
    client = FakeClient(responses)
    uploader = MediaUploader(client=client, default_parent_type="docx_image")

    image_path = tmp_path / "logo.png"
    image_path.write_bytes(b"pngdata")

    token = await uploader.upload_image(image_path, parent_node="doc123")
    assert token == "img-123"

    method, url, kwargs = client.requests[0]
    assert method == "POST"
    assert url.endswith("/open-apis/drive/v1/medias/upload_all")
    assert kwargs["data"]["file_name"] == "logo.png"
    assert kwargs["data"]["parent_type"] == "docx_image"
    assert kwargs["data"]["parent_node"] == "doc123"
    assert kwargs["data"]["size"] == str(len(b"pngdata"))
    assert kwargs["data"]["checksum"] == MediaUploader._adler32(b"pngdata")
    assert "files" in kwargs
