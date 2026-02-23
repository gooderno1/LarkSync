# LarkSync Feishu Local Cache Skill

用于 OpenClaw 的集成技能：通过 LarkSync 将飞书文档低频同步到本地，后续优先本地读取，降低飞书 API 调用量与 token 消耗。

## 默认推荐模式
- 同步模式：`download_only`
- 下载频率：每日 1 次（可配置时间）
- 读取策略：OpenClaw 优先本地目录检索与引用

## 目录结构
```text
integrations/openclaw/skills/larksync_feishu_local_cache/
  SKILL.md
  README.md
  scripts/
    larksync_skill_helper.py
```

## 依赖前提
1. 本机已安装并运行 LarkSync（后端可访问 `http://localhost:8000`）。
2. 已在 LarkSync 中完成飞书 OAuth 授权。

## 常用命令
```bash
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py check
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py bootstrap-daily --local-path "D:\\Knowledge\\FeishuMirror" --cloud-folder-token "<TOKEN>" --sync-mode download_only --download-value 1 --download-unit days --download-time 01:00 --run-now
```

## 上架 clwuhub（建议先 dry-run）
```bash
cd integrations/openclaw/skills/larksync_feishu_local_cache
clawhub publish --dry-run
clawhub publish
```

> 具体发布流程请结合 OpenClaw 官方文档与 `docs/OPENCLAW_SKILL.md`。
