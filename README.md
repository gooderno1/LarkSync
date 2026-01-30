# LarkSync

运行在本地的“双向同步助手”，通过智能转码引擎连接飞书云端（Docx）与本地文件系统（Markdown/Office）。实现“本地编辑，云端协作”的无缝工作流，打通个人数据孤岛与企业知识库。

## 功能概览
- 全栈脚手架已搭建：FastAPI 后端 + Vite React TypeScript 前端
- 统一开发入口：根目录 `npm run dev` 并行启动前后端
- 预留同步核心模块与数据层目录结构（core / services / db）
- 配置中心：支持 `data/config.json` 与环境变量覆盖（含 `sync_mode`）
- SQLite 同步状态模型：`SyncMapping`
- 发布脚本：`scripts/release.py` 自动更新版本、CHANGELOG 并提交推送
- OAuth 登录：后端提供 `/auth/login`、`/auth/callback`、`/auth/status`、`/auth/logout`
- 云端目录树：后端提供 `/drive/tree`，前端可展示云空间层级
- Docx 转 Markdown：支持标题/加粗/列表/引用/代码块/待办/表格/图片块解析与图片落盘
- 本地写入器：写入文件后强制同步云端 mtime
- 非文档下载：提供 Drive 文件下载器，直接写入本地目录
- 本地监听：Watchdog 防抖监听 + WebSocket 实时事件推送
- Markdown 转 Docx：调用 Docx Block 接口执行全量覆盖（含 429 指数退避重试）
- Markdown 上行局部更新：基于 block 差异仅更新变更段落（支持 fallback 全量覆盖）
- 同步任务支持更新模式：自动/局部/全量
- Markdown 图片上传：本地图片自动上传为 Docx 图片块并插入文档
- 通用文件上传：支持 upload_all / 分片上传，并在本地状态库记录 file_hash 与云端 token
- 冲突中心：持久化冲突记录与前端对比视图，支持“使用本地/云端”决策
- 同步任务配置向导：支持云端目录选择器、本地文件夹选择器与任务状态
- 下载型同步任务：支持立即同步、状态展示与删除
- 双向/上传任务：本地变更上传（已映射 Docx 全量覆盖，普通文件新增上传）
- 手动上传 Markdown：用于快速验证 Docx 全量覆盖与图片上传链路
- 文档链接本地化：云端链接自动改写为本地相对路径，附件落盘至 attachments
- 日志系统：后端运行日志写入 `data/logs/larksync.log`

## 本地开发
### 使用教程
- 完整使用步骤见 `docs/USAGE.md`，后续功能变更会同步更新。
### OAuth 配置
- 支持在网页中通过“OAuth 配置向导”填写并保存应用参数，详细步骤见 `docs/OAUTH_GUIDE.md`。
### 依赖安装
- 根目录：`npm install`（用于并行启动前后端）
- 前端：`cd apps/frontend` 后执行 `npm install`
- 后端：`cd apps/backend` 后执行 `python -m pip install -r requirements.txt`
  - 开发依赖：`python -m pip install -r requirements-dev.txt`

### 启动
- 统一入口：根目录执行 `npm run dev`
- 分别启动：
  - 后端：`cd apps/backend` 后执行 `uvicorn src.main:app --reload --port 8000`
  - 前端：`cd apps/frontend` 后执行 `npm run dev`

### 配置
- 默认读取 `data/config.json`，可通过环境变量覆盖：
  - `LARKSYNC_SYNC_MODE`：`bidirectional` / `download_only` / `upload_only`
  - `LARKSYNC_DATABASE_URL` 或 `LARKSYNC_DB_PATH`
  - `LARKSYNC_AUTH_AUTHORIZE_URL` / `LARKSYNC_AUTH_TOKEN_URL`
  - `LARKSYNC_AUTH_CLIENT_ID` / `LARKSYNC_AUTH_CLIENT_SECRET`
  - `LARKSYNC_AUTH_REDIRECT_URI`
  - `LARKSYNC_AUTH_SCOPES`（逗号分隔）
  - `LARKSYNC_TOKEN_STORE`（`keyring` / `memory`）

## 生产部署（Docker）
- 构建与启动：
  - `docker-compose build`
  - `docker-compose up -d`
- 访问地址：`http://localhost:8080`
- 说明：生产环境通过 Nginx 反向代理 `/api/*` 到后端，前端已在生产模式下自动加 `/api` 前缀。
