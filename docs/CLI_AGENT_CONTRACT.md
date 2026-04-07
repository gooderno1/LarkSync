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

## 4. `bootstrap-cache` 契约

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

## 5. 推荐分支处理

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

## 6. 兼容说明

- `bootstrap-daily` 仍保留，适合低层组合调用和历史脚本兼容。
- OpenClaw helper 的旧别名 `create-task`、`run-task` 继续可用。
- `larksync_wsl_helper.py` 会自动探测 Windows 侧可达地址，并在必要时补 `--allow-remote-base-url`。
