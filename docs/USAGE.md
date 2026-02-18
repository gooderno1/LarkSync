# LarkSync 使用教程（持续更新）

本文档用于记录当前版本的使用与测试流程，会随项目迭代同步维护。

## 0. 当前版本（截至 2026-02-18）
- 最新发布记录：`v0.5.44`（见 `CHANGELOG.md` 顶部）
- 当前主线状态：`v0.5.44`（更新检查 404 友好化、公开前仓库清理）
- 后端版本：`apps/backend/pyproject.toml` 中为 `v0.5.44`
- 前端版本：`apps/frontend/package.json` 中为 `0.5.44`
- 根目录版本：`package.json` 中为 `v0.5.44`

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
  "upload_interval_value": 60,
  "upload_interval_unit": "seconds",
  "upload_daily_time": "01:00",
  "download_interval_value": 1,
  "download_interval_unit": "days",
  "download_daily_time": "01:00",
  "device_display_name": "我的主力设备",
  "delete_policy": "safe",
  "delete_grace_minutes": 30
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
- `LARKSYNC_DEVICE_NAME`（可选，作为设备显示名默认值）
- `LARKSYNC_DELETE_POLICY`（`off` / `safe` / `strict`）
- `LARKSYNC_DELETE_GRACE_MINUTES`（删除宽限时间，分钟）

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
托盘主进程与后端启动都会自动过滤不兼容 `PYTHONPATH`（例如误指向其它 Python 版本的 `site-packages`），避免本机环境污染导致 `npm run dev` 或托盘显示异常。
若托盘未显示，请先完整退出旧实例后重启（检查端口 `48901` 是否仍被占用），并确认已安装 `apps/backend/requirements.txt` 中的 `pystray` 与 `Pillow`。

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
- 每个任务可单独配置 MD 上传模式（默认 `enhanced`）：
  - `enhanced`：本地 MD 上行会更新云文档，并维护云端 `_LarkSync_MD_Mirror` 副本。
  - `download_only`：仅做云端下行，不执行本地 MD 上行。
  - `doc_only`：仅更新云文档，不保留云端 MD 副本（复杂格式可能有损耗风险）。
- 支持停用/启用与删除任务。
- 新建/编辑任务会执行映射约束校验（同设备同账号维度）：
  - 一个本地目录只能绑定一个云端目录。
  - 一个云端目录只能绑定一个本地目录。
  - 禁止父子本地目录同时创建任务（避免重复扫描和循环同步）。
- 任务卡片显示状态、进度与最近错误信息。
- 完成率按“`完成 / (总数 - 跳过)`”计算，跳过项不再拉低完成率。
- 长路径显示优化：本地/云端路径默认显示后半段；点击“展开”后会按换行完整展示，不再溢出边框。
- 测试任务不再按名称/路径关键词推断，统一以后端 `is_test` 字段识别；你新建任务默认是正式任务。
- 仅在开发/测试模式且存在 `is_test=true` 的任务时，页面才显示“显示/隐藏测试任务”按钮。
- 下载侧支持 Docx 与普通文件类型；Sheet/Bitable 等类型会显示为"跳过"。
- Docx 内嵌 `sheet` 会优先转 Markdown 表格；若本地仍是历史 `sheet_token` 占位，系统会在下次下载时自动重转一次（即使云端 mtime 未变化）。
- 若云端为快捷方式（Shortcut），会解析为目标类型后下载。
- 上传侧支持：
  - 已映射 Docx：本地 Markdown 变更会按 `update_mode` 执行局部或全量更新。
  - 新增普通文件：会上传到任务对应云端文件夹。
  - Markdown 新建 Docx：先导入创建云端文档，再覆盖内容。
  - 新建 Docx 导入完成后，会自动清理同目录用于导入的临时 `.md` 源文件，避免云端出现重复第三份文档。
- 文档内链接若指向已同步文件，会改写为本地相对路径；附件块会下载到同目录 `attachments/`。
- 同步日志在"日志中心"按时间倒序展示（默认每 5 秒刷新）。
- 日志筛选支持状态多选与任务多选：
  - 默认选择“所有日志（推荐）”，会展示全量状态并自动覆盖后续新增状态类型。
  - 可按任务复选过滤，不再是单选。
  - 删除联动相关状态可单独筛选：`delete_pending`（待删除）、`deleted`（删除成功）、`delete_failed`（删除失败）。
