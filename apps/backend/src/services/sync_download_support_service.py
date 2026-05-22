from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Awaitable, Callable

from loguru import logger

from src.services.bitable_service import BitableService
from src.services.docx_service import DocxService
from src.services.drive_service import DriveNode, DriveService
from src.services.export_task_service import ExportTaskError, ExportTaskResult, ExportTaskService
from src.services.file_downloader import FileDownloader
from src.services.sheet_service import SheetService
from src.services.sync_link_service import SyncLinkItem
from src.services.sync_task_service import SyncTaskItem
from src.services.transcoder import DocxTranscoder

ParseMtime = Callable[[str | int | float | None], float]
ContainsLegacyDocxPlaceholder = Callable[[Path], bool]
ResolveTarget = Callable[[DriveNode], tuple[str, str]]
DocxFilename = Callable[[str], str]
ExportFilename = Callable[[str, str], str]
GenericFilename = Callable[[str], str]
ExtractExportSubId = Callable[[str | None, str], str | None]
GetLocalSignature = Callable[[Path], tuple[str, int, float] | None]


@dataclass(frozen=True)
class DownloadCandidate:
    node: DriveNode
    relative_dir: Path
    effective_token: str
    effective_type: str
    target_dir: Path
    target_path: Path
    mtime: float
    export_sub_id: str | None = None


