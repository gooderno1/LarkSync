# OpenClaw Skill 使用与上架指南

本文档说明如何基于 LarkSync 使用 OpenClaw Skill，目标是让飞书文档先低频同步到本地，再由 OpenClaw 优先本地读取，减少飞书 API 调用与 token 消耗。

## 为什么这个 Skill 有吸引力
- 对用户：同样的问题不必反复消耗飞书 API，文档问答成本更可控。
- 对 Agent：读取路径更稳定，避免把每次检索都绑定到远程 API 可用性。
- 对团队：可以把“飞书协作 + 本地知识库 + AI 检索”组合成长期可持续方案。

一句话：把“每次读取都打云 API”变成“每天低频同步一次，本地高频复用”。  

## 1. Skill 位置

```text
integrations/openclaw/skills/larksync_feishu_local_cache/
```

关键文件：
- `SKILL.md`：Skill 定义（OpenClaw 识别入口）
- `scripts/larksync_skill_helper.py`：自动化辅助脚本

## 2. 推荐默认策略（降本优先）
- 同步模式：`download_only`
- 下载频率：每天一次（可改时间）
- 读取方式：OpenClaw 优先读本地同步目录

这样可以把“高频问答读取”从飞书 API 迁移到本地文件系统，显著降低 API 请求量。

## 3. 本地执行流程

### 3.1 检查环境
```bash
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py check
```

### 3.2 一键配置低频同步并建任务
```bash
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py bootstrap-daily \
  --local-path "D:\\Knowledge\\FeishuMirror" \
  --cloud-folder-token "<你的飞书文件夹 token>" \
  --sync-mode download_only \
  --download-value 1 \
  --download-unit days \
  --download-time 01:00 \
  --run-now
```

### 3.3 进阶：双向同步（谨慎）
```bash
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py create-task \
  --name "OpenClaw 双向任务" \
  --local-path "D:\\Knowledge\\FeishuBiSync" \
  --cloud-folder-token "<token>" \
  --sync-mode bidirectional
```

## 4. 上架 ClawHub

> 建议先登录，再做 dry-run，最后正式发布。

```bash
cd integrations/openclaw/skills/larksync_feishu_local_cache
clawhub login
clawhub sync --root . --dry-run
clawhub publish . --slug larksync-feishu-local-cache --name "LarkSync Feishu Local Cache" --version 0.1.0 --changelog "首次发布：飞书低频同步到本地缓存"
```

若发布失败，请先检查：
1. `SKILL.md` frontmatter 是否完整（`name`、`description`、`metadata`）。
2. 目录内引用脚本路径是否有效。
3. OpenClaw CLI 是否已登录并具备发布权限。

## 5. 常见排查
- `check` 显示后端不可达：先启动 LarkSync（`npm run dev` 或托盘版）。
- `auth.connected=false`：先在 LarkSync 完成飞书授权。
- 创建任务 409：说明路径映射冲突或已有任务，脚本会尝试复用已有任务。

## 6. 相关参考
- OpenClaw Skills 文档：<https://openclaw.ai/docs/skills>
- OpenClaw Hub 发布文档：<https://openclaw.ai/docs/getting-started/publish-skill>