- 系统日志页默认“最新优先”；若后端不可达或读取失败，页面会显示明确错误提示。

### 5.2 同步策略（可配置）
- **本地 → 云端**：默认每 60 秒触发一次上传周期。
- **云端 → 本地**：默认每天 01:00 触发一次下载（可手动触发）。
- 间隔单位支持：秒 / 小时 / 天。
- 当单位为"天"时，需填写具体触发时间（HH:MM）。
- 自动更新开启后，系统会按“检查间隔（小时）”自动检查稳定版并自动下载更新包；安装仍需用户手动执行。
- 每次 OAuth 登录成功后，系统会额外触发一次“立即检查更新”。
- “更多设置”拥有独立保存按钮，不再和“同步策略”共用一次保存动作。
- “保存更多设置”按钮位于“展开/收起设置”旁，便于同一区域完成修改与提交。
- 删除同步策略（任务级，位于“同步任务 -> 任务管理”）：
  - `off`：关闭删除联动（本地/云端删除不会同步到另一侧）。
  - `safe`：启用墓碑+宽限期，宽限到期后执行删除；云端删除同步到本地时，先移动到 `.larksync_trash/`。
  - `strict`：不使用宽限期，删除会尽快联动执行。
  - 宽限时间单位为“分钟”；`strict` 模式下宽限固定为 `0`。
  - 删除失败会自动进入重试队列（5 分钟退避），避免历史 `failed` 长期不再执行。
  - 删除执行时会同步清理云端 `_LarkSync_MD_Mirror` 中对应 MD 副本，避免镜像残留。
- “设置 -> 更多设置”不再直接控制删除策略；仅保留全局默认值作为新任务初始值。
- 文档同步策略补充：
  - `enhanced` 模式：下行（云端 Docx → 本地 MD）和上行（本地 MD → 云端）都会同步维护 `_LarkSync_MD_Mirror`。
  - `download_only` 模式：仅云端下行，不执行本地 MD 上行。
  - `doc_only` 模式：上行只更新云文档，不保留 `_LarkSync_MD_Mirror` 副本。

### 5.3 登录与连接状态
- 打开前端页面，点击"连接飞书"。
- 授权完成后会自动跳转回前端首页，随后显示 Connected 状态。
- 首屏会先做真实授权状态检测，再决定是否进入引导向导；已授权时不会再闪现授权页。
- 侧边栏会显示“设备显示名称 + 飞书昵称”，用于用户可读展示。
- 设备显示名称可在“设置 -> 更多设置”中修改。
- 登录引导页支持明/暗主题切换；默认主题为明亮模式。
- 若出现“已连接（昵称未同步）”，表示 OAuth 主连接可用，但账号昵称还未补齐；重新授权并刷新页面通常可恢复。
  - 从 `v0.5.33` 起，后端会在 `/auth/status` 自动补齐 `open_id`。
  - 从 `v0.5.35` 起，后端会一并补齐并缓存飞书昵称（`name`）。

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

### 5.6 任务归属与设备验证
- 从 `v0.5.29` 起，同步任务按 **设备 + 飞书账号** 双重归属：
  - 设备维度：`device_id`
  - 账号维度：飞书 OAuth 返回的 `open_id`
- `device_id` / `open_id` 仅用于内部归属判断，不在主界面直接展示。
- 同设备多账号场景下，任务不会互相可见。
- 历史任务若缺少 `open_id`，会在首次访问时自动归属当前账号。
- 当前实现不引入独立本地账号体系，登录统一沿用飞书 OAuth。
- 从 `v0.5.33` 起，任务访问改为严格双重匹配（`owner_device_id` + `owner_open_id`），不再放行空 `owner_open_id` 任务。
- 对于历史空 `owner_open_id` 任务，系统仅会自动迁移“可确认为本机路径”的任务；其他历史任务会被隐藏，避免跨设备串任务。
- 若升级后发现旧任务不再显示，通常是历史任务未满足安全迁移条件；可在当前设备重新创建任务（推荐），或联系开发补充手动认领工具。