class SyncDownloadSupportService:
    def __init__(
        self,
        *,
        export_extension_map: dict[str, str],
        parse_mtime: ParseMtime,
        contains_legacy_docx_placeholder: ContainsLegacyDocxPlaceholder,
        resolve_target: ResolveTarget,
        docx_filename: DocxFilename,
        export_filename: ExportFilename,
        generic_filename: GenericFilename,
        extract_export_sub_id: ExtractExportSubId,
        get_local_signature: GetLocalSignature,
    ) -> None:
        self._export_extension_map = dict(export_extension_map)
        self._parse_mtime = parse_mtime
        self._contains_legacy_docx_placeholder = contains_legacy_docx_placeholder
        self._resolve_target = resolve_target
        self._docx_filename = docx_filename
        self._export_filename = export_filename
        self._generic_filename = generic_filename
        self._extract_export_sub_id = extract_export_sub_id
        self._get_local_signature = get_local_signature

    def should_skip_download_for_unchanged(
        self,
        *,
        local_path: Path,
        cloud_mtime: float,
        persisted: SyncLinkItem | None,
        effective_token: str,
        effective_type: str,
    ) -> bool:
        if persisted is None:
            return False
        if persisted.cloud_token != effective_token:
            return False
        if not local_path.exists() or not local_path.is_file():
            return False
        if effective_type in {"doc", "docx"} and self._contains_legacy_docx_placeholder(
            local_path
        ):
            return False
        if persisted.cloud_mtime is not None and persisted.cloud_mtime >= (cloud_mtime - 1.0):
            if persisted.local_hash:
                signature = self._get_local_signature(local_path)
                if not signature:
                    return False
                return signature[0] == persisted.local_hash
            return True
        if persisted.updated_at >= (cloud_mtime - 1.0):
            if persisted.local_hash:
                signature = self._get_local_signature(local_path)
                if not signature:
                    return False
                return signature[0] == persisted.local_hash
            return True
        return False

    def build_download_candidate(
        self,
        task: SyncTaskItem,
        node: DriveNode,
        relative_dir: Path,
    ) -> DownloadCandidate:
        effective_token, effective_type = self._resolve_target(node)
        target_dir = Path(task.local_path) / relative_dir
        if effective_type in {"docx", "doc"}:
            filename = self._docx_filename(node.name)
        elif effective_type in self._export_extension_map:
            filename = self._export_filename(
                node.name,
                self._export_extension_map[effective_type],
            )
        else:
            filename = self._generic_filename(node.name)
        export_sub_id = self._extract_export_sub_id(node.url, effective_type)
        target_path = target_dir / filename
        return DownloadCandidate(
            node=node,
            relative_dir=relative_dir,
            effective_token=effective_token,
            effective_type=effective_type,
            target_dir=target_dir,
            target_path=target_path,
            mtime=self._parse_mtime(node.modified_time),
            export_sub_id=export_sub_id,
        )

    async def hydrate_export_sub_ids(
        self,
        candidates: list[DownloadCandidate],
        drive_service: DriveService,
        *,
        sheet_service: SheetService | None = None,
        bitable_service: BitableService | None = None,
    ) -> list[DownloadCandidate]:
        pending: list[tuple[str, str]] = []
        for candidate in candidates:
            if (
                candidate.effective_type in self._export_extension_map
                and not candidate.export_sub_id
            ):
                pending.append((candidate.effective_token, candidate.effective_type))
        if not pending:
            return candidates

        meta_map = {}
        batch_query = getattr(drive_service, "batch_query_metas", None)
        if batch_query is not None:
            try:
                meta_map = await batch_query(pending, with_url=True)
            except Exception as exc:
                logger.warning("补齐表格导出 sub_id 失败: {}", exc)

        enriched: list[DownloadCandidate] = []
        remaining: dict[tuple[str, str], list[int]] = {}
        for idx, candidate in enumerate(candidates):
            if (
                candidate.effective_type in self._export_extension_map
                and not candidate.export_sub_id
            ):
                meta = meta_map.get(candidate.effective_token)
                url = getattr(meta, "url", None) if meta else None
                sub_id = self._extract_export_sub_id(url, candidate.effective_type)
                if sub_id:
                    candidate = replace(candidate, export_sub_id=sub_id)
                else:
                    key = (candidate.effective_token, candidate.effective_type)
                    remaining.setdefault(key, []).append(idx)
            enriched.append(candidate)

        if not remaining:
            return enriched

        for (token, file_type), indices in remaining.items():
            if file_type == "sheet":
                if not sheet_service:
                    continue
                try:
                    sheet_ids = await sheet_service.list_sheet_ids(token)
                except Exception as exc:
                    logger.warning("获取 sheet 子表失败: token={} error={}", token, exc)
                    continue
                if not sheet_ids:
                    continue
                for idx in indices:
                    enriched[idx] = replace(enriched[idx], export_sub_id=sheet_ids[0])
                logger.info("补齐 sheet sub_id: token={} sheet_id={}", token, sheet_ids[0])
            elif file_type == "bitable":
                if not bitable_service:
                    continue
                try:
                    table_ids = await bitable_service.list_table_ids(token)
                except Exception as exc:
                    logger.warning("获取 bitable 子表失败: token={} error={}", token, exc)
                    continue
                if not table_ids:
                    continue
                for idx in indices:
                    enriched[idx] = replace(enriched[idx], export_sub_id=table_ids[0])
                logger.info("补齐 bitable sub_id: token={} table_id={}", token, table_ids[0])

        return enriched

    def select_download_candidates(
        self,
        candidates: list[DownloadCandidate],
        persisted_by_path: dict[str, SyncLinkItem],
    ) -> tuple[list[DownloadCandidate], list[DownloadCandidate]]:
        selected: dict[str, DownloadCandidate] = {}
        duplicated: list[DownloadCandidate] = []
        for candidate in candidates:
            key = str(candidate.target_path).lower()
            current = selected.get(key)
            if current is None:
                selected[key] = candidate
                continue
            persisted = persisted_by_path.get(str(candidate.target_path))
            chosen = self.choose_download_candidate(
                current=current,
                candidate=candidate,
                persisted=persisted,
            )
            if chosen is candidate:
                duplicated.append(current)
                selected[key] = candidate
            else:
                duplicated.append(candidate)
        return list(selected.values()), duplicated

    @staticmethod
    def choose_download_candidate(
        *,
        current: DownloadCandidate,
        candidate: DownloadCandidate,
        persisted: SyncLinkItem | None,
    ) -> DownloadCandidate:
        if persisted:
            current_match = current.effective_token == persisted.cloud_token
            candidate_match = candidate.effective_token == persisted.cloud_token
            if candidate_match and not current_match:
                return candidate
            if current_match and not candidate_match:
                return current
        if candidate.mtime > current.mtime:
            return candidate
        if candidate.mtime < current.mtime:
            return current
        type_priority = {
            "docx": 3,
            "doc": 3,
            "sheet": 2,
            "bitable": 2,
            "file": 2,
        }
        candidate_rank = type_priority.get(candidate.effective_type, 1)
        current_rank = type_priority.get(current.effective_type, 1)
        if candidate_rank > current_rank:
            return candidate
        return current

    async def download_docx(
        self,
        document_id: str,
        *,
        docx_service: DocxService,
        transcoder: DocxTranscoder,
        base_dir: Path | None = None,
        link_map: dict[str, Path] | None = None,
    ) -> str:
        blocks = await docx_service.list_blocks(document_id)
        return await transcoder.to_markdown(
            document_id,
            blocks,
            base_dir=base_dir,
            link_map=link_map,
        )

    async def download_exported_file(
        self,
        *,
        export_task_service: ExportTaskService,
        file_downloader: FileDownloader,
        file_token: str,
        file_type: str,
        target_path: Path,
        mtime: float,
        export_extension: str,
        export_sub_id: str | None,
        poll_attempts: int,
        poll_interval: float,
    ) -> None:
        attempts: list[str | None] = [None]
        if export_sub_id:
            attempts.append(export_sub_id)
        last_error: Exception | None = None
        last_sub_id: str | None = None
        for sub_id in attempts:
            last_sub_id = sub_id
            try:
                task = await export_task_service.create_export_task(
                    file_extension=export_extension,
                    file_token=file_token,
                    file_type=file_type,
                    sub_id=sub_id,
                )
                result = await self.wait_for_export_task(
                    export_task_service,
                    task.ticket,
                    file_token=file_token,
                    poll_attempts=poll_attempts,
                    poll_interval=poll_interval,
                )
                if not result.file_token:
                    raise RuntimeError("导出任务未返回文件 token")
                await file_downloader.download_exported_file(
                    file_token=result.file_token,
                    file_name=target_path.name,
                    target_dir=target_path.parent,
                    mtime=mtime,
                )
                return
            except (ExportTaskError, RuntimeError) as exc:
                last_error = exc
                if sub_id is None and export_sub_id:
                    logger.info(
                        "导出任务失败，尝试携带 sub_id 重试: token={} type={} sub_id={}",
                        file_token,
                        file_type,
                        export_sub_id,
                    )
                    continue
                break
        suffix = f" sub_id={last_sub_id}" if last_sub_id else ""
        raise RuntimeError(f"导出任务失败{suffix}: {last_error}") from last_error

    async def wait_for_export_task(
        self,
        export_task_service: ExportTaskService,
        ticket: str,
        *,
        file_token: str | None = None,
        poll_attempts: int,
        poll_interval: float,
    ) -> ExportTaskResult:
        last_error: str | None = None
        last_result: ExportTaskResult | None = None
        for attempt in range(poll_attempts):
            result = await export_task_service.get_export_task_result(
                ticket,
                file_token=file_token,
            )
            last_result = result
            job_status = result.job_status
            if job_status == 0:
                if result.file_token:
                    return result
                last_error = "导出任务未返回文件 token"
                break
            if result.job_error_msg:
                last_error = f"导出任务失败: status={job_status} msg={result.job_error_msg}"
                break
            if job_status not in (None, 1, 2):
                last_error = f"导出任务失败: status={job_status}"
                break
            if attempt < poll_attempts - 1:
                await asyncio.sleep(poll_interval)
        if last_error:
            raise RuntimeError(last_error)
        if last_result and last_result.job_status not in (None, 1, 2):
            detail = f"导出任务失败: status={last_result.job_status}"
            if last_result.job_error_msg:
                detail = f"{detail} msg={last_result.job_error_msg}"
            raise RuntimeError(detail)
        status_hint = (
            f" status={last_result.job_status}"
            if last_result and last_result.job_status is not None
            else ""
        )
        raise RuntimeError(f"导出任务超时{status_hint}")


__all__ = ["DownloadCandidate", "SyncDownloadSupportService"]
