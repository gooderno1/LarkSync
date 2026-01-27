from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Iterable

from src.services.feishu_client import FeishuClient


class DocxServiceError(RuntimeError):
    pass


@dataclass
class ConvertResult:
    first_level_block_ids: list[str]
    blocks: list[dict[str, Any]]


class DocxService:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")

    async def replace_document_content(
        self, document_id: str, markdown: str, user_id_type: str = "open_id"
    ) -> None:
        items = await self.list_blocks(document_id, user_id_type=user_id_type)
        root_block = self._find_root_block(items)
        if not root_block:
            raise DocxServiceError("未找到文档根 Block")

        convert = await self.convert_markdown(markdown, user_id_type=user_id_type)

        children = root_block.get("children") or []
        if children:
            await self.delete_children(
                document_id=document_id,
                block_id=root_block["block_id"],
                start_index=0,
                end_index=len(children),
            )

        await self._create_from_convert(
            document_id=document_id,
            root_block_id=root_block["block_id"],
            convert=convert,
            user_id_type=user_id_type,
        )

    async def convert_markdown(
        self, markdown: str, user_id_type: str = "open_id"
    ) -> ConvertResult:
        payload = {"content_type": "markdown", "content": markdown}
        response = await self._request_json(
            "POST",
            f"{self._base_url}/open-apis/docx/documents/blocks/convert",
            params={"user_id_type": user_id_type},
            json=payload,
        )
        data = response.get("data")
        if not isinstance(data, dict):
            raise DocxServiceError("转换接口响应缺少 data")
        first_level_block_ids = data.get("first_level_block_ids")
        blocks = data.get("blocks")
        if not isinstance(first_level_block_ids, list) or not isinstance(blocks, list):
            raise DocxServiceError("转换接口响应缺少 blocks 信息")
        return ConvertResult(
            first_level_block_ids=first_level_block_ids,
            blocks=blocks,
        )

    async def list_blocks(
        self, document_id: str, user_id_type: str = "open_id"
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = {"page_size": 500, "user_id_type": user_id_type}
            if page_token:
                params["page_token"] = page_token
            response = await self._request_json(
                "GET",
                f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks",
                params=params,
            )
            data = response.get("data")
            if not isinstance(data, dict):
                raise DocxServiceError("获取块列表响应缺少 data")
            page_items = data.get("items", [])
            if isinstance(page_items, list):
                items.extend(page_items)
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break
        return items

    async def delete_children(
        self, document_id: str, block_id: str, start_index: int, end_index: int
    ) -> None:
        payload = {"start_index": start_index, "end_index": end_index}
        await self._request_json(
            "DELETE",
            f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/children/batch_delete",
            params={"client_token": str(uuid.uuid4()), "document_revision_id": -1},
            json=payload,
        )

    async def _create_from_convert(
        self,
        document_id: str,
        root_block_id: str,
        convert: ConvertResult,
        user_id_type: str,
    ) -> None:
        block_map = {block.get("block_id"): block for block in convert.blocks}
        children_map = {
            block.get("block_id"): block.get("children", [])
            for block in convert.blocks
        }
        await self._create_children_recursive(
            document_id=document_id,
            parent_block_id=root_block_id,
            child_ids=convert.first_level_block_ids,
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
        )

    async def _create_children_recursive(
        self,
        document_id: str,
        parent_block_id: str,
        child_ids: list[str],
        block_map: dict[str, dict[str, Any]],
        children_map: dict[str, list[str]],
        user_id_type: str,
    ) -> None:
        for chunk in _chunked(child_ids, 50):
            payload = {
                "children": [self._sanitize_block(block_map[child_id]) for child_id in chunk],
                "index": -1,
            }
            response = await self._request_json(
                "POST",
                f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
                params={
                    "client_token": str(uuid.uuid4()),
                    "document_revision_id": -1,
                    "user_id_type": user_id_type,
                },
                json=payload,
            )
            data = response.get("data") or {}
            created = data.get("children", [])
            if not isinstance(created, list):
                raise DocxServiceError("创建块响应缺少 children")

            for old_id, new_block in zip(chunk, created):
                new_id = new_block.get("block_id")
                if not new_id:
                    raise DocxServiceError("创建块响应缺少 block_id")
                old_children = children_map.get(old_id, [])
                if old_children:
                    await self._create_children_recursive(
                        document_id=document_id,
                        parent_block_id=new_id,
                        child_ids=old_children,
                        block_map=block_map,
                        children_map=children_map,
                        user_id_type=user_id_type,
                    )

    @staticmethod
    def _sanitize_block(block: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(block)
        cleaned.pop("block_id", None)
        cleaned.pop("parent_id", None)
        cleaned.pop("children", None)
        return cleaned

    @staticmethod
    def _find_root_block(items: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
        for item in items:
            if item.get("block_type") == 1 and not item.get("parent_id"):
                return item
        for item in items:
            if item.get("block_type") == 1:
                return item
        return next(iter(items), None)

    async def _request_json(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        response = await self._client.request_with_retry(method, url, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code", 0) != 0:
            raise DocxServiceError(payload.get("msg", "飞书 API 返回错误"))
        if not isinstance(payload, dict):
            raise DocxServiceError("飞书 API 响应格式错误")
        return payload


def _chunked(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]
