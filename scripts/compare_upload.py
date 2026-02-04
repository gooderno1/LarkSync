import argparse
import asyncio
from datetime import datetime
from pathlib import Path
import difflib

from src.services.docx_service import DocxService
from src.services.drive_service import DriveService
from src.services.file_uploader import FileUploader
from src.services.import_task_service import ImportTaskService
from src.services.sync_link_service import SyncLinkService
from src.services.sync_runner import SyncTaskRunner
from src.services.sync_task_service import SyncTaskService
from src.services.transcoder import DocxTranscoder
from src.db.session import init_db


async def _download_markdown(
    docx_service: DocxService,
    transcoder: DocxTranscoder,
    document_id: str,
    output_path: Path,
) -> None:
    blocks = await docx_service.list_blocks(document_id)
    markdown = await transcoder.to_markdown(document_id, blocks, base_dir=output_path.parent)
    output_path.write_text(markdown, encoding="utf-8")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Upload local markdown to cloud and diff with original doc.")
    parser.add_argument("--task-id", required=False, help="Sync task id (optional)")
    parser.add_argument("--source-local", required=True, help="Original local markdown path")
    parser.add_argument("--upload-local", required=True, help="Local markdown copy to upload")
    parser.add_argument("--output-dir", required=False, default="data/example/compare", help="Output directory")
    parser.add_argument(
        "--skip-local-check",
        action="store_true",
        help="Skip source/upload local content equality check",
    )
    args = parser.parse_args()

    source_local = Path(args.source_local)
    upload_local = Path(args.upload_local)
    if not source_local.exists():
        raise RuntimeError(f"source local not found: {source_local}")
    if not upload_local.exists():
        raise RuntimeError(f"upload local not found: {upload_local}")

    source_text = source_local.read_text(encoding="utf-8").replace("\r\n", "\n")
    upload_text = upload_local.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not args.skip_local_check and source_text != upload_text:
        raise RuntimeError(
            "source-local 与 upload-local 当前内容不一致，请先复制为相同内容再执行对比。"
        )

    await init_db()
    sync_task_service = SyncTaskService()
    task = None
    if args.task_id:
        task = await sync_task_service.get_task(args.task_id)
    if task is None:
        tasks = await sync_task_service.list_tasks()
        for candidate in tasks:
            if upload_local.as_posix().startswith(candidate.local_path):
                task = candidate
                break
    if task is None:
        raise RuntimeError("未找到对应同步任务，请提供 --task-id")
    task.update_mode = "full"

    link_service = SyncLinkService()
    source_link = await link_service.get_by_local_path(str(source_local))
    if not source_link:
        raise RuntimeError("未找到原始文档映射，请先执行一次下载同步")

    runner = SyncTaskRunner(
        drive_service=DriveService(),
        docx_service=DocxService(),
        transcoder=DocxTranscoder(),
        file_uploader=FileUploader(),
        link_service=link_service,
        import_task_service=ImportTaskService(),
    )

    status = runner.get_status(task.id)
    await runner._upload_markdown(
        task=task,
        status=status,
        path=upload_local,
        docx_service=runner._docx_service,
        file_uploader=runner._file_uploader,
        drive_service=runner._drive_service,
        import_task_service=runner._import_task_service,
    )

    upload_link = await link_service.get_by_local_path(str(upload_local))
    if not upload_link:
        raise RuntimeError("上传完成但未生成映射，无法对比")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    original_path = output_dir / "original.md"
    uploaded_path = output_dir / "uploaded.md"
    diff_path = output_dir / "diff.txt"

    await _download_markdown(runner._docx_service, runner._transcoder, source_link.cloud_token, original_path)
    await _download_markdown(runner._docx_service, runner._transcoder, upload_link.cloud_token, uploaded_path)

    original_text = original_path.read_text(encoding="utf-8").splitlines()
    uploaded_text = uploaded_path.read_text(encoding="utf-8").splitlines()
    diff = difflib.unified_diff(
        original_text,
        uploaded_text,
        fromfile="original",
        tofile="uploaded",
        lineterm="",
    )
    diff_text = "\n".join(diff)
    diff_path.write_text(diff_text, encoding="utf-8")

    print(f"original_doc={source_link.cloud_token}")
    print(f"uploaded_doc={upload_link.cloud_token}")
    print(f"diff_path={diff_path}")
    print("diff_empty" if not diff_text else "diff_nonempty")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
