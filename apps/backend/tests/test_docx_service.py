import hashlib
import httpx
import pytest

from src.services.docx_service import (
    ConvertResult,
    DocxService,
    _build_create_chunks,
    _normalize_markdown_for_convert,
    _patch_table_properties,
    _replace_continuation_placeholders,
)
from src.services.transcoder import BLOCK_TYPE_IMAGE, BLOCK_TYPE_TABLE, DocxParser
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


class StubFileUploader:
    class _Result:
        def __init__(self, file_token: str) -> None:
            self.file_token = file_token

    def __init__(self, file_token: str = "file-token") -> None:
        self.file_token = file_token
        self.calls: list[tuple[str, str, str, bool]] = []

    async def upload_file(
        self,
        file_path,
        parent_node: str,
        parent_type: str = "explorer",
        record_db: bool = True,
    ):
        self.calls.append((str(file_path), parent_node, parent_type, record_db))
        return self._Result(self.file_token)


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
                "children": [{"block_id": "n1"}]
            },
        },
        {"code": 0, "data": {"children": [{"block_id": "n2"}]}},
        {"code": 0, "data": {"file_token": "img-token"}},
        {"code": 0, "data": {"block": {"block_id": "n2"}}},
        {"code": 0, "data": {"children": [{"block_id": "n3"}]}},
        {"code": 0, "data": {"document_revision_id": 1, "client_token": "t"}},
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    markdown = "段落一\n\n![](assets/logo.png)\n\n段落二"

    await service.replace_document_content(
        "doc789", markdown, base_path=tmp_path.as_posix(), update_mode="full"
    )

    assert client.requests[1][1].endswith("/open-apis/docx/v1/documents/blocks/convert")

    create_calls = [
        call
        for call in client.requests
        if call[0] == "POST" and call[1].endswith("/open-apis/docx/v1/documents/doc789/blocks/root/children")
    ]
    assert len(create_calls) == 3
    payloads = [call[2]["json"]["children"][0] for call in create_calls]
    assert payloads[0]["block_type"] == 2
    assert payloads[1]["block_type"] == 27
    assert payloads[1].get("image") == {}
    assert payloads[2]["block_type"] == 2

    upload_call = next(
        call for call in client.requests if call[1].endswith("/open-apis/drive/v1/medias/upload_all")
    )
    assert upload_call[1].endswith("/open-apis/drive/v1/medias/upload_all")
    assert upload_call[2]["data"]["parent_node"] == "n2"
    assert upload_call[2]["data"]["parent_type"] == "docx_image"

    patch_call = next(
        call for call in client.requests if call[0] == "PATCH" and "/open-apis/docx/v1/documents/doc789/blocks/" in call[1]
    )
    assert patch_call[0] == "PATCH"
    assert patch_call[1].endswith("/open-apis/docx/v1/documents/doc789/blocks/n2")
    assert patch_call[2]["json"] == {"replace_image": {"token": "img-token"}}


@pytest.mark.asyncio
async def test_replace_document_content_uploads_local_file_link_as_file_block(tmp_path) -> None:
    attachments_dir = tmp_path / "attachments"
    attachments_dir.mkdir()
    file_path = attachments_dir / "方案.docx"
    file_path.write_bytes(b"doc")
    placeholder = f"[[LARKSYNC_FILE:{hashlib.sha1(str(file_path).encode('utf-8')).hexdigest()}]]"

    responses = [
        {
            "code": 0,
            "data": {
                "items": [{"block_id": "root", "block_type": 1, "children": []}],
                "has_more": False,
            },
        },
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t1"],
                "blocks": [
                    {
                        "block_id": "t1",
                        "block_type": 2,
                        "text": {"elements": [{"text_run": {"content": placeholder}}]},
                    }
                ],
            },
        },
        {
            "code": 0,
            "data": {
                "children": [
                    {
                        "block_id": "n1",
                        "block_type": 33,
                        "children": ["n1_file"],
                    }
                ],
            },
        },
        {"code": 0, "data": {"block": {"block_id": "n1_file"}}},
    ]
    client = FakeClient(responses)
    file_uploader = StubFileUploader(file_token="uploaded-file-token")
    service = DocxService(client=client, file_uploader=file_uploader)

    markdown = "[方案.docx](attachments/方案.docx)"
    await service.replace_document_content(
        "doc-file", markdown, base_path=tmp_path.as_posix(), update_mode="full"
    )

    assert len(file_uploader.calls) == 1
    upload_call = file_uploader.calls[0]
    assert upload_call[0].endswith("attachments\\方案.docx")
    assert upload_call[1] == "n1_file"
    assert upload_call[2] == "docx_file"
    assert upload_call[3] is False

    patch_call = client.requests[3]
    assert patch_call[0] == "PATCH"
    assert patch_call[1].endswith("/open-apis/docx/v1/documents/doc-file/blocks/n1_file")
    assert patch_call[2]["json"] == {"replace_file": {"token": "uploaded-file-token"}}


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


