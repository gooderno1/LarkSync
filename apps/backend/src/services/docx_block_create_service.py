from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

from loguru import logger

from src.services.file_uploader import FileUploadError
from src.services.media_uploader import MediaUploadError
from src.services.transcoder import BLOCK_TYPE_FILE, BLOCK_TYPE_TABLE

RequestJsonFn = Callable[..., Awaitable[dict[str, Any]]]
SanitizeBlockFn = Callable[[dict[str, Any]], dict[str, Any]]
ReplaceImageBlockFn = Callable[..., Awaitable[None]]
ReplaceFileBlockFn = Callable[..., Awaitable[None]]
PopulateTableCellsFn = Callable[..., Awaitable[None]]
FallbackTableBlockFn = Callable[..., Awaitable[bool]]
SummarizeBlockTypesFn = Callable[[Iterable[dict[str, Any]]], dict[int | None, int]]
TruncatePayloadFn = Callable[[dict[str, Any], int], str]


def _chunked(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def build_create_chunks(
    *,
    child_ids: list[str],
    children_map: dict[str, list[str]],
    image_paths: dict[str, Path] | None,
    file_paths: dict[str, Path] | None,
    batch_size: int = 50,
) -> list[list[str]]:
    chunks: list[list[str]] = []
    buffered: list[str] = []
    for child_id in child_ids:
        has_nested = bool(children_map.get(child_id))
        has_asset = bool(
            (image_paths and child_id in image_paths)
            or (file_paths and child_id in file_paths)
        )
        if has_nested or has_asset:
            if buffered:
                chunks.extend(list(_chunked(buffered, batch_size)))
                buffered = []
            chunks.append([child_id])
            continue
        buffered.append(child_id)

    if buffered:
        chunks.extend(list(_chunked(buffered, batch_size)))
    return chunks


def extract_file_block_id(created_block: dict[str, Any]) -> str | None:
    block_id = created_block.get("block_id")
    if created_block.get("block_type") == BLOCK_TYPE_FILE and isinstance(block_id, str):
        return block_id
    children = created_block.get("children") or []
    if children and isinstance(children[0], str):
        return children[0]
    if isinstance(block_id, str):
        return block_id
    return None


class DocxBlockCreateService:
    def __init__(
        self,
        *,
        request_json: RequestJsonFn,
        sanitize_block: SanitizeBlockFn,
        replace_image_block: ReplaceImageBlockFn,
        replace_file_block: ReplaceFileBlockFn,
        populate_table_cells: PopulateTableCellsFn,
        fallback_table_block_without_code: FallbackTableBlockFn,
        summarize_block_types: SummarizeBlockTypesFn,
        truncate_payload: TruncatePayloadFn,
        media_uploader: Any,
        file_uploader: Any,
        base_url: str,
        image_parent_type: str,
        file_parent_type: str,
        service_error_cls: type[Exception],
    ) -> None:
        self._request_json = request_json
        self._sanitize_block = sanitize_block
        self._replace_image_block = replace_image_block
        self._replace_file_block = replace_file_block
        self._populate_table_cells = populate_table_cells
        self._fallback_table_block_without_code = fallback_table_block_without_code
        self._summarize_block_types = summarize_block_types
        self._truncate_payload = truncate_payload
        self._media_uploader = media_uploader
        self._file_uploader = file_uploader
        self._base_url = base_url.rstrip("/")
        self._image_parent_type = image_parent_type
        self._file_parent_type = file_parent_type
        self._service_error_cls = service_error_cls

    async def create_children_recursive(
        self,
        *,
        document_id: str,
        parent_block_id: str,
        child_ids: list[str],
        block_map: dict[str, dict[str, Any]],
        children_map: dict[str, list[str]],
        user_id_type: str,
        insert_index: int = -1,
        image_paths: dict[str, Path] | None = None,
        file_paths: dict[str, Path] | None = None,
        error_flag: dict[str, bool] | None = None,
    ) -> None:
        next_index = insert_index
        create_chunks = build_create_chunks(
            child_ids=child_ids,
            children_map=children_map,
            image_paths=image_paths,
            file_paths=file_paths,
        )
        for chunk in create_chunks:
            logger.info(
                "创建子块: document_id={} parent={} size={} types={}",
                document_id,
                parent_block_id,
                len(chunk),
                self._summarize_block_types([block_map[child_id] for child_id in chunk]),
            )
            payload = {
                "children": [self._sanitize_block(block_map[child_id]) for child_id in chunk],
            }
            if next_index >= 0:
                payload["index"] = next_index
            image_uploads: list[tuple[int, Path]] = []
            file_uploads: list[tuple[int, Path]] = []
            if image_paths:
                for idx, child_id in enumerate(chunk):
                    image_path = image_paths.get(child_id)
                    if image_path:
                        image_uploads.append((idx, image_path))
            if file_paths:
                for idx, child_id in enumerate(chunk):
                    file_path = file_paths.get(child_id)
                    if file_path:
                        file_uploads.append((idx, file_path))
            if next_index >= 0:
                next_index += len(chunk)
            try:
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
            except Exception as exc:
                await self.handle_create_children_error(
                    exc,
                    document_id=document_id,
                    parent_block_id=parent_block_id,
                    chunk=chunk,
                    block_map=block_map,
                    children_map=children_map,
                    user_id_type=user_id_type,
                    image_paths=image_paths,
                    file_paths=file_paths,
                    insert_index=insert_index,
                    error_flag=error_flag,
                )
                continue
            data = response.get("data") or {}
            created = data.get("children", [])
            if not isinstance(created, list):
                raise self._service_error_cls("创建块响应缺少 children")

            if image_uploads:
                await self._upload_created_images(
                    created=created,
                    image_uploads=image_uploads,
                    document_id=document_id,
                    user_id_type=user_id_type,
                )

            if file_uploads:
                await self._upload_created_files(
                    created=created,
                    file_uploads=file_uploads,
                    document_id=document_id,
                    user_id_type=user_id_type,
                )

            for old_id, new_block in zip(chunk, created):
                new_id = new_block.get("block_id")
                if not new_id:
                    raise self._service_error_cls("创建块响应缺少 block_id")
                old_block = block_map.get(old_id, {})
                if old_block.get("block_type") == BLOCK_TYPE_TABLE:
                    await self._populate_table_cells(
                        document_id=document_id,
                        table_block=new_block,
                        source_table_block=old_block,
                        block_map=block_map,
                        children_map=children_map,
                        user_id_type=user_id_type,
                        image_paths=image_paths,
                        file_paths=file_paths,
                        error_flag=error_flag,
                    )
                    continue
                old_children = children_map.get(old_id, [])
                if old_children:
                    await self.create_children_recursive(
                        document_id=document_id,
                        parent_block_id=new_id,
                        child_ids=old_children,
                        block_map=block_map,
                        children_map=children_map,
                        user_id_type=user_id_type,
                        insert_index=-1,
                        image_paths=image_paths,
                        file_paths=file_paths,
                        error_flag=error_flag,
                    )

    async def handle_create_children_error(
        self,
        exc: Exception,
        *,
        document_id: str,
        parent_block_id: str,
        chunk: list[str],
        block_map: dict[str, dict[str, Any]],
        children_map: dict[str, list[str]],
        user_id_type: str,
        image_paths: dict[str, Path] | None = None,
        file_paths: dict[str, Path] | None = None,
        insert_index: int = -1,
        error_flag: dict[str, bool] | None = None,
        rate_limit_retry: int = 0,
    ) -> None:
        exc_str = str(exc).lower()
        is_rate_limit = "frequency limit" in exc_str or "99991400" in exc_str

        if is_rate_limit and rate_limit_retry < 3:
            delay = 2.0 * (2 ** rate_limit_retry)
            logger.warning(
                "频率限制，延迟 {:.0f}s 后整体重试: document_id={} parent={} size={} attempt={}",
                delay,
                document_id,
                parent_block_id,
                len(chunk),
                rate_limit_retry + 1,
            )
            await asyncio.sleep(delay)
            try:
                await self.create_children_recursive(
                    document_id=document_id,
                    parent_block_id=parent_block_id,
                    child_ids=chunk,
                    block_map=block_map,
                    children_map=children_map,
                    user_id_type=user_id_type,
                    insert_index=insert_index,
                    image_paths=image_paths,
                    file_paths=file_paths,
                    error_flag=error_flag,
                )
            except Exception as retry_exc:
                await self.handle_create_children_error(
                    retry_exc,
                    document_id=document_id,
                    parent_block_id=parent_block_id,
                    chunk=chunk,
                    block_map=block_map,
                    children_map=children_map,
                    user_id_type=user_id_type,
                    image_paths=image_paths,
                    file_paths=file_paths,
                    insert_index=insert_index,
                    error_flag=error_flag,
                    rate_limit_retry=rate_limit_retry + 1,
                )
            return

        logger.warning(
            "创建子块失败，准备拆分重试: document_id={} parent={} size={} error={}",
            document_id,
            parent_block_id,
            len(chunk),
            exc,
        )
        if len(chunk) <= 1:
            if not chunk:
                return
            block_id = chunk[0]
            raw_block = block_map[block_id]
            if raw_block.get("block_type") == BLOCK_TYPE_TABLE:
                fallback_applied = await self._fallback_table_block_without_code(
                    document_id=document_id,
                    parent_block_id=parent_block_id,
                    table_block_id=block_id,
                    block_map=block_map,
                    user_id_type=user_id_type,
                    insert_index=insert_index,
                    error_flag=error_flag,
                )
                if fallback_applied:
                    return
            block = self._sanitize_block(raw_block)
            logger.error(
                "无效块已跳过: document_id={} parent={} block_id={} block_type={} keys={} payload={}",
                document_id,
                parent_block_id,
                block_id,
                block.get("block_type"),
                sorted(block.keys()),
                self._truncate_payload(block),
            )
            if error_flag is not None:
                error_flag["error"] = True
            return
        mid = len(chunk) // 2
        await self.create_children_recursive(
            document_id=document_id,
            parent_block_id=parent_block_id,
            child_ids=chunk[:mid],
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
            insert_index=insert_index,
            image_paths=image_paths,
            file_paths=file_paths,
            error_flag=error_flag,
        )
        await self.create_children_recursive(
            document_id=document_id,
            parent_block_id=parent_block_id,
            child_ids=chunk[mid:],
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
            insert_index=insert_index if insert_index < 0 else insert_index + mid,
            image_paths=image_paths,
            file_paths=file_paths,
            error_flag=error_flag,
        )

    async def _upload_created_images(
        self,
        *,
        created: list[dict[str, Any]],
        image_uploads: list[tuple[int, Path]],
        document_id: str,
        user_id_type: str,
    ) -> None:
        for idx, image_path in image_uploads:
            if idx >= len(created):
                continue
            new_id = created[idx].get("block_id")
            if not new_id:
                continue
            try:
                token = await self._media_uploader.upload_image(
                    image_path,
                    parent_node=new_id,
                    parent_type=self._image_parent_type,
                )
                await self._replace_image_block(
                    document_id=document_id,
                    block_id=new_id,
                    token=token,
                    image_path=image_path,
                    user_id_type=user_id_type,
                )
            except MediaUploadError as exc:
                logger.error(
                    "图片上传失败: document_id={} block_id={} path={} error={}",
                    document_id,
                    new_id,
                    image_path,
                    exc,
                )
            except Exception as exc:
                logger.error(
                    "图片块回填失败: document_id={} block_id={} path={} error={}",
                    document_id,
                    new_id,
                    image_path,
                    exc,
                )

    async def _upload_created_files(
        self,
        *,
        created: list[dict[str, Any]],
        file_uploads: list[tuple[int, Path]],
        document_id: str,
        user_id_type: str,
    ) -> None:
        for idx, file_path in file_uploads:
            if idx >= len(created):
                continue
            new_block = created[idx]
            target_file_block_id = extract_file_block_id(new_block)
            if not target_file_block_id:
                logger.error(
                    "附件块回填失败: document_id={} reason=missing_file_block path={} block={}",
                    document_id,
                    file_path,
                    self._truncate_payload(new_block),
                )
                continue
            try:
                upload = await self._file_uploader.upload_file(
                    file_path=file_path,
                    parent_node=target_file_block_id,
                    parent_type=self._file_parent_type,
                    record_db=False,
                )
                await self._replace_file_block(
                    document_id=document_id,
                    block_id=target_file_block_id,
                    token=upload.file_token,
                    user_id_type=user_id_type,
                )
            except FileUploadError as exc:
                logger.error(
                    "附件上传失败: document_id={} block_id={} path={} error={}",
                    document_id,
                    target_file_block_id,
                    file_path,
                    exc,
                )
            except Exception as exc:
                logger.error(
                    "附件块回填失败: document_id={} block_id={} path={} error={}",
                    document_id,
                    target_file_block_id,
                    file_path,
                    exc,
                )


__all__ = [
    "DocxBlockCreateService",
    "build_create_chunks",
    "extract_file_block_id",
]