## 6. 图片与附件同步
- 当 Markdown 中包含本地图片路径（如 `![](assets/logo.png)`）时，上传流程会：
  1) 调用飞书素材上传接口获取 `file_token`。
  2) 生成 Docx 图片块并插入文档。
- 建议使用相对路径，并确保 `base_path` 指向 Markdown 文件所在目录（可在同步任务配置中填写）。

## 7. 测试
- 本地联调测试（默认）：
```bash
npm run dev
```
  - 启动托盘 + 前端 HMR + 后端热重载，作为日常本地测试入口。

- 打包体验测试（用户级）：
```bash
python scripts/build_installer.py
# Windows 安装包
python scripts/build_installer.py --nsis
# macOS 安装包
python scripts/build_installer.py --dmg
```
  - 产物安装后需验证：启动、托盘菜单、面板打开、退出流程。

- 后端（建议先进入干净虚拟环境）：
```bash
cd apps/backend
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest
```
- 前端：
```bash
cd apps/frontend
npm install
npm run build
npx tsc --noEmit
```
- 说明：若后端测试出现 `ImportError: cannot import name 'FixtureDef' from 'pytest'`，通常是本机全局 `pytest` 与 `pytest-asyncio` 版本冲突，建议使用项目虚拟环境重新安装依赖后再执行。

## 8. 运行日志
- 后端运行日志：`data/logs/larksync.log`（10MB 轮转，保留 10 天）
- 后端 stderr：`data/logs/backend-stderr.log`
- Vite 开发日志：`data/logs/vite-dev.log`（仅 `--dev` 模式）

## 9. 测试重置（可选）
- 如需模拟“新用户首次登录”并隔离历史任务数据，可执行：
  1) 停止当前运行中的 LarkSync。
  2) 归档 `data/larksync.db*` 到 `data/archive/<timestamp>/`。
  3) 清空本地 token（调用 `/auth/logout` 或清理 token 存储）。
  4) 重新启动 `npm run dev`，系统会自动创建空数据库。

## 10. 本地打包与安装包下载
### 10.1 本地打包（当前真实做法）
统一使用脚本：`scripts/build_installer.py`。

```bash
# 仅生成 PyInstaller 目录产物（dist/LarkSync/）
python scripts/build_installer.py

# Windows：额外生成 NSIS 安装包（dist/LarkSync-Setup-<version>.exe）
python scripts/build_installer.py --nsis

# macOS：额外生成 DMG（dist/LarkSync-<version>.dmg）
python scripts/build_installer.py --dmg
```

说明：
- 脚本默认会先构建前端（`apps/frontend/npm run build`），再执行 PyInstaller。
- 若前端已提前构建，可加 `--skip-frontend` 跳过前端构建阶段。
- Windows 生成安装包依赖 `makensis`（NSIS）；macOS 生成 DMG 依赖 `create-dmg`。
- 脚本会自动过滤与当前解释器版本不匹配的 `PYTHONPATH` `site-packages`（例如 `Python312` 与 `Python314` 混用），减少本机环境污染导致的打包失败。

### 10.2 GitHub Release 下载安装包
- 发布页：<https://github.com/gooderno1/LarkSync/releases>
- Windows：下载 `LarkSync-Setup-*.exe`
- macOS：下载 `LarkSync-*.dmg`

说明：
- 自动更新依赖公开可访问的 GitHub Release；若仓库私有、暂无 Release 或无稳定版 tag，客户端会显示“暂无稳定版 Release”，不会继续下载更新包。

## 11. 已知限制
- 非 Markdown 文件的"覆盖更新"接口尚未接入。
- 在线文档中的 `sheet` 内嵌表格当前为“优先转 Markdown 表格”；在权限不足、接口异常或超限场景下会回退为 `sheet_token` 占位输出。
- 文档内附件块若字段结构不同，请提供 docx blocks JSON 样例以完善解析。

本教程会随版本更新持续完善。