def test_normalize_markdown_for_convert_uses_tabs_for_nested_list() -> None:
    markdown = "1. 上级\n   - 硬件团队\n     1. 任务A\n     2. 任务B\n"
    normalized = _normalize_markdown_for_convert(markdown)

    assert "\t1. 任务A" in normalized
    assert "\t2. 任务B" in normalized
    assert "```" not in normalized


def test_normalize_markdown_for_convert_keeps_fenced_code() -> None:
    markdown = "```text\n    1. not-a-list\n```\n"
    normalized = _normalize_markdown_for_convert(markdown)

    assert normalized == markdown


def test_normalize_markdown_for_convert_rewrites_indented_image_in_list() -> None:
    markdown = "1. 条目\n   - 来源\n\n   ![](assets/a.png)\n"
    normalized = _normalize_markdown_for_convert(markdown)

    assert "\t- ![](assets/a.png)" in normalized


def test_normalize_markdown_for_convert_keeps_nested_context_after_indented_paragraph() -> None:
    markdown = "1. 条目\n   - 来源\n   说明文本\n   - 跟进\n"
    normalized = _normalize_markdown_for_convert(markdown)

    assert "\t\t[[LARKSYNC_CONTINUATION]]说明文本" in normalized
    assert "\t- 跟进" in normalized


def test_normalize_markdown_for_convert_keeps_multi_line_continuation_in_list() -> None:
    markdown = "1. 条目\n   - 产品定义：\n     一：内容A\n\n     二：内容B\n"
    normalized = _normalize_markdown_for_convert(markdown)

    assert "\t\t[[LARKSYNC_CONTINUATION]]一：内容A" in normalized
    assert "\t\t[[LARKSYNC_CONTINUATION]]二：内容B" in normalized


def test_normalize_markdown_for_convert_does_not_over_indent_deep_continuation() -> None:
    markdown = "1. 条目\n   - 子项\n      说明\n"
    normalized = _normalize_markdown_for_convert(markdown)

    assert "\t\t[[LARKSYNC_CONTINUATION]]说明" in normalized
    assert "\t\t\t[[LARKSYNC_CONTINUATION]]说明" not in normalized


def test_normalize_markdown_for_convert_does_not_touch_non_list_indented_text() -> None:
    markdown = "   普通缩进文本\n"
    normalized = _normalize_markdown_for_convert(markdown)

    assert normalized == markdown


def test_normalize_markdown_for_convert_keeps_deep_odd_space_nesting() -> None:
    markdown = "1. 主项\n         - 第四层\n"
    normalized = _normalize_markdown_for_convert(markdown)

    assert "\t\t\t\t- 第四层" in normalized


def test_replace_continuation_placeholders_keeps_list_when_placeholder_not_prefix() -> None:
    convert = ConvertResult(
        first_level_block_ids=["b1"],
        blocks=[
            {
                "block_id": "b1",
                "block_type": 12,
                "bullet": {
                    "elements": [
                        {"text_run": {"content": "建设方案\n"}},
                        {
                            "text_run": {
                                "content": "[[LARKSYNC_CONTINUATION]]附件.docx"
                            }
                        }
                    ]
                },
            }
        ],
    )

    patched = _replace_continuation_placeholders(convert)
    block = patched.blocks[0]
    assert block["block_type"] == 12
    assert block["bullet"]["elements"][0]["text_run"]["content"] == "建设方案\n"
    assert block["bullet"]["elements"][1]["text_run"]["content"] == "附件.docx"


