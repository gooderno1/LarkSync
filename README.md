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
- 共享文件夹支持：目录树新增“共享文件夹”根节点，可直接选择共享空间目录
- 共享链接/Token 选择：当共享目录未出现在树中时可粘贴分享链接创建任务
- Docx 转 Markdown：支持标题/加粗/列表/引用/代码块/待办(含完成态)/表格/图片块解析与图片落盘，支持提及与提醒渲染
- 表格单元格增强：表格内列表/换行保留层级缩进，兼容嵌套待办文本容器
- 本地写入器：写入文件后强制同步云端 mtime
- 非文档下载：提供 Drive 文件下载器，直接写入本地目录
- 表格导出下载：飞书 sheet/bitable 自动导出为 xlsx 后落盘
- 表格导出增强：导出任务查询携带源文档 token，修复共享表格导出 400
- 文件名净化：自动替换 Windows 非法字符，避免下载失败
- 本地变更监听：Watchdog 防抖监听驱动上传队列
- Markdown 转 Docx：调用 Docx Block 接口执行全量覆盖（含 429 指数退避重试）
- Markdown 上行局部更新：基于 block 差异仅更新变更段落（partial 模式失败直接报错，避免静默全量覆盖）
- 同步任务支持更新模式：自动/局部/全量
- Markdown 图片上传：本地图片自动上传为 Docx 图片块并插入文档
- 通用文件上传：支持 upload_all / 分片上传，并在本地状态库记录 file_hash 与云端 token
- 冲突中心：持久化冲突记录与前端对比视图，支持“使用本地/云端”决策
- 同步任务配置向导：支持云端目录选择器、本地文件夹选择器与任务状态
- 下载型同步任务：支持立即同步、状态展示与删除
- 全新侧边栏仪表盘 UI：任务/冲突/设置分区与实时日志面板
- 组件化架构：pages / components / hooks / lib 分层，TanStack Query 数据管理
- 明暗主题切换：Inter + JetBrains Mono 字体，Zinc + Lark Blue 色板
- Toast 通知与确认弹窗：操作反馈即时可见，删除等危险操作需二次确认
- 新建任务分步向导：Step 1/2/3 引导式创建
- 冲突解决 Keep Both：支持使用本地/云端/保留双方三种策略
- WebSocket 实时日志流：连接后端 ws://host/ws/logs 推送日志
- 骨架屏与空状态引导：页面加载与无数据时的良好视觉体验
- 日志中心：支持日志筛选/搜索/加载更多，冲突管理作为子模块
- 日志读取优化：后端日志流式分页读取，支持历史滚动查看
- 同步任务管理：默认简洁视图，按需展开管理选项
- 双向/上传任务：本地变更上传（已映射 Docx 全量覆盖，普通文件新增上传）
- Markdown 新建 Docx：缺少映射时自动创建云端文档并覆盖内容
- Markdown file 映射直传：历史为 `file` 的 `.md` 继续按文件上传，不再强制迁移为 Docx
- 文档链接本地化：已同步且本地存在的云端链接自动改写为本地相对路径，未同步链接保持云端地址；附件落盘至 attachments
- 日志系统：后端运行日志写入 `data/logs/larksync.log`
- 开发控制台日志：`npm run dev` 输出同时写入 `data/logs/dev-console.log`
- 同步日志：前端按时间展示任务与文件同步事件
- 双向下载保护：bidirectional 模式下检测到本地文件较新时跳过下载，避免覆盖本地修改
- 块状态自愈：partial 模式遇到缺失块状态时自动初始化，避免“本地较新但无法上云”
- 云端同名去重：下载阶段对同一路径的同名云端文件按策略择一，避免映射漂移与重复覆盖
- 块级更新：Markdown 变更按块检测与更新，记录每块更新时间
- 上行一致性优化：列表续行/附件挂载/文本子块渲染优化，减少云端回写后的结构偏差
- 飞书频控重试：新增对 `99991400(request trigger frequency limit)` 的指数退避重试
- 飞书开发文档同步：`python scripts/sync_feishu_docs.py` 自动检查并下载最新手册
- 定时调度：本地变更队列按秒/小时/天触发上传；云端下载支持按秒/小时/天或每日定时（可配置）

## 快速开始

LarkSync 统一采用 **系统托盘模式** 运行，启动后在系统托盘区域显示图标，右键菜单可打开管理面板、暂停/恢复同步、查看日志、配置开机自启动等。

### 依赖安装

```bash
# 根目录（用于 npm run dev）
npm install

# 前端
cd apps/frontend && npm install

# 后端
cd apps/backend && pip install -r requirements.txt
```

### 开发调试（推荐日常开发使用）

一键启动：托盘 + 前端 Vite 热重载（3666）+ 后端 uvicorn --reload（8000）。

```bash
npm run dev
```

- 前端改代码 → Vite HMR 即时生效
- 后端改代码 → uvicorn 自动重启
- 托盘图标、菜单、通知等与正式版完全一致
- 退出：托盘右键"退出"或 Ctrl+C

### 日常使用（无需热重载）

先构建前端，再通过一键启动器运行，前后端统一由 FastAPI 服务于 `http://localhost:8000`。

```bash
# 构建前端（仅需执行一次，代码更新后重新构建）
python scripts/build.py

# 启动
# Windows：双击 LarkSync.bat 或 LarkSync.pyw
# macOS：双击 LarkSync.command
# 通用：python apps/tray/tray_app.py
```

### 打包为安装包（v0.5.0+）

```bash
python scripts/build_installer.py          # PyInstaller 打包
python scripts/build_installer.py --nsis   # Windows: 额外生成安装包
python scripts/build_installer.py --dmg    # macOS: 额外生成 DMG
```

### OAuth 配置

支持在设置页填写 App ID / Secret / Redirect URI，详细步骤见 `docs/OAUTH_GUIDE.md`。

### 开发文档更新

执行 `npm run sync:feishu-docs`（或 `python scripts/sync_feishu_docs.py`）同步飞书开发手册到 `docs/feishu/`。

### 配置

默认读取 `data/config.json`，可通过环境变量覆盖：
- `LARKSYNC_SYNC_MODE`：`bidirectional` / `download_only` / `upload_only`
- `LARKSYNC_DATABASE_URL` 或 `LARKSYNC_DB_PATH`
- `LARKSYNC_AUTH_AUTHORIZE_URL` / `LARKSYNC_AUTH_TOKEN_URL`
- `LARKSYNC_AUTH_CLIENT_ID` / `LARKSYNC_AUTH_CLIENT_SECRET`
- `LARKSYNC_AUTH_REDIRECT_URI`
- `LARKSYNC_AUTH_SCOPES`（逗号分隔）
- `LARKSYNC_TOKEN_STORE`（`keyring` / `memory`）
- `LARKSYNC_UPLOAD_INTERVAL_VALUE` / `LARKSYNC_UPLOAD_INTERVAL_UNIT` / `LARKSYNC_UPLOAD_DAILY_TIME`
- `LARKSYNC_DOWNLOAD_INTERVAL_VALUE` / `LARKSYNC_DOWNLOAD_INTERVAL_UNIT` / `LARKSYNC_DOWNLOAD_DAILY_TIME`
