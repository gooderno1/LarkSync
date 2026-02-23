# LarkSync Feishu Local Cache Skill

把飞书文档“变成本地知识库”的 OpenClaw 集成技能。  
核心目标：让 OpenClaw **优先读本地同步副本**，而不是每次都打飞书 API，从源头降低 token 消耗与限流风险。

## 为什么值得安装
- 省额度：把高频问答读取从飞书 API 转到本地文件系统。
- 更稳：飞书偶发限流/网络波动时，本地副本仍可读。
- 更快：日常检索直接命中本地目录，不必每次远程拉取。
- 可扩展：默认低风险 `download_only`，需要时可升级到双向同步。

## 一句话效果（Before / After）
- Before：问一个文档问题 -> 调一次飞书 API -> 累积额度消耗。
- After：每天低频同步一次 -> 多次问答都走本地读取 -> API 用量大幅下降。

## 适合谁
- 已经在飞书沉淀大量文档、同时用 OpenClaw 做日常知识检索的人。
- 想把飞书纳入 NAS/本地知识管理体系的人。
- 关注“可持续调用成本”的个人或团队。

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

## 30 秒快速上手
```bash
# 1) 环境检查
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py check

# 2) 一键配置每日低频同步（推荐）
python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py bootstrap-daily --local-path "D:\\Knowledge\\FeishuMirror" --cloud-folder-token "<TOKEN>" --sync-mode download_only --download-value 1 --download-unit days --download-time 01:00 --run-now
```

完成后，OpenClaw 可优先读取本地镜像目录，减少飞书 API 请求。

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