def test_replace_continuation_placeholders_converts_prefix_placeholder_list_block_to_text() -> None:
    convert = ConvertResult(
        first_level_block_ids=["b1"],
        blocks=[
            {
                "block_id": "b1",
                "block_type": 13,
                "children": ["c1"],
                "ordered": {
                    "elements": [
                        {"text_run": {"content": "[[LARKSYNC_CONTINUATION]]**二、 后续**"}}
                    ]
                },
            }
        ],
    )

    patched = _replace_continuation_placeholders(convert)
    block = patched.blocks[0]
    assert block["block_type"] == 2
    assert block["text"]["elements"][0]["text_run"]["content"] == "**二、 后续**"
    assert block["children"] == ["c1"]


def test_replace_continuation_placeholders_reparents_converted_continuations() -> None:
    convert = ConvertResult(
        first_level_block_ids=["root"],
        blocks=[
            {
                "block_id": "root",
                "block_type": 13,
                "ordered": {"elements": [{"text_run": {"content": "主项"}}]},
                "children": ["item", "cont1", "cont2"],
            },
            {
                "block_id": "item",
                "block_type": 12,
                "bullet": {"elements": [{"text_run": {"content": "产品定义："}}]},
            },
            {
                "block_id": "cont1",
                "block_type": 12,
                "bullet": {
                    "elements": [
                        {"text_run": {"content": "[[LARKSYNC_CONTINUATION]]一：内容"}}
                    ]
                },
            },
            {
                "block_id": "cont2",
                "block_type": 12,
                "bullet": {
                    "elements": [
                        {"text_run": {"content": "[[LARKSYNC_CONTINUATION]]二：内容"}}
                    ]
                },
            },
        ],
    )

    patched = _replace_continuation_placeholders(convert)
    root = next(block for block in patched.blocks if block["block_id"] == "root")
    item = next(block for block in patched.blocks if block["block_id"] == "item")
    cont1 = next(block for block in patched.blocks if block["block_id"] == "cont1")
    cont2 = next(block for block in patched.blocks if block["block_id"] == "cont2")

    assert root["children"] == ["item"]
    assert item["children"] == ["cont1", "cont2"]
    assert cont1["block_type"] == 2
    assert cont2["block_type"] == 2


def test_replace_continuation_placeholders_keeps_sibling_for_non_continuation_context() -> None:
    convert = ConvertResult(
        first_level_block_ids=["root"],
        blocks=[
            {
                "block_id": "root",
                "block_type": 13,
                "ordered": {"elements": [{"text_run": {"content": "主项"}}]},
                "children": ["item", "cont1"],
            },
            {
                "block_id": "item",
                "block_type": 12,
                "bullet": {"elements": [{"text_run": {"content": "普通条目"}}]},
            },
            {
                "block_id": "cont1",
                "block_type": 12,
                "bullet": {
                    "elements": [
                        {"text_run": {"content": "[[LARKSYNC_CONTINUATION]]**二、 后续**"}}
                    ]
                },
            },
        ],
    )

    patched = _replace_continuation_placeholders(convert)
    root = next(block for block in patched.blocks if block["block_id"] == "root")
    item = next(block for block in patched.blocks if block["block_id"] == "item")
    cont1 = next(block for block in patched.blocks if block["block_id"] == "cont1")

    assert root["children"] == ["item", "cont1"]
    assert "children" not in item
    assert cont1["block_type"] == 2


