# LarkSync

<p align="center">
  <img src="assets/branding/LarkSync_Logo_Horizontal_Lockup_FullColor.png" alt="LarkSync Logo" width="520" />
</p>

本地优先的飞书文档同步工具，用于打通飞书云文档与本地文件系统（Markdown/Office）的协作链路。  
当前版本：`v0.5.45`（2026-02-28），核心运行形态为托盘常驻 + Web 管理面板。

## 项目简介
LarkSync 面向“云端协作 + 本地知识管理”并行使用的用户场景。你可以继续在飞书中协作，同时把文档体系稳定地纳入本地目录、NAS 和后续 AI 助手工作流中，避免重复搬运和手工同步。

项目重点不只是“下载备份”，而是双向同步中的一致性与可维护性：任务级策略、设备与账号归属隔离、删除联动策略、更新检查与日志可观测性都已落地。

## 适用场景
1. 作为 NAS 与飞书联合应用的补充，把飞书纳入个人整体工作体系。
2. 本地文档可直接上传飞书，免去手工重复上传。
3. 为 OpenClaw 等 AI 助手做文档管理准备，降低飞书 API 额度与性能压力。
4. 打通本地编辑、云端协作、多设备同步。

## 功能亮点
- 飞书 Docx 与本地 Markdown 双向同步。
- 任务级 MD 模式：`enhanced` / `download_only` / `doc_only`。
- 删除联动策略：`off` / `safe` / `strict`。
- 设备 + 飞书账号双重归属隔离，避免跨设备串任务。
- 自动更新检查与更新包下载（sha256 校验）。
- 日志中心与同步状态面板，便于排查同步异常。
- 内置 OpenClaw Skill 模板：支持“低频同步到本地再本地读取”的降 token 用法。

## 快速开始

### 方式 1：本地开发（推荐）
```bash
npm install
cd apps/frontend && npm install
cd ../backend && python -m pip install -r requirements.txt
cd ../..
npm run dev
```

启动后：
- 前端：`http://localhost:3666`
- 后端：`http://localhost:8000`

### 方式 2：直接下载安装包（面向使用者）
- 打开发布页：<https://github.com/gooderno1/LarkSync/releases>
- Windows 下载 `LarkSync-Setup-*.exe`
- macOS 下载 `LarkSync-*.dmg`

## 文档导航（建议先读）
- 使用文档：[`docs/USAGE.md`](docs/USAGE.md)
- OAuth 配置：[`docs/OAUTH_GUIDE.md`](docs/OAUTH_GUIDE.md)
- 同步逻辑：[`docs/SYNC_LOGIC.md`](docs/SYNC_LOGIC.md)
- OpenClaw Skill：[`docs/OPENCLAW_SKILL.md`](docs/OPENCLAW_SKILL.md)

## OpenClaw 集成
- Skill 目录：`integrations/openclaw/skills/larksync_feishu_local_cache/`
- 设计目标：通过 LarkSync 低频同步飞书文档到本地，让 OpenClaw 优先本地检索，减少飞书 API 调用次数。
- WSL helper 已收敛为“诊断 + 安全转发”，不再自动安装依赖或自动拉起后端，降低 ClawHub 安全扫描误报风险。

## License
本项目采用 **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**。  
完整法律文本见 [`LICENSE`](LICENSE) 或官网：<https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode>
