# OpenClaw / AI Agent 本地飞书缓存教程

更新时间：2026-05-28

本文面向希望让 OpenClaw 或其他 AI Agent 读取飞书文档的用户。推荐模式是：LarkSync 低频把飞书文档同步到本地，Agent 高频读取本地目录。

## 1. 适用场景

适合：

- 团队知识库主要在飞书，Agent 需要反复查询。
- 希望减少飞书 API 调用次数和限流风险。
- 希望把飞书文档纳入本地检索、RAG、脚本处理或 NAS 备份。
- OpenClaw 运行在 WSL，但 LarkSync 运行在 Windows 托盘。

不适合：

- 需要秒级实时读取飞书最新编辑内容。
- 希望 Agent 直接修改飞书文档。
- 尚未完成飞书 OAuth 配置。

## 2. 推荐架构

```text
飞书云文档
  ↓ 低频同步（download_only）
LarkSync 本地同步目录
  ↓ 本地读取
OpenClaw / AI Agent / 本地检索脚本
```

这个架构把高频读取从远程 API 转移到本地文件系统，稳定性和成本都更可控。

## 3. 准备工作

1. 安装并启动 LarkSync。
2. 按 [OAuth 配置指南](OAUTH_GUIDE.md) 完成飞书授权。
3. 创建一个本地目录，例如 `D:\Knowledge\FeishuMirror`。
4. 准备一个飞书文件夹 token。
5. 首次建议先同步一个测试文件夹。

## 4. 用 GUI 创建缓存任务

1. 打开 LarkSync 管理面板。
2. 进入“同步任务”。
3. 新建任务。
4. 本地目录选择 `D:\Knowledge\FeishuMirror`。
5. 云端目录选择目标飞书文件夹。
6. 同步模式选择 `download_only`。
7. 下载频率建议设为每天一次，例如 `01:00`。
8. 保存后点击“立即同步”。

同步完成后，OpenClaw 或其他 Agent 直接读取这个本地目录。

## 5. 用 CLI 初始化缓存任务

在仓库目录或安装包可访问的命令环境中执行：

```bash
python scripts/larksync_cli.py bootstrap-cache \
  --local-path "D:\Knowledge\FeishuMirror" \
  --cloud-folder-token "<你的飞书文件夹 token>" \
  --sync-mode download_only \
  --download-value 1 \
  --download-unit days \
  --download-time 01:00 \
  --run-now
```

如果你想先查看可执行计划：

```bash
python scripts/larksync_cli.py workflow-template --template daily-cache
python scripts/larksync_cli.py workflow-plan \
  --template daily-cache \
  --entrypoint helper \
  --set "local_path=D:\Knowledge\FeishuMirror" \
  --set "cloud_folder_token=<你的飞书文件夹 token>"
```

## 6. WSL 场景

如果 OpenClaw 在 WSL，LarkSync 在 Windows：

```bash
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py diagnose
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py bootstrap-cache \
  --local-path "/mnt/d/Knowledge/FeishuMirror" \
  --cloud-folder-token "<你的飞书文件夹 token>" \
  --sync-mode download_only \
  --download-value 1 \
  --download-unit days \
  --download-time 01:00 \
  --run-now
```

如果诊断显示 Windows 侧不可达：

- 确认 LarkSync 托盘程序已启动。
- 确认后端监听 `18765` 端口。
- 如手动设置过 `LARKSYNC_BACKEND_BIND_HOST=127.0.0.1`，请改为 `0.0.0.0` 或移除后重启。

## 7. Agent 提示词建议

可以在 Agent 系统提示词或项目说明中加入：

```text
优先读取本地 LarkSync 缓存目录 D:\Knowledge\FeishuMirror。
该目录由 LarkSync 每天从飞书同步一次，作为飞书文档的本地只读缓存。
不要直接调用飞书 API，除非用户明确要求读取实时云端内容。
```

WSL 中可写成：

```text
优先读取 /mnt/d/Knowledge/FeishuMirror。
该目录由 Windows 侧 LarkSync 从飞书同步，作为本地只读缓存。
```

## 8. 运行维护

- 默认推荐每天同步一次。
- 重要知识库可在每天工作前手动点击“立即同步”。
- 定期查看日志中心，确认最近一次同步成功。
- 如果文档数量很大，首次同步后再交给 Agent 高频读取。

## 9. 常见问题

### Agent 读不到最新飞书修改怎么办

先在 LarkSync 中手动执行一次同步。LarkSync 追求最终一致性，不是秒级实时同步。

### 是否应该让 Agent 写回飞书

不建议第一阶段这么做。Agent 场景推荐 `download_only`，把飞书文档作为本地只读缓存。

### 同步目录可以放进 Git 吗

可以，但需要谨慎。飞书同步目录可能包含团队文档、图片和附件，不建议直接提交到公开仓库。

### 如何反馈 OpenClaw 问题

请参考 [反馈与排障指南](FEEDBACK.md)，并额外提供：

- OpenClaw 运行环境：Windows / WSL / macOS。
- LarkSync 后端地址。
- `diagnose` 输出。
- 使用的本地缓存目录。