def test_replace_placeholders_with_files_attaches_to_list_children(tmp_path) -> None:
    placeholder = "[[LARKSYNC_FILE:abc123]]"
    file_path = tmp_path / "附件.docx"
    file_path.write_bytes(b"doc")
    convert = ConvertResult(
        first_level_block_ids=["root"],
        blocks=[
            {
                "block_id": "root",
                "block_type": 13,
                "ordered": {"elements": [{"text_run": {"content": "主项"}}]},
                "children": ["item"],
            },
            {
                "block_id": "item",
                "block_type": 12,
                "bullet": {
                    "elements": [
                        {"text_run": {"content": f"建设方案\n{placeholder}"}}
                    ]
                },
            },
        ],
    )
    service = DocxService(client=FakeClient([]))

    patched = service._replace_placeholders_with_images(
        convert,
        placeholders={},
        image_paths={},
        file_placeholders={placeholder: "attachments/附件.docx"},
        file_paths={placeholder: file_path},
    )
    root = next(block for block in patched.blocks if block["block_id"] == "root")
    item = next(block for block in patched.blocks if block["block_id"] == "item")
    file_blocks = [block for block in patched.blocks if block.get("block_type") == 23]

    assert root["children"] == ["item"]
    assert len(item.get("children") or []) == 1
    assert file_blocks


def test_build_create_chunks_isolates_complex_blocks(tmp_path) -> None:
    child_ids = ["a", "b", "c", "d", "e"]
    image_paths = {"d": tmp_path / "d.png"}
    chunks = _build_create_chunks(
        child_ids=child_ids,
        children_map={"b": ["b1"]},
        image_paths=image_paths,
        file_paths=None,
        batch_size=3,
    )

    assert chunks == [["a"], ["b"], ["c"], ["d"], ["e"]]


def test_build_create_chunks_batches_simple_blocks() -> None:
    chunks = _build_create_chunks(
        child_ids=["a", "b", "c", "d"],
        children_map={},
        image_paths=None,
        file_paths=None,
        batch_size=3,
    )

    assert chunks == [["a", "b", "c"], ["d"]]


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


@pytest.mark.asyncio
async def test_partial_update_table_children_flattens_nested_cells() -> None:
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
                "table": {"cells": [["cell1", "cell2"], ["cell3"]]},
            },
            {"block_id": "cell1", "block_type": 32, "children": []},
            {"block_id": "cell2", "block_type": 32, "children": []},
            {"block_id": "cell3", "block_type": 32, "children": []},
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
    assert service.children_map.get("t1") == ["cell1", "cell2", "cell3"]


def test_sanitize_block_strips_table_cells() -> None:
    block = {
        "block_id": "tbl1",
        "block_type": BLOCK_TYPE_TABLE,
        "table": {
            "property": {"row_size": 2, "column_size": 2},
            "cells": [["c1", "c2"], ["c3", "c4"]],
        },
        "children": ["c1", "c2", "c3", "c4"],
    }
    cleaned = DocxService._sanitize_block(block)
    assert "block_id" not in cleaned
    assert "children" not in cleaned
    assert "cells" not in cleaned["table"]


def test_patch_table_properties_reshapes_flat_cells() -> None:
    convert = ConvertResult(
        first_level_block_ids=["t1"],
        blocks=[
            {
                "block_id": "t1",
                "block_type": BLOCK_TYPE_TABLE,
                "table": {
                    "cells": [
                        "row1colA",
                        "row1colB",
                        "row2colA",
                        "row2colB",
                    ]
                },
            },
        ],
    )
    markdown = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    patched = _patch_table_properties(convert, markdown)
    table = next(block for block in patched.blocks if block.get("block_id") == "t1")["table"]
    assert table["cells"] == [["row1colA", "row1colB"], ["row2colA", "row2colB"]]
    assert table["property"]["row_size"] == 2
    assert table["property"]["column_size"] == 2


