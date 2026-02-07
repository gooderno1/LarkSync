# LarkSync 使用教程（持续更新）

本文档用于记录当前版本的使用与测试流程，会随项目迭代同步维护。

## 1. 环境准备
- Node.js 18+（用于前端）
- Python 3.10+（后端 FastAPI + 系统托盘）

## 2. 依赖安装
- 根目录：`npm install`
- 前端：`cd apps/frontend` 后执行 `npm install`
- 后端：`cd apps/backend` 后执行 `python -m pip install -r requirements.txt`
  - 开发依赖：`python -m pip install -r requirements-dev.txt`

## 3. 配置飞书 OAuth
### 3.1 设置页配置（推荐）
1) 先在飞书控制台完成：
   - 创建企业自建应用
   - 配置 OAuth 回调地址
   - 添加用户身份权限（Scopes）
2) 打开 LarkSync 的"设置"页，填写：
   - App ID
   - App Secret
   - Redirect URI

详细步骤见 `docs/OAUTH_GUIDE.md`。

> 授权地址 / Token 地址为可选项，通常留空即可使用默认值。

### 3.2 data/config.json（可选）
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
  "token_store": "keyring",
  "upload_interval_value": 2,
  "upload_interval_unit": "seconds",
  "upload_daily_time": "01:00",
  "download_interval_value": 1,
  "download_interval_unit": "days",
  "download_daily_time": "01:00"
}
```

说明：
- 回调地址统一为 `http://localhost:8000/auth/callback`。
- `auth_scopes` 为可选字段，默认值已内置。

### 3.3 环境变量（可覆盖）
- `LARKSYNC_SYNC_MODE`
- `LARKSYNC_DATABASE_URL` / `LARKSYNC_DB_PATH`
- `LARKSYNC_AUTH_AUTHORIZE_URL`
- `LARKSYNC_AUTH_TOKEN_URL`
- `LARKSYNC_AUTH_CLIENT_ID`
- `LARKSYNC_AUTH_CLIENT_SECRET`
- `LARKSYNC_AUTH_REDIRECT_URI`
- `LARKSYNC_AUTH_SCOPES`
- `LARKSYNC_TOKEN_STORE`
- `LARKSYNC_UPLOAD_INTERVAL_VALUE`
- `LARKSYNC_UPLOAD_INTERVAL_UNIT`
- `LARKSYNC_UPLOAD_DAILY_TIME`
- `LARKSYNC_DOWNLOAD_INTERVAL_VALUE`
- `LARKSYNC_DOWNLOAD_INTERVAL_UNIT`
- `LARKSYNC_DOWNLOAD_DAILY_TIME`

## 4. 启动（托盘模式）

LarkSync 统一通过 **系统托盘** 运行。启动后在系统托盘区域显示图标，右键菜单可打开管理面板、暂停/恢复同步、查看日志等。

### 4.1 开发调试（带热重载）

```bash
npm run dev
```

内部会启动：
- Vite 前端开发服务器（`http://localhost:3666`，HMR 热重载）
- uvicorn 后端（`http://localhost:8000`，`--reload` 热重载）
- 系统托盘图标

改前端代码即时生效，改后端代码自动重启。退出：托盘右键"退出"或 Ctrl+C。

Vite 日志输出到 `data/logs/vite-dev.log`。

### 4.2 日常使用（无热重载）

先构建前端，再启动托盘：

```bash
# 构建前端（代码更新后需重新执行）
python scripts/build.py

# 启动
# Windows：双击 LarkSync.bat 或 LarkSync.pyw
# macOS：双击 LarkSync.command
# 通用：python apps/tray/tray_app.py
```

前后端由 FastAPI 统一服务于 `http://localhost:8000`。

## 5. 主要功能使用
### 5.1 同步任务配置
- 前端"同步任务"页可新建任务，包含本地路径、云端文件夹 token 与同步模式。
- 支持"选择本地文件夹"按钮调用系统对话框（不可用时可手动输入路径）。
- 支持云端目录选择器，点击文件夹即可自动填充 token。
- 下载模式任务保存后会自动触发一次同步，也可点击"立即同步"手动触发。
- 双向/仅上传任务保存后会自动启动上传调度，按配置间隔处理本地变更队列。
- 支持停用/启用与删除任务。
- 任务卡片显示状态、进度与最近错误信息。
- 下载侧支持 Docx 与普通文件类型；Sheet/Bitable 等类型会显示为"跳过"。
- 若云端为快捷方式（Shortcut），会解析为目标类型后下载。
- 上传侧支持：
  - 已映射 Docx：本地 Markdown 变更会按 `update_mode` 执行局部或全量更新。
  - 新增普通文件：会上传到任务对应云端文件夹。
  - Markdown 新建 Docx：先导入创建云端文档，再覆盖内容。
- 文档内链接若指向已同步文件，会改写为本地相对路径；附件块会下载到同目录 `attachments/`。
- 同步日志在"日志中心"按时间倒序展示（默认每 5 秒刷新）。

### 5.2 同步策略（可配置）
- **本地 → 云端**：默认每 2 秒触发一次上传周期。
- **云端 → 本地**：默认每天 01:00 触发一次下载（可手动触发）。
- 间隔单位支持：秒 / 小时 / 天。
- 当单位为"天"时，需填写具体触发时间（HH:MM）。

### 5.3 登录与连接状态
- 打开前端页面，点击"连接飞书"。
- 授权完成后会自动跳转回前端首页，随后显示 Connected 状态。

### 5.4 云端目录树
- 页面点击"刷新"即可拉取云端目录树。
- 后端接口：`GET /drive/tree`（可选参数 `folder_token`）。
> 若提示 Access denied，请在飞书控制台"权限管理"添加用户身份权限（`drive:drive` 或 `drive:drive.metadata:readonly`），并重新授权。

### 5.5 冲突管理（日志中心子模块）
- 前端日志中心可查看冲突列表并执行"使用本地/云端"。
- 后端接口：
  - `GET /conflicts`
  - `POST /conflicts`
  - `POST /conflicts/check`
  - `POST /conflicts/{id}/resolve`

## 6. 图片与附件同步
- 当 Markdown 中包含本地图片路径（如 `![](assets/logo.png)`）时，上传流程会：
  1) 调用飞书素材上传接口获取 `file_token`。
  2) 生成 Docx 图片块并插入文档。
- 建议使用相对路径，并确保 `base_path` 指向 Markdown 文件所在目录（可在同步任务配置中填写）。

## 7. 测试
- 后端单测：`cd apps/backend` 后执行 `python -m pytest`
- 前端类型检查：`cd apps/frontend` 后执行 `npx tsc --noEmit`

## 8. 运行日志
- 后端运行日志：`data/logs/larksync.log`（10MB 轮转，保留 10 天）
- 后端 stderr：`data/logs/backend-stderr.log`
- Vite 开发日志：`data/logs/vite-dev.log`（仅 `--dev` 模式）

## 9. 已知限制
- 非 Markdown 文件的"覆盖更新"接口尚未接入。
- 文档内附件块若字段结构不同，请提供 docx blocks JSON 样例以完善解析。

本教程会随版本更新持续完善。
