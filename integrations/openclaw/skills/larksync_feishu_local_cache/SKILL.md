---
name: larksync-feishu-local-cache
description: 通过 LarkSync 将飞书文档低频同步到本地目录，优先本地读取，降低飞书 API 调用与 token 消耗。
homepage: https://github.com/gooderno1/LarkSync
metadata:
  category: integrations
  tags:
    - openclaw
    - feishu
    - larksync
    - sync
    - local-cache
  license: CC-BY-NC-SA-4.0
---

# LarkSync Feishu Local Cache Skill

## 适用目标
- 目标：减少 OpenClaw 直接调用飞书 API 的频率，优先读取本地 Markdown/附件。
- 默认策略：`download_only` + 每日低频同步（可自定义时间与周期）。
- 进阶策略：支持 `bidirectional`（双向）和 `upload_only`，但仅在用户明确要求时启用。

## 触发意图（示例）
- “把飞书生产测试文件夹每天 01:00 同步到本地，给我配置好。”
- “先检查 LarkSync 当前授权和同步任务状态。”
- “我想把这个目录切成双向同步，先评估风险再改。”

## 默认执行流程
1. 检查本地 LarkSync 服务与授权状态。
2. 配置低频下载策略（默认每天一次）。
3. 创建同步任务（默认 `download_only`）。
4. 按需触发一次立即同步，建立本地缓存基线。
5. 后续回答用户文档问题时，优先读取本地同步目录。

## 命令入口
使用以下脚本作为统一入口（返回 JSON，便于自动化编排）：

```bash
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py check
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py configure-download --download-value 1 --download-unit days --download-time 01:00
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py create-task --name "OpenClaw 每日同步" --local-path "D:\\Knowledge\\FeishuMirror" --cloud-folder-token "<TOKEN>" --sync-mode download_only
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py run-task --task-id "<TASK_ID>"
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py bootstrap-daily --local-path "D:\\Knowledge\\FeishuMirror" --cloud-folder-token "<TOKEN>" --sync-mode download_only --download-value 1 --download-unit days --download-time 01:00 --run-now
```

## 约束与安全边界
- 未通过 `check` 之前，不执行任务创建或策略变更。
- 未经用户明确同意，不把 `download_only` 自动切到 `bidirectional`。
- 若用户要开启双向，必须先告知风险：
  - 本地误改可能上云；
  - 首次建任务可能触发下行/上行扫描；
  - 建议先在测试目录验证。

## 失败处理
- 若接口返回 401/403：提示重新授权飞书并检查“用户身份权限”。
- 若创建任务冲突（409）：自动复用同路径+同云目录的现有任务并回显任务 ID。
- 若后端不可达：提示先启动 `npm run dev` 或 LarkSync 托盘程序。

## 输出规范
- 对用户：简明中文结论 + 下一步操作。
- 对系统：保留 helper 脚本 JSON 原始输出，便于追踪与审计。