@pytest.mark.asyncio
async def test_replace_document_content_populates_table_cells_without_creating_cells() -> None:
    responses = [
        {
            "code": 0,
            "data": {
                "items": [{"block_id": "root", "block_type": 1, "children": []}],
                "has_more": False,
            },
        },
        {
            "code": 0,
            "data": {
                "first_level_block_ids": ["t1"],
                "blocks": [
                    {
                        "block_id": "t1",
                        "block_type": 31,
                        "children": ["c1", "c2"],
                        "table": {"property": {"row_size": 1, "column_size": 2}},
                    },
                    {
                        "block_id": "c1",
                        "block_type": 32,
                        "children": ["p1"],
                        "table_cell": {},
                    },
                    {
                        "block_id": "c2",
                        "block_type": 32,
                        "children": ["p2"],
                        "table_cell": {},
                    },
                    {
                        "block_id": "p1",
                        "block_type": 2,
                        "text": {"elements": [{"text_run": {"content": "A"}}]},
                    },
                    {
                        "block_id": "p2",
                        "block_type": 2,
                        "text": {"elements": [{"text_run": {"content": "B"}}]},
                    },
                ],
            },
        },
        {
            "code": 0,
            "data": {
                "children": [
                    {
                        "block_id": "new_table",
                        "block_type": 31,
                        "children": ["cellA", "cellB"],
                    }
                ]
            },
        },
        {"code": 0, "data": {"children": [{"block_id": "np1"}]}},
        {"code": 0, "data": {"children": [{"block_id": "np2"}]}},
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    await service.replace_document_content("doc-table", "| A | B |", update_mode="full")

    urls = [req[1] for req in client.requests]
    assert any(url.endswith("/blocks/cellA/children") for url in urls)
    assert any(url.endswith("/blocks/cellB/children") for url in urls)
    assert not any(url.endswith("/blocks/new_table/children") for url in urls)


@pytest.mark.asyncio
async def test_delete_children_batches_large_range() -> None:
    responses = [
        {"code": 0, "data": {"document_revision_id": 1}},
        {"code": 0, "data": {"document_revision_id": 1}},
        {"code": 0, "data": {"document_revision_id": 1}},
    ]
    client = FakeClient(responses)
    service = DocxService(client=client)

    await service.delete_children("doc-batch", "root", start_index=0, end_index=120)

    assert len(client.requests) == 3
    payloads = [req[2]["json"] for req in client.requests]
    assert payloads[0] == {"start_index": 70, "end_index": 120}
    assert payloads[1] == {"start_index": 20, "end_index": 70}
    assert payloads[2] == {"start_index": 0, "end_index": 20}


def test_replace_placeholders_keeps_list_text_and_appends_image(tmp_path) -> None:
    image_path = tmp_path / "inline.png"
    image_path.write_bytes(b"img")
    placeholder = "[[LARKSYNC_IMAGE:test-inline]]"
    convert = ConvertResult(
        first_level_block_ids=["b1"],
        blocks=[
            {
                "block_id": "b1",
                "block_type": 12,
                "bullet": {
                    "elements": [
                        {
                            "text_run": {
                                "content": f"客户回复\n{placeholder}",
                                "text_element_style": {
                                    "bold": False,
                                    "inline_code": False,
                                    "italic": False,
                                    "strikethrough": False,
                                    "underline": False,
                                },
                            }
                        }
                    ]
                },
            }
        ],
    )
    service = DocxService(client=FakeClient([]))
    patched = service._replace_placeholders_with_images(
        convert,
        placeholders={placeholder: "assets/inline.png"},
        image_paths={placeholder: image_path},
    )

    block_map = {block["block_id"]: block for block in patched.blocks}
    parser = DocxParser(patched.blocks)
    assert block_map["b1"]["block_type"] == 12
    assert parser.text_from_block(block_map["b1"]) == "客户回复"
    assert patched.first_level_block_ids == ["b1"]
    image_id = block_map["b1"]["children"][0]
    assert block_map[image_id]["block_type"] == BLOCK_TYPE_IMAGE
    assert all("LARKSYNC_IMAGE" not in str(block) for block in patched.blocks)


def test_replace_placeholders_turns_empty_list_item_into_image(tmp_path) -> None:
    image_path = tmp_path / "list.png"
    image_path.write_bytes(b"img")
    placeholder = "[[LARKSYNC_IMAGE:list-only]]"
    convert = ConvertResult(
        first_level_block_ids=["b1"],
        blocks=[
            {
                "block_id": "b1",
                "block_type": 12,
                "bullet": {
                    "elements": [
                        {
                            "text_run": {
                                "content": placeholder,
                                "text_element_style": {
                                    "bold": False,
                                    "inline_code": False,
                                    "italic": False,
                                    "strikethrough": False,
                                    "underline": False,
                                },
                            }
                        }
                    ]
                },
            }
        ],
    )
    service = DocxService(client=FakeClient([]))
    patched = service._replace_placeholders_with_images(
        convert,
        placeholders={placeholder: "assets/list.png"},
        image_paths={placeholder: image_path},
    )

    block_map = {block["block_id"]: block for block in patched.blocks}
    assert len(patched.first_level_block_ids) == 1
    assert block_map["b1"]["block_type"] == BLOCK_TYPE_IMAGE


def test_replace_placeholders_turns_pure_text_into_image_blocks(tmp_path) -> None:
    image_a = tmp_path / "a.png"
    image_b = tmp_path / "b.png"
    image_a.write_bytes(b"a")
    image_b.write_bytes(b"b")
    placeholder_a = "[[LARKSYNC_IMAGE:hash-a]]"
    placeholder_b = "[[LARKSYNC_IMAGE:hash-b]]"
    convert = ConvertResult(
        first_level_block_ids=["t1"],
        blocks=[
            {
                "block_id": "t1",
                "block_type": 2,
                "text": {
                    "elements": [
                        {
                            "text_run": {
                                "content": f"{placeholder_a}\n{placeholder_b}",
                                "text_element_style": {
                                    "bold": False,
                                    "inline_code": False,
                                    "italic": False,
                                    "strikethrough": False,
                                    "underline": False,
                                },
                            }
                        }
                    ]
                },
            }
        ],
    )
    service = DocxService(client=FakeClient([]))
    patched = service._replace_placeholders_with_images(
        convert,
        placeholders={
            placeholder_a: "assets/a.png",
            placeholder_b: "assets/b.png",
        },
        image_paths={
            placeholder_a: image_a,
            placeholder_b: image_b,
        },
    )

    block_map = {block["block_id"]: block for block in patched.blocks}
    assert patched.first_level_block_ids[0] == "t1"
    assert len(patched.first_level_block_ids) == 2
    first = patched.first_level_block_ids[0]
    second = patched.first_level_block_ids[1]
    assert block_map[first]["block_type"] == BLOCK_TYPE_IMAGE
    assert block_map[second]["block_type"] == BLOCK_TYPE_IMAGE
    assert all("LARKSYNC_IMAGE" not in str(block) for block in patched.blocks)


def test_replace_placeholders_in_text_inserts_image_sibling(tmp_path) -> None:
    image_path = tmp_path / "text.png"
    image_path.write_bytes(b"img")
    placeholder = "[[LARKSYNC_IMAGE:text-inline]]"
    convert = ConvertResult(
        first_level_block_ids=["t1"],
        blocks=[
            {
                "block_id": "t1",
                "block_type": 2,
                "text": {
                    "elements": [
                        {
                            "text_run": {
                                "content": f"前缀 {placeholder} 后缀",
                                "text_element_style": {
                                    "bold": False,
                                    "inline_code": False,
                                    "italic": False,
                                    "strikethrough": False,
                                    "underline": False,
                                },
                            }
                        }
                    ]
                },
            }
        ],
    )
    service = DocxService(client=FakeClient([]))
    patched = service._replace_placeholders_with_images(
        convert,
        placeholders={placeholder: "assets/text.png"},
        image_paths={placeholder: image_path},
    )

    block_map = {block["block_id"]: block for block in patched.blocks}
    parser = DocxParser(patched.blocks)
    assert parser.text_from_block(block_map["t1"]) == "前缀  后缀"
    assert len(patched.first_level_block_ids) == 2
    image_id = patched.first_level_block_ids[1]
    assert block_map[image_id]["block_type"] == BLOCK_TYPE_IMAGE
