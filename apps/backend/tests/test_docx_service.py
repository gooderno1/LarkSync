import hashlib
import httpx
import pytest

from src.services.docx_service import ConvertResult, DocxService
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
        {
            "code": 0,
            "data": {
                "children": [{"block_id": "n1"}],
                "document_revision_id": 2,
                "client_token": "t2",
            },
        },
        {"code": 0, "data": {"document_revision_id": 1, "client_token": "t"}},
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    await service.replace_document_content("doc123", "# Title", update_mode="full")

    list_call = client.requests[0]
    assert list_call[0] == "GET"
    assert list_call[1].endswith("/open-apis/docx/v1/documents/doc123/blocks")

    convert_call = client.requests[1]
    assert convert_call[0] == "POST"
    assert convert_call[1].endswith("/open-apis/docx/v1/documents/blocks/convert")

    create_call = client.requests[2]
    assert create_call[0] == "POST"
    assert create_call[1].endswith(
        "/open-apis/docx/v1/documents/doc123/blocks/root/children"
    )
    child_payload = create_call[2]["json"]["children"][0]
    assert "block_id" not in child_payload
    assert "parent_id" not in child_payload
    assert "children" not in child_payload

    delete_call = client.requests[3]
    assert delete_call[0] == "DELETE"
    assert delete_call[1].endswith(
        "/open-apis/docx/v1/documents/doc123/blocks/root/children/batch_delete"
    )
    assert delete_call[2]["json"]["start_index"] == 0
    assert delete_call[2]["json"]["end_index"] == 2


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

    await service.replace_document_content("doc456", "- item", update_mode="full")

    assert len(client.requests) == 4
    assert client.requests[2][1].endswith(
        "/open-apis/docx/v1/documents/doc456/blocks/root/children"
    )
    assert client.requests[3][1].endswith(
        "/open-apis/docx/v1/documents/doc456/blocks/np1/children"
    )


@pytest.mark.asyncio
async def test_replace_document_content_uploads_local_images(tmp_path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    image_path = assets_dir / "logo.png"
    image_path.write_bytes(b"img")
    placeholder = f"[[LARKSYNC_IMAGE:{hashlib.sha1(str(image_path).encode('utf-8')).hexdigest()}]]"

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
                "first_level_block_ids": ["t1", "t2", "t3"],
                "blocks": [
                    {"block_id": "t1", "block_type": 2, "text": {"elements": []}},
                    {
                        "block_id": "t2",
                        "block_type": 2,
                        "text": {"elements": [{"text_run": {"content": placeholder}}]},
                    },
                    {"block_id": "t3", "block_type": 2, "text": {"elements": []}},
                ],
            },
        },
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
        {"code": 0, "data": {"file_token": "img-token"}},
        {"code": 0, "data": {"document_revision_id": 1, "client_token": "t"}},
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    markdown = "段落一\n\n![](assets/logo.png)\n\n段落二"

    await service.replace_document_content(
        "doc789", markdown, base_path=tmp_path.as_posix(), update_mode="full"
    )

    assert client.requests[1][1].endswith("/open-apis/docx/v1/documents/blocks/convert")

    create_call = client.requests[2]
    children_payload = create_call[2]["json"]["children"]
    assert len(children_payload) == 3
    image_blocks = [child for child in children_payload if child.get("block_type") == 27]
    assert image_blocks and image_blocks[0].get("image") == {}

    upload_call = client.requests[3]
    assert upload_call[1].endswith("/open-apis/drive/v1/medias/upload_all")
    assert upload_call[2]["data"]["parent_node"] == "n2"
    assert upload_call[2]["data"]["parent_type"] == "docx_image"


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
    ]
    client = FakeClient(responses)
    service = DocxService(client=client, media_uploader=FailingMediaUploader())

    markdown = "前文 ![](assets/docid/token.png) 后文"
    convert = await service.convert_markdown_with_images(
        markdown, document_id="docid", base_path=tmp_path
    )

    assert all(block.get("block_type") != 27 for block in convert.blocks)


@pytest.mark.asyncio
async def test_convert_markdown_patches_table_property() -> None:
    responses = [
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t1"],
                "blocks": [
                    {
                        "block_id": "t1",
                        "block_type": 31,
                        "table": {"cells": ["c1", "c2", "c3", "c4"]},
                    }
                ],
            },
        }
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    markdown = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    convert = await service.convert_markdown_with_images(
        markdown, document_id="doc-table"
    )

    table_block = next(
        block for block in convert.blocks if block.get("block_type") == 31
    )
    prop = (table_block.get("table") or {}).get("property") or {}
    assert prop.get("row_size") == 2
    assert prop.get("column_size") == 2


@pytest.mark.asyncio
async def test_partial_update_skips_when_duplicate_signatures() -> None:
    service = DocxService(client=FakeClient([]))
    current_blocks = [
        {"block_id": "root", "block_type": 1, "children": ["c1", "c2"]},
        {
            "block_id": "c1",
            "block_type": 2,
            "text": {"elements": [{"text_run": {"content": "same"}}]},
        },
        {
            "block_id": "c2",
            "block_type": 2,
            "text": {"elements": [{"text_run": {"content": "same"}}]},
        },
    ]
    convert = ConvertResult(
        first_level_block_ids=["n1", "n2"],
        blocks=[
            {
                "block_id": "n1",
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "same"}}]},
            },
            {
                "block_id": "n2",
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "same"}}]},
            },
        ],
    )
    applied = await service._apply_partial_update(
        document_id="doc-skip",
        root_block_id="root",
        current_children=["c1", "c2"],
        current_blocks=current_blocks,
        convert=convert,
        user_id_type="open_id",
        force=False,
    )
    assert applied is False


@pytest.mark.asyncio
async def test_partial_update_table_children_uses_cells() -> None:
    class SpyDocxService(DocxService):
        def __init__(self) -> None:
            super().__init__(client=FakeClient([]))
            self.children_map = None

        async def delete_children(self, *args, **kwargs) -> None:
            return None

        async def _create_children_recursive(self, *args, **kwargs) -> None:
            self.children_map = kwargs.get("children_map")

    service = SpyDocxService()
    current_blocks = [
        {"block_id": "root", "block_type": 1, "children": ["c1"]},
        {
            "block_id": "c1",
            "block_type": 2,
            "text": {"elements": [{"text_run": {"content": "old"}}]},
        },
    ]
    convert = ConvertResult(
        first_level_block_ids=["t1"],
        blocks=[
            {
                "block_id": "t1",
                "block_type": 31,
                "table": {"cells": ["cell1", "cell2"]},
            },
            {"block_id": "cell1", "block_type": 32, "children": []},
            {"block_id": "cell2", "block_type": 32, "children": []},
        ],
    )
    await service._apply_partial_update(
        document_id="doc-table",
        root_block_id="root",
        current_children=["c1"],
        current_blocks=current_blocks,
        convert=convert,
        user_id_type="open_id",
        force=True,
    )
    assert service.children_map is not None
    assert service.children_map.get("t1") == ["cell1", "cell2"]
