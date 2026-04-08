from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.larksync_cli import (  # noqa: E402
    ApiResult,
    do_build_workflow_plan,
    do_get_workflow_template,
    do_list_workflow_templates,
    do_bootstrap_cache,
    build_download_config_payload,
    build_task_payload,
    do_auth_status,
    do_bootstrap_daily,
    do_check,
    do_configure_download,
    do_create_task,
    do_delete_task,
    do_get_config,
    do_get_drive_tree,
    do_get_task_status,
    do_list_conflicts,
    do_list_task_status,
    do_list_tasks,
    do_read_file_logs,
    do_read_sync_logs,
    do_reset_task_links,
    do_resolve_conflict,
    do_run_task,
    do_set_config,
    do_update_check,
    do_update_download,
    do_update_install,
    do_update_status,
    do_update_task,
    infer_md_sync_mode,
    main as _cli_main,
    validate_base_url,
    _request_json,
    _validate_hhmm,
)

_COMMAND_ALIASES = {
    "create-task": "task-create",
    "run-task": "task-run",
}

__all__ = [
    "ApiResult",
    "_request_json",
    "_validate_hhmm",
    "build_download_config_payload",
    "build_task_payload",
    "do_auth_status",
    "do_build_workflow_plan",
    "do_get_workflow_template",
    "do_list_workflow_templates",
    "do_bootstrap_cache",
    "do_bootstrap_daily",
    "do_check",
    "do_configure_download",
    "do_create_task",
    "do_delete_task",
    "do_get_config",
    "do_get_drive_tree",
    "do_get_task_status",
    "do_list_conflicts",
    "do_list_task_status",
    "do_list_tasks",
    "do_read_file_logs",
    "do_read_sync_logs",
    "do_reset_task_links",
    "do_resolve_conflict",
    "do_run_task",
    "do_set_config",
    "do_update_check",
    "do_update_download",
    "do_update_install",
    "do_update_status",
    "do_update_task",
    "infer_md_sync_mode",
    "main",
    "validate_base_url",
]


def _normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return []
    normalized = list(argv)
    for index, value in enumerate(normalized):
        if value in _COMMAND_ALIASES:
            normalized[index] = _COMMAND_ALIASES[value]
            break
    return normalized


def main(argv: list[str] | None = None) -> int:
    return _cli_main(_normalize_argv(list(argv if argv is not None else sys.argv[1:])))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
