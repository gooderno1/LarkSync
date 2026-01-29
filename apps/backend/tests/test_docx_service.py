import httpx
import pytest

from src.services.docx_service import DocxService
from src.services.media_uploader import MediaUploadError


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


class FailingMediaUploader:
    async def upload_image(self, file_path, parent_node: str, parent_type: str | None = None) -> str:
        raise MediaUploadError("图片不存在")


@pytest.mark.asyncio
async def test_replace_document_content_clears_and_creates() -> None:
    responses = [
        {
            "code": 0,
            "data": {
                "items": [
                    {"block_id": "root", "block_type": 1, "children": ["c1", "c2"]}
                ],
                "has_more": False,
            },
        },
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t1"],
                "blocks": [
                    {"block_id": "t1", "block_type": 2, "text": {"elements": []}}
                ],
            },
        },
        {"code": 0, "data": {"document_revision_id": 1, "client_token": "t"}},
        {
            "code": 0,
            "data": {
                "children": [{"block_id": "n1"}],
                "document_revision_id": 2,
                "client_token": "t2",
            },
        },
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    await service.replace_document_content("doc123", "# Title")

    list_call = client.requests[0]
    assert list_call[0] == "GET"
    assert list_call[1].endswith("/open-apis/docx/v1/documents/doc123/blocks")

    convert_call = client.requests[1]
    assert convert_call[0] == "POST"
    assert convert_call[1].endswith("/open-apis/docx/v1/documents/blocks/convert")

    delete_call = client.requests[2]
    assert delete_call[0] == "DELETE"
    assert delete_call[1].endswith(
        "/open-apis/docx/v1/documents/doc123/blocks/root/children/batch_delete"
    )
    assert delete_call[2]["json"]["start_index"] == 0
    assert delete_call[2]["json"]["end_index"] == 2

    create_call = client.requests[3]
    assert create_call[0] == "POST"
    assert create_call[1].endswith(
        "/open-apis/docx/v1/documents/doc123/blocks/root/children"
    )
    child_payload = create_call[2]["json"]["children"][0]
    assert "block_id" not in child_payload
    assert "parent_id" not in child_payload
    assert "children" not in child_payload


@pytest.mark.asyncio
async def test_replace_document_content_creates_nested_children() -> None:
    responses = [
        {
            "code": 0,
            "data": {
                "items": [
                    {"block_id": "root", "block_type": 1, "children": []}
                ],
                "has_more": False,
            },
        },
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["p1"],
                "blocks": [
                    {
                        "block_id": "p1",
                        "block_type": 12,
                        "children": ["c1"],
                        "bullet": {"elements": []},
                    },
                    {"block_id": "c1", "block_type": 2, "text": {"elements": []}},
                ],
            },
        },
        {
            "code": 0,
            "data": {
                "children": [{"block_id": "np1"}],
                "document_revision_id": 3,
                "client_token": "t3",
            },
        },
        {
            "code": 0,
            "data": {
                "children": [{"block_id": "nc1"}],
                "document_revision_id": 4,
                "client_token": "t4",
            },
        },
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    await service.replace_document_content("doc456", "- item")

    assert len(client.requests) == 4
    assert client.requests[2][1].endswith(
        "/open-apis/docx/v1/documents/doc456/blocks/root/children"
    )
    assert client.requests[3][1].endswith(
        "/open-apis/docx/v1/documents/doc456/blocks/np1/children"
    )


@pytest.mark.asyncio
async def test_replace_document_content_uploads_local_images(tmp_path) -> None:
    responses = [
        {
            "code": 0,
            "data": {
                "items": [
                    {"block_id": "root", "block_type": 1, "children": ["c1"]}
                ],
                "has_more": False,
            },
        },
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t1"],
                "blocks": [
                    {"block_id": "t1", "block_type": 2, "text": {"elements": []}}
                ],
            },
        },
        {"code": 0, "data": {"file_token": "img-token"}},
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t2"],
                "blocks": [
                    {"block_id": "t2", "block_type": 2, "text": {"elements": []}}
                ],
            },
        },
        {"code": 0, "data": {"document_revision_id": 1, "client_token": "t"}},
        {
            "code": 0,
            "data": {
                "children": [
                    {"block_id": "n1"},
                    {"block_id": "n2"},
                    {"block_id": "n3"},
                ]
            },
        },
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    image_path = assets_dir / "logo.png"
    image_path.write_bytes(b"img")

    markdown = "段落一\n\n![](assets/logo.png)\n\n段落二"

    await service.replace_document_content(
        "doc789", markdown, base_path=tmp_path.as_posix()
    )

    assert client.requests[1][1].endswith("/open-apis/docx/v1/documents/blocks/convert")
    assert client.requests[2][1].endswith("/open-apis/drive/v1/medias/upload_all")
    assert client.requests[2][2]["data"]["parent_node"] == "doc789"
    assert client.requests[2][2]["data"]["parent_type"] == "docx_image"

    create_call = client.requests[5]
    children_payload = create_call[2]["json"]["children"]
    assert len(children_payload) == 3
    assert any(child.get("image", {}).get("token") == "img-token" for child in children_payload)


@pytest.mark.asyncio
async def test_convert_markdown_with_images_falls_back_on_missing_image(tmp_path) -> None:
    responses = [
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t1"],
                "blocks": [
                    {"block_id": "t1", "block_type": 2, "text": {"elements": []}}
                ],
            },
        },
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t2"],
                "blocks": [
                    {"block_id": "t2", "block_type": 2, "text": {"elements": []}}
                ],
            },
        },
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t3"],
                "blocks": [
                    {"block_id": "t3", "block_type": 2, "text": {"elements": []}}
                ],
            },
        },
    ]
    client = FakeClient(responses)
    service = DocxService(client=client, media_uploader=FailingMediaUploader())

    markdown = "前文 ![](assets/docid/token.png) 后文"
    convert = await service.convert_markdown_with_images(
        markdown, document_id="docid", base_path=tmp_path
    )

    assert all(block.get("block_type") != 27 for block in convert.blocks)
