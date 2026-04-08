# LarkSync CLI Agent Contract

本文档定义 LarkSync 正式 CLI 在 Agent / Skill 场景下的稳定调用约定，目标是减少“靠 README 猜行为”的隐性耦合。

## 1. 统一输出约定

所有 CLI 命令都返回 JSON：

```json
{
  "ok": true,
  "result": {
    "action": "check"
  }
}
```

失败时返回：

```json
{
  "ok": false,
  "error": "RuntimeError: ..."
}
```

退出码约定：
- `0`：命令执行成功。注意对 `bootstrap-cache` 而言，`needs_oauth` / `needs_drive_permission` 也属于“成功返回了可继续编排的状态”。
- `1`：命令执行失败，例如参数错误、HTTP 调用失败、后端返回不可恢复错误。
- `2`：CLI 参数解析失败。

## 2. 推荐 Agent 工作流

1. 调用 `check` 获取健康状态、授权状态、配置与任务概况。
2. 调用 `bootstrap-cache` 完成首次接入。
3. 若 `bootstrap-cache.phase=needs_oauth`，提示用户完成一次 OAuth，再重试同一命令。
4. 若 `bootstrap-cache.phase=configured`，后续可使用 `task-status`、`task-run`、`logs-sync`、`conflict-list` 做巡检与运维。

推荐原因：
- `bootstrap-cache` 已内置首次接入的关键分支判断；
- Agent 不需要自己拼多次 API，也不需要自己定义“下一步”规则；
- `bootstrap-daily` 继续保留，但更偏底层组合命令，不是首选 Agent 入口。

## 3. 关键命令面

适合 Agent 稳定调用的命令：

| 命令 | 作用 |
| --- | --- |
| `check` | 读取健康、授权、配置、任务概况 |
| `auth-status` | 单独读取授权状态 |
| `workflow-template-list` | 枚举内置标准工作流模板 |
| `workflow-template` | 读取单个工作流模板的结构化定义 |
| `workflow-plan` | 按模板和参数生成可执行命令计划 |
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

## 4. 工作流模板

CLI 提供两条发现型命令：

```bash
python scripts/larksync_cli.py workflow-template-list
python scripts/larksync_cli.py workflow-template --template daily-cache
python scripts/larksync_cli.py workflow-plan --template daily-cache --entrypoint helper --set "local_path=D:\\Knowledge\\FeishuMirror" --set "cloud_folder_token=<TOKEN>"
python scripts/larksync_cli.py workflow-execute --template daily-cache --dry-run --from-step bootstrap --to-step inspect-task --output-json-file data\\workflow.json --set "local_path=D:\\Knowledge\\FeishuMirror" --set "cloud_folder_token=<TOKEN>"
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

执行控制项：
- `--from-step` / `--to-step`：只执行指定区间内的步骤
- `--continue-on-error`：单步失败后继续执行后续步骤，并在结果中汇总错误
- `--output-json-file`：将整份执行结果落盘为 JSON，便于外层 Agent 审计或二次处理
- `--run-id`：显式指定本次执行的稳定 ID
- `--resume-from-file`：从已有 `workflow-execute` 结果文件恢复状态
- `--skip-completed`：恢复执行时跳过结果中已成功的步骤

推荐用法：
1. `workflow-template-list` 发现有哪些标准流程。
2. `workflow-template` 查看模板结构和分支。
3. `workflow-plan` 结合当前参数生成执行计划。
4. `workflow-execute` 在确认计划无误后执行；需要预演时先加 `--dry-run`。
5. 若只想重跑一段链路，配合 `--from-step` / `--to-step`；若需要持久化执行痕迹，配合 `--output-json-file`。
6. 若要从上次执行结果恢复，复用 `--run-id` 并传入 `--resume-from-file`；若不想重复跑已成功步骤，再加 `--skip-completed`。

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
- `completed`：是否完成初始化
- `ready_for_sync`：是否已可进入正常同步
- `summary`：给人类看的简短结论
- `check`：原始巡检结果
- `next_step`：Agent 可直接消费的下一步动作提示

`phase` 枚举：
- `blocked_backend_unreachable`：后端不可达，需先启动 LarkSync
- `needs_oauth`：需要用户先完成 OAuth
- `needs_drive_permission`：授权存在，但 Drive 权限不可用
- `configured`：配置已完成，可继续运行任务或读取本地缓存

`next_step.type` 枚举：
- `start_backend`
- `complete_oauth`
- `grant_drive_permission`
- `use_local_cache`

## 6. 推荐分支处理

当 `phase=needs_oauth`：
- 提示用户完成一次浏览器授权；
- 使用返回中的 `next_step.login_url`；
- 授权完成后重试同一条 `bootstrap-cache` 命令。

当 `phase=needs_drive_permission`：
- 提示检查飞书应用权限和当前账号授权范围；
- 不要继续创建或运行任务。

当 `phase=configured`：
- 如 `run_now=true`，优先读取返回中的 `task_status`；
- 后续巡检优先使用 `task-status`、`logs-sync`、`conflict-list`。

## 7. 兼容说明

- `bootstrap-daily` 仍保留，适合低层组合调用和历史脚本兼容。
- OpenClaw helper 的旧别名 `create-task`、`run-task` 继续可用。
- `larksync_wsl_helper.py` 会自动探测 Windows 侧可达地址，并在必要时补 `--allow-remote-base-url`。
