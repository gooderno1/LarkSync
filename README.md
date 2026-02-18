# LarkSync

<p align="center">
  <img src="assets/branding/LarkSync_Logo_Horizontal_Lockup_FullColor.png" alt="LarkSync Logo" width="520" />
</p>

本地优先的飞书文档同步工具，把飞书云文档接入你的 NAS、本地知识库与 AI 文档工作流。  
当前版本：`v0.5.44`（2026-02-18）

## 项目价值
1. 作为 NAS 与飞书联合应用的补充，把飞书纳入个人整体工作体系。
2. 本地文档可直接上传飞书，免去手工重复上传。
3. 为 OpenClaw 等 AI 助手做文档管理准备，降低飞书 API 额度与性能压力。
4. 打通本地编辑、云端协作、多设备同步。

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

## 主要功能
- 飞书 Docx 与本地 Markdown 双向同步
- 任务级 MD 模式（`enhanced` / `download_only` / `doc_only`）
- 删除联动策略（`off` / `safe` / `strict`）
- 设备 + 飞书账号双重归属隔离
- 自动更新检查与更新包下载（sha256 校验）

## 文档导航
- 使用文档：[`docs/USAGE.md`](docs/USAGE.md)
- OAuth 配置：[`docs/OAUTH_GUIDE.md`](docs/OAUTH_GUIDE.md)
- 同步逻辑：[`docs/SYNC_LOGIC.md`](docs/SYNC_LOGIC.md)

## 常见问题
- 托盘不显示：先退出旧实例并确认端口 `48901` 未占用，再重启 `npm run dev`。
- 更新检查提示 `HTTP 404`：通常是仓库无公开 Release 或无稳定版 tag。
