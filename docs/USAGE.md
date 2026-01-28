# LarkSync 使用教程（持续更新）

本文档用于记录当前版本的使用与测试流程，会随项目迭代同步维护。

## 1. 环境准备
- Node.js 18+（用于前端与根目录脚本）
- Python 3.10+（后端 FastAPI）

## 2. 依赖安装
- 根目录：`npm install`
- 前端：`cd apps/frontend` 后执行 `npm install`
- 后端：`cd apps/backend` 后执行 `python -m pip install -r requirements.txt`
  - 开发依赖：`python -m pip install -r requirements-dev.txt`

## 3. 配置飞书 OAuth
### 3.1 data/config.json（推荐）
在 `data/config.json` 中填入飞书应用信息：

```json
{
  "auth_authorize_url": "FEISHU_AUTH_AUTHORIZE_URL",
  "auth_token_url": "FEISHU_AUTH_TOKEN_URL",
  "auth_client_id": "YOUR_APP_ID",
  "auth_client_secret": "YOUR_APP_SECRET",
  "auth_redirect_uri": "http://localhost:8000/auth/callback",
  "auth_scopes": [
    "drive:drive",
    "docs:doc",
    "drive:meta",
    "contact:contact.base:readonly"
  ],
  "sync_mode": "bidirectional",
  "token_store": "keyring"
}
```

说明：
- OAuth 授权与 Token URL 请以飞书开放平台文档为准。
- 本地开发默认回调地址为 `http://localhost:8000/auth/callback`。
- Docker 生产环境回调地址为 `http://localhost:8080/api/auth/callback`。

### 3.2 环境变量（可覆盖）
- `LARKSYNC_SYNC_MODE`
- `LARKSYNC_DATABASE_URL` / `LARKSYNC_DB_PATH`
- `LARKSYNC_AUTH_AUTHORIZE_URL`
- `LARKSYNC_AUTH_TOKEN_URL`
- `LARKSYNC_AUTH_CLIENT_ID`
- `LARKSYNC_AUTH_CLIENT_SECRET`
- `LARKSYNC_AUTH_REDIRECT_URI`
- `LARKSYNC_AUTH_SCOPES`
- `LARKSYNC_TOKEN_STORE`

## 4. 本地开发启动
### 4.1 一键启动
在根目录执行：
- `npm run dev`

默认端口：
- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`

### 4.2 分别启动
- 后端：`cd apps/backend` 后执行 `uvicorn src.main:app --reload --port 8000`
- 前端：`cd apps/frontend` 后执行 `npm run dev`

## 5. 主要功能使用
### 5.1 登录与连接状态
- 打开前端页面，点击“登录飞书”。
- 授权完成后，前端会显示 Connected 状态。

### 5.2 云端目录树
- 页面点击“刷新目录”即可拉取云端目录树。
- 后端接口：`GET /drive/tree`（可选参数 `folder_token`）。

### 5.3 本地监听与事件日志
- 在前端输入本地目录并启动监听。
- 后端接口：
  - `POST /watcher/start`
  - `POST /watcher/stop`
  - `GET /watcher/status`
- WebSocket 事件：`/ws/events`

### 5.4 冲突中心
- 前端可查看冲突列表并执行“使用本地/云端”。
- 后端接口：
  - `GET /conflicts`
  - `POST /conflicts`
  - `POST /conflicts/check`
  - `POST /conflicts/{id}/resolve`

## 6. 图片上传（Markdown → Docx）
- 当 Markdown 中包含本地图片路径（如 `![](assets/logo.png)`）时，上传流程会：
  1) 调用飞书素材上传接口获取 `file_token`。
  2) 生成 Docx 图片块并插入文档。
- 建议使用相对路径，并确保 `base_path` 指向 Markdown 文件所在目录（当前为服务端接口参数，UI 尚未暴露）。

## 7. 生产部署（Docker）
- 构建镜像：`docker-compose build`
- 启动服务：`docker-compose up -d`
- 访问地址：`http://localhost:8080`
- 说明：生产环境通过 Nginx 将 `/api/*` 转发到后端。

## 8. 测试
- 后端单测：`cd apps/backend` 后执行 `python -m pytest`
- 前端暂无单测，建议执行 `npm run lint`（如已配置）。

## 9. 已知限制
- 同步任务配置向导、全量双向同步引擎仍在完善。
- 本地 → 云端的自动同步任务尚未暴露为 UI 操作。

本教程会随版本更新持续完善。
