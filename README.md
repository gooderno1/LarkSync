# LarkSync

本地优先的飞书文档同步器：把飞书云文档系统接入你的本地知识库、NAS 与 AI 文档工作流。

## 当前状态
- 当前版本：`v0.5.44`（2026-02-18）
- 核心运行形态：系统托盘常驻 + Web 管理面板
- 开发入口：`npm run dev`
- 稳定版一行发布：`npm run release:publish`

## 为什么做这个项目
1. 作为 NAS 与飞书联合应用的补充，把飞书纳入个人整体工作体系。
2. 让本地文档上传飞书变成自动流程，免去“本地保存后再手动上传一次”。
3. 为 OpenClaw 等 AI 助手的个人文档管理做准备，避免每次读取都直接调用飞书 API（免费次数与效率都受限）。
4. 打通“本地编辑 + 云端协作 + 多设备同步”的完整链路。

## 核心能力
- 双向同步：飞书 Docx <-> 本地 Markdown，支持任务级模式控制。
- 任务级 MD 策略：
  - `enhanced`：云文档 + `_LarkSync_MD_Mirror` 云端镜像（默认）
  - `download_only`：仅下行，不执行本地 MD 上行
  - `doc_only`：仅更新云文档，不保留镜像（有转换损耗风险）
- 同步任务隔离：按 `设备 ID + 飞书 open_id` 双重绑定。
- 任务映射约束：同设备同账号下，本地目录与云端目录强制一对一，禁止父子目录并行任务。
- 删除联动策略（任务级）：`off / safe / strict`，`safe` 含墓碑宽限和本地回收目录 `.larksync_trash/`。
- 转码能力：覆盖标题、列表、代码块、表格、图片、公式、提醒/提及、内嵌 sheet 等常见结构。
- 可靠性：哈希优先变更判定、429 指数退避、SQLite WAL、自愈恢复、同步日志持久化。
- 桌面体验：托盘状态、通知、日志中心、测试任务显隐、主题切换。
- 发布与升级：GitHub Release 构建安装包、客户端稳定版检查与自动下载（sha256 校验）。

## 项目结构
```text
apps/
  backend/   FastAPI + SQLAlchemy + Watchdog
  frontend/  React + Vite + TypeScript
  tray/      pystray 托盘应用
scripts/     打包、发布、文档同步脚本
data/        SQLite 与日志等运行数据
docs/        使用说明、同步逻辑、OAuth 指南
```

## 快速开始

### 1) 安装依赖
```bash
npm install
cd apps/frontend && npm install
cd ../backend && python -m pip install -r requirements.txt
```

### 2) 本地开发测试（默认方式）
```bash
npm run dev
```

会同时启动：
- 托盘进程
- 前端 Vite（`http://localhost:3666`）
- 后端 FastAPI（`http://localhost:8000`）

### 3) 日常运行（无热更新）
```bash
python scripts/build.py
# Windows: 双击 LarkSync.bat / LarkSync.pyw
# macOS: 双击 LarkSync.command
# 通用: python apps/tray/tray_app.py
```

## 测试方式
- 本地联调测试：`npm run dev`
- 用户级体验测试（打包后安装验证）：
```bash
python scripts/build_installer.py
python scripts/build_installer.py --nsis   # Windows 安装包
python scripts/build_installer.py --dmg    # macOS DMG
```
- 后端回归：
```bash
cd apps/backend
python -m pip install -r requirements-dev.txt
python -m pytest
```
- 前端检查：
```bash
cd apps/frontend
npm run build
npx tsc --noEmit
```

## 发布与 GitHub 发布

### 一行发布稳定版（本地）
```bash
npm run release:publish
```

该命令会自动：
1. 计算下一个稳定版本号
2. 更新根/前端/后端版本
3. 更新 `CHANGELOG.md`
4. `git commit` + `git tag`
5. `git push` 与 `git push origin <tag>`

### GitHub 安装包发布
- 已配置工作流：`.github/workflows/release-build.yml`
- 触发条件：推送稳定版 tag（`v*` 且非 `-dev`）
- 产物：Windows `*.exe`、macOS `*.dmg` 自动上传到 Release

## 自动更新机制
- 检查策略：按配置周期检查 + 每次 OAuth 登录成功后额外检查一次。
- 下载策略：命中新稳定版时可自动下载更新包（不自动安装）。
- 校验策略：必须通过 sha256 校验才会保留更新包。
- 说明：若看到 `获取 Release 失败: HTTP 404` 或 “暂无稳定版 Release”，通常是仓库未公开、无 Release 或无稳定版 tag。

## 配置与文档
- 使用文档：`docs/USAGE.md`
- OAuth 指南：`docs/OAUTH_GUIDE.md`
- 同步逻辑：`docs/SYNC_LOGIC.md`
- 飞书开发文档同步：`npm run sync:feishu-docs`

主要环境变量（节选）：
- `LARKSYNC_SYNC_MODE`
- `LARKSYNC_UPLOAD_INTERVAL_VALUE` / `LARKSYNC_UPLOAD_INTERVAL_UNIT`
- `LARKSYNC_DOWNLOAD_INTERVAL_VALUE` / `LARKSYNC_DOWNLOAD_INTERVAL_UNIT`
- `LARKSYNC_AUTO_UPDATE_ENABLED`
- `LARKSYNC_UPDATE_CHECK_INTERVAL_HOURS`
- `LARKSYNC_ALLOW_DEV_TO_STABLE`

## 常见问题
- 托盘不显示：
  - 先退出旧实例，确认 `48901` 未被占用，再重启 `npm run dev`
  - 确认后端依赖已安装（`pystray`、`Pillow`）
- `npm run dev` 启动异常：
  - 项目已内置 `PYTHONPATH` 污染过滤，但建议仍在项目虚拟环境运行
- 打包失败且堆栈含 `numpy/matplotlib`：
  - 先升级到当前版本脚本（已内置跨版本 `site-packages` 过滤）
