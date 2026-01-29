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
### 3.0 网页配置向导（推荐）
在前端首页的“OAuth 配置向导”中填写并保存以下信息（详见 `docs/OAUTH_GUIDE.md`）：
- 授权地址（Authorize URL）
- Token 地址（Access Token URL）
- App ID / App Secret
- 回调地址（Redirect URI）
- 权限 scopes（逗号分隔）

参数获取步骤：
1) 登录飞书开放平台，创建企业自建应用。
2) 在“应用凭证”页面获取 App ID 与 App Secret。
3) 在“安全设置 / OAuth 回调”中添加回调地址：  
   - 开发：`http://localhost:8000/auth/callback`  
   - 生产：`http://localhost:8080/api/auth/callback`
4) 在“权限管理”中添加 scopes（建议最少）：  
   - `drive:drive`  
   - `docs:doc`  
   - `drive:drive.metadata:readonly`  
   - `contact:contact.base:readonly`
5) 在飞书 OAuth2 文档中查看授权地址与 Token 地址，并填入上方表单。

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
    "drive:drive.metadata:readonly",
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
### 5.0 同步任务配置
- 前端“同步任务配置”区域可新建任务，包含本地路径、云端文件夹 token 与同步模式。
- 支持“选择本地文件夹”按钮调用系统对话框（若不可用可手动输入路径）。
- 支持云端目录选择器，点击文件夹即可自动填充 token。
- 下载模式任务在保存后会自动触发一次同步，也可点击“立即同步”手动触发。
- 双向/仅上传任务在保存后会自动启动上传监听，并在“立即同步”时执行一次上传扫描。
- 支持停用/启用与删除任务。
- 任务卡片显示状态、进度与最近文件列表。
- 下载侧支持 Docx 与普通文件类型；Sheet/Bitable 等类型会显示为“跳过”。
- 若云端为快捷方式（Shortcut），会解析为目标类型后下载。
- 上传侧支持：
  - 已映射 Docx：本地 Markdown 变更会全量覆盖云端文档内容。
  - 新增普通文件：会上传到任务对应云端文件夹。
  - 非 MD 文件的“覆盖更新”与 Markdown 新建 Docx 仍需补齐导入接口样例。
- 文档内若链接到同步范围内的云端文件，会自动改写为本地相对路径；附件块会下载到同目录 `attachments/`。
- 后端接口：
  - `GET /sync/tasks`
  - `POST /sync/tasks`
  - `PATCH /sync/tasks/{id}`

### 5.1 登录与连接状态
- 打开前端页面，点击“登录飞书”。
- 授权完成后会自动跳转回前端首页，随后显示 Connected 状态。

### 5.2 云端目录树
- 页面点击“刷新目录”即可拉取云端目录树。
- 后端接口：`GET /drive/tree`（可选参数 `folder_token`）。
> 若提示 Access denied，请在飞书控制台“权限管理”添加用户身份权限（`drive:drive` 或 `drive:drive.metadata:readonly`），并重新授权。

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
- 建议使用相对路径，并确保 `base_path` 指向 Markdown 文件所在目录（可在同步任务配置中填写）。

### 6.1 手动触发 Markdown 替换上传
前端“手动上传 Markdown”区域支持直接触发上传；也可用接口触发 Markdown 全量覆盖上传（用于测试图片上传链路）：  
`POST /sync/markdown/replace`

请求示例：
```json
{
  "document_id": "doccnxxxx",
  "markdown_path": "C:/Docs/test.md",
  "task_id": "可选：同步任务 ID",
  "base_path": "可选：Markdown 基准路径"
}
```

## 7. 生产部署（Docker）
- 构建镜像：`docker-compose build`
- 启动服务：`docker-compose up -d`
- 访问地址：`http://localhost:8080`
- 说明：生产环境通过 Nginx 将 `/api/*` 转发到后端。

## 8. 测试
- 后端单测：`cd apps/backend` 后执行 `python -m pytest`
- 前端暂无单测，建议执行 `npm run lint`（如已配置）。

## 8.1 运行日志
- 后端运行日志默认写入：`data/logs/larksync.log`
- 日志会按 10MB 轮转并保留 10 天，方便排查同步/上传问题。

## 9. 已知限制
- Markdown 新建 Docx 需提供飞书导入接口样例以实现自动创建。
- 非 Markdown 文件的“覆盖更新”接口尚未接入。
- 文档内附件块若字段结构不同，请提供 docx blocks JSON 样例以完善解析。

本教程会随版本更新持续完善。
