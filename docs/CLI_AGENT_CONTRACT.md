# LarkSync CLI Agent Contract

本文档定义 LarkSync 正式 CLI 在 Agent / Skill 场景下的稳定调用约定，目标是减少“靠 README 猜行为”的隐性耦合。

v1.0.0 起，完整的任务 JSON、授权和维护命令见 [技能命令参考](../integrations/skills/larksync/references/commands.md)，客户端安装见 [AI 使用指南](AI_GUIDE.md)。`capabilities` 离线发现能力，`schema` 查询当前运行后端的 OpenAPI。

## 1. 统一输出约定

除 `--help` 外，CLI 返回 UTF-8 JSON；全局 `--account-id` / `--base-url` 放在子命令之前：

```json
{
  "ok": true,
  "account_id": "selected-account-id",
  "result": {
    "action": "check"
  }
}
```

失败时返回：

```json
{
  "ok": false,
  "error": "CliError: ...",
  "error_code": "ACCOUNT_REQUIRED",
  "next_step": "运行 account-list 后指定 --account-id。",
  "details": null
}
```

退出码约定：
- `0`：命令执行成功。注意对 `bootstrap-cache` 而言，`needs_oauth` / `needs_drive_permission` 也属于“成功返回了可继续编排的状态”。
- `1`：API、环境或账号选择失败。
- `2`：CLI 参数解析或 JSON 字段校验失败。

`ok` 不代表同步完成；只有 `sync_complete: true` 才表示本次同步成功结束。`task-wait` 超时返回 `timed_out: true`，不取消任务。`auth-status` / `check` 只检查本地凭据，`auth-verify` 才实际检查云目录读取；它也不代表写权限已验证。

## 2. 推荐 Agent 工作流

1. `capabilities` → `account-list`，确定账号；多账号时必须传 `--account-id`。
2. 无账号时用 `app-list`、`auth-start`、`auth-poll` 完成应用注册和 Device Flow 授权，用户自行扫码。
3. `auth-verify` → `drive-list`，验证读取权限并分页确认云文件夹。
4. `task-plan --spec-file task.json`，默认仅下载、删除关闭，不调用网络或写文件。
5. 根据用户授权执行 `task-create --spec-file task.json`；启用任务可能立即运行。
6. `task-wait` 确认结果；日常使用 `task-get/update/pause/resume/diagnostics/entries/delete`。

旧 `bootstrap-*` / `workflow-*` 保留兼容，下面第 4—7 节记录旧编排方式。bootstrap 会修改全局频率，影响全部任务，只有用户明确需要该全局配置时才使用。新任务首选上面的流程。

## 3. 关键命令面

适合 Agent 稳定调用的命令：

| 命令 | 作用 |
| --- | --- |
| `capabilities` / `schema` | 离线能力发现 / 运行服务的模型契约 |
| `account-list` / `app-list` | 账号与应用发现，不返回密钥 |
| `auth-start/poll/cancel/reauthorize` | 扫码会话生命周期 |
| `auth-verify` / `drive-list` | 验证 Drive 读取、分页目录发现 |
| `task-plan` / `task-create` / `task-update` | JSON 配置、无写入预览、创建修改 |
| `task-get/pause/resume/delete` | 日常维护 |
| `task-wait` / `task-run --wait` | 有限等待，不混淆提交和完成 |
| `task-diagnostics` / `task-entries` | 运行诊断与本地目录分页浏览 |
| `check` | 读取健康、授权、配置、任务概况 |
| `auth-status` | 单独读取授权状态 |
| `workflow-template-list` | 枚举内置标准工作流模板 |
| `workflow-template` | 读取单个工作流模板的结构化定义 |
| `workflow-plan` | 按模板和参数生成可执行命令计划 |
| `workflow-run-list` | 列出已归档的工作流执行记录 |
| `workflow-run-show` | 读取单个工作流执行记录 |
| `workflow-run-prune` | 清理旧的工作流执行记录 |
| `workflow-execute` | 按模板与参数顺序执行工作流 |
| `bootstrap-cache` | 首次缓存初始化的高层命令 |
| `task-list` | 列出现有同步任务 |
| `task-status` | 读取单个任务运行状态 |
| `task-run` | 立即触发一次任务 |
| `logs-sync` | 查询同步日志 |
| `conflict-list` | 查询冲突列表 |
| `update-status` | 查询自动更新状态 |

正式入口：

```bash
python scripts/larksync_cli.py <command> [options]
```

OpenClaw 兼容入口：

```bash
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py <command> [options]
```

WSL 场景推荐入口：

```bash
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py <command> [options]
```

## 4. 旧工作流模板（兼容）

CLI 提供两条发现型命令：

```bash
python scripts/larksync_cli.py workflow-template-list
python scripts/larksync_cli.py workflow-template --template daily-cache
python scripts/larksync_cli.py workflow-plan --template daily-cache --entrypoint helper --set "local_path=D:\\Knowledge\\FeishuMirror" --set "cloud_folder_token=<TOKEN>"
python scripts/larksync_cli.py workflow-execute --template daily-cache --dry-run --from-step bootstrap --to-step inspect-task --output-json-file data\\workflow.json --set "local_path=D:\\Knowledge\\FeishuMirror" --set "cloud_folder_token=<TOKEN>"
python scripts/larksync_cli.py workflow-run-list --limit 10
```

当前内置模板：
- `daily-cache`：首次接入或新增目录缓存初始化
- `refresh-cache`：对已有任务执行一次手动刷新并回读状态/日志
- `conflict-audit`：查询冲突并指导人工决策

