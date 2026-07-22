# LarkSync 真实数据安全测试指南

本文适用于在电脑上仍安装并使用正式版 LarkSync 时验证 v0.8。默认原则是：正式版优先、测试数据隔离、云端写入默认拒绝、Token 不复制。

## 运行配置档

| Profile | 正式版可否继续运行 | 飞书访问 | 云端写入 | Token Store |
| --- | --- | --- | --- | --- |
| `synthetic_test` | 可以 | 禁止 | 禁止 | 独立文件 |
| `snapshot_test` | 可以 | 禁止 | 禁止，本地 API 也只读 | 独立文件 |
| `live_readonly` | 必须完整退出 | 允许语义只读请求 | HTTP 边界拒绝 | 系统 keyring |
| `live_bidirectional` | 必须完整退出，除非使用独立授权 | 允许 | 仅 allowlist 根目录 | 系统 keyring |

非生产 Profile 必须显式使用独立后端端口、Vite 端口、实例锁和数据目录。共享 keyring 的 Profile 在检测到正式版 18765 或升级过渡期的旧版 8000 仍运行时会拒绝启动。

## Level 0：合成数据

正式版可以继续运行。执行：

```powershell
npm run dev:test
```

该入口默认使用：

- 后端首选端口 `18000`。
- Vite 端口 `13666`。
- 实例锁 `48911`。
- 数据目录 `data/dev-test`。
- `synthetic_test` Profile。
- 独立文件 Token Store；FeishuClient 禁止访问云端。

若 18000 上已有实例，但数据目录或 Profile 不匹配，启动脚本会选择下一个空闲端口，不会复用未知后端。

## Level 1：脱敏正式数据快照

正式版可以继续运行。必须先通过正式版自身状态或维护信息确认实际数据库路径；不要根据仓库 `data/`、`%APPDATA%` 或进程目录猜测。

导出使用 SQLite online backup，不复制正在写入的 `db/wal/shm`：

```powershell
python scripts/export_test_snapshot.py `
  --source-db "<已确认的正式数据库绝对路径>" `
  --output "data/test-runs/<run-id>/snapshot"

python scripts/validate_test_profile.py `
  --profile snapshot_test `
  --data-dir "data/test-runs/<run-id>/snapshot"
```

启动快照实例前设置独立环境：

```powershell
$env:LARKSYNC_RUNTIME_PROFILE = "snapshot_test"
$env:LARKSYNC_BACKEND_PORT = "18100"
$env:LARKSYNC_VITE_DEV_PORT = "13766"
$env:LARKSYNC_LOCK_PORT = "49011"
$env:LARKSYNC_DATA_DIR = "<snapshot 目录绝对路径>"
$env:LARKSYNC_DB_PATH = "<snapshot 目录绝对路径>\larksync.db"
$env:LARKSYNC_TOKEN_STORE = "file"
$env:LARKSYNC_TOKEN_FILE = "<snapshot 目录绝对路径>\token_store.json"
npm run dev
```

快照导出会执行以下不可逆脱敏，但只修改快照副本：

- 停用全部任务。
- 把遗留 `running` 改为 `cancelled`。
- 将本地路径重映射到快照 `workspace/`。
- 稳定伪名化云端 Token。
- 删除 owner open_id 和冲突正文预览。
- 不导出 keyring Token、App Secret、更新包或正式日志。

查询性能基准：

```powershell
python scripts/benchmark_snapshot.py `
  --database "<snapshot 目录绝对路径>\larksync.db" `
  --iterations 20 `
  --max-p95-ms 250 `
  --max-peak-memory-mb 256
```

## Level 2：真实云端只读

此阶段不能与使用同一 keyring 的正式版并行。开始前必须：

1. 记录正式版版本、任务数、运行数和冲突数。
2. 等待所有正式任务结束。
3. 从托盘完整退出正式版。
4. 确认 `LarkSync.exe` 已退出且 18765、8000 端口均关闭。
5. 使用 SQLite online backup 备份已确认的正式数据库；禁止导出 keyring Token。

测试环境必须设置 `live_readonly`、独立端口/锁/数据目录、`download_only`、`delete_policy=off` 和新本地空目录。建议同时设置：

```powershell
$env:LARKSYNC_CLOUD_AUDIT_LOG = "<测试目录>\cloud-request-audit.jsonl"
```

只读边界允许 GET、HEAD、OPTIONS，以及元数据批查、Docx block convert、导出任务三类语义只读 POST。创建目录、上传、导入、修改块和删除等请求会在取得 Token 和发送 HTTP 前被拒绝。

测试结束后检查审计中没有云端写请求，再停止测试实例、清理测试环境变量、启动正式版，并复核授权、任务数和冲突数。

## Level 3：专用目录双向测试

只有用户明确确认专用飞书测试根目录 Token 后才可执行：

```powershell
$env:LARKSYNC_RUNTIME_PROFILE = "live_bidirectional"
$env:LARKSYNC_ALLOWED_CLOUD_ROOTS = "<专用测试根目录 Token>"
```

任务自身的 `cloud_folder_token` 必须与 allowlist 根 Token 一致。每个写请求还必须处在当前任务根作用域内；仅设置环境变量而未使用该任务执行，仍会被 FeishuClient 拒绝。

禁止把正式业务目录、正式本地同步目录或从日志中猜测出的 Token 放入 allowlist。

## 结果判定

真实数据测试只有同时满足以下条件才可通过：

- 测试实例未访问正式端口和正式本地目录。
- 快照模式没有任何飞书请求。
- 真实只读审计没有云端写请求。
- 专用双向测试根目录之外的写请求为 0。
- 正式版恢复后授权、任务数、冲突数和关键文件清单与测试前一致。