模板返回内容包含：
- `entrypoints`：CLI / helper / WSL helper 的推荐入口
- `inputs`：工作流输入参数
- `steps`：标准步骤与推荐命令
- `branching`：推荐分支处理

`workflow-plan` 在 `workflow-template` 基础上进一步输出：
- `values`：已灌入的模板参数
- `missing_inputs`：仍缺失的外部输入
- `plan.steps[*].argv`：结构化参数数组
- `plan.steps[*].command_line`：可直接复制执行的命令行
- `plan.steps[*].dynamic_inputs`：依赖上一步运行结果的参数

`workflow-execute` 在 `workflow-plan` 基础上进一步提供：
- `execution_log`：实际执行的步骤与运行时参数
- `results`：各步骤原始返回值，后续步骤可从中提取动态输入
- `dry_run=true`：只返回计划，不触发真实执行
- `completed` / `executed_steps`：实际执行结果摘要
- `failed_steps` / `errors`：失败步骤汇总
- `run_id` / `run_file`：本次执行的稳定 ID 与标准归档文件路径（自动写入 `data/workflows/<run_id>.json`）

执行控制项：
- `--from-step` / `--to-step`：只执行指定区间内的步骤
- `--continue-on-error`：单步失败后继续执行后续步骤，并在结果中汇总错误
- `--output-json-file`：将整份执行结果落盘为 JSON，便于外层 Agent 审计或二次处理
- `--run-id`：显式指定本次执行的稳定 ID
- `--resume-from-file`：从已有 `workflow-execute` 结果文件恢复状态；未传时会尝试从 `data/workflows/<run_id>.json` 自动恢复
- `--skip-completed`：恢复执行时跳过结果中已成功的步骤

运行记录命令：
- `workflow-run-list --limit N`：按最近保存时间倒序列出执行记录
- `workflow-run-show --run-id <id>`：读取指定 run 的完整 JSON
- `workflow-run-prune --keep N`：仅保留最近 N 条标准运行记录

推荐用法：
1. `workflow-template-list` 发现有哪些标准流程。
2. `workflow-template` 查看模板结构和分支。
3. `workflow-plan` 结合当前参数生成执行计划。
4. `workflow-execute` 在确认计划无误后执行；需要预演时先加 `--dry-run`。
5. `workflow-execute` 每次真实执行都会自动归档到 `data/workflows/<run_id>.json`；若需要额外产出到别处，再补 `--output-json-file`。
6. 若只想重跑一段链路，配合 `--from-step` / `--to-step`。
7. 若要从上次执行结果恢复，复用 `--run-id`；默认读取用户数据目录 `LarkSync/cli/workflows/<run_id>.json`，可用 `LARKSYNC_CLI_DATA_DIR` 覆盖。旧仓库 `data/workflows` 记录需显式 `--resume-from-file` 导入；不想重复已成功步骤时加 `--skip-completed`。
8. 若要让外层 Agent 查询历史执行，使用 `workflow-run-list` / `workflow-run-show`；若要定期清理历史，使用 `workflow-run-prune`。

## 5. `bootstrap-cache` 契约

命令示例：

```bash
python scripts/larksync_cli.py bootstrap-cache \
  --local-path "D:\\Knowledge\\FeishuMirror" \
  --cloud-folder-token "<TOKEN>" \
  --sync-mode download_only \
  --download-value 1 \
  --download-unit days \
  --download-time 01:00 \
  --run-now
```

输入语义：
- `--local-path`：本地缓存目录
- `--cloud-folder-token`：飞书云目录 token
- `--sync-mode`：默认推荐 `download_only`
- `--download-*`：下载频率配置
- `--run-now`：完成配置后立即执行一次任务，建立本地缓存基线

稳定返回字段：
- `action`：固定为 `bootstrap-cache`
- `phase`：当前阶段
- `completed` / `configuration_complete`：是否完成配置，不代表文件已同步
- `sync_complete`：bootstrap 固定为 false，另用 task-wait 确认同步结果
- `ready_for_sync`：是否已可进入正常同步
- `summary`：给人类看的简短结论
- `check`：原始巡检结果
- `next_step`：Agent 可直接消费的下一步动作提示

`phase` 枚举：
- `blocked_backend_unreachable`：后端不可达，需先启动 LarkSync
- `needs_oauth`：需要用户先完成 OAuth
- `needs_drive_permission`：授权存在，但 Drive / Docx 必要权限不可用
- `configured`：配置已完成，仍需等待同步成功后读取缓存

`next_step.type` 枚举：
- `start_backend`
- `complete_oauth`
- `grant_drive_permission`
- `wait_for_sync`

## 6. 推荐分支处理

当 `phase=needs_oauth`：
- 提示用户完成 Device Flow 扫码；
- 使用 `next_step.commands`，或通过 `next_step.login_url` 打开应用连接页；不再跳转旧 `/auth/login`；
- 授权完成后重试同一条 `bootstrap-cache` 命令。

当 `phase=needs_drive_permission`：
- 提示检查飞书应用权限和当前账号授权范围，重点确认 `drive:drive`、`docx:document`、`docx:document.block:convert`；
- 不要继续创建或运行任务。

当 `phase=configured`：
- 如 `run_now=true`，优先读取返回中的 `task_status`；
- 后续巡检优先使用 `task-status`、`logs-sync`、`conflict-list`。

## 7. 兼容说明

- `bootstrap-daily` 仍保留，适合低层组合调用和历史脚本兼容。
- OpenClaw helper 的旧别名 `create-task`、`run-task` 在源码仓库内继续可用；独立安装应改用自包含的 `integrations/skills/larksync`。
- `larksync_wsl_helper.py` 会自动探测 Windows 侧可达地址，并在必要时补 `--allow-remote-base-url`。
