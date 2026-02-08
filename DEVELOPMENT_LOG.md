# DEVELOPMENT LOG

## v0.5.0-dev.5 (2026-02-08)
- 目标：补齐 CI/CD 自动构建与 Release 上传。
- 结果：
  - 新增 GitHub Actions workflow，tag 发布时自动构建 Windows/macOS 安装包并上传到 Release。
  - 版本号升级至 v0.5.0-dev.5（backend）。
- 测试：未执行（需在 GitHub Actions 触发 tag 构建验证）。
- 问题：无。

## v0.5.0-dev.4 (2026-02-08)
- 目标：补齐 macOS 打包流程（.app + DMG）。
- 结果：
  - PyInstaller spec 增加 macOS .app bundle 产物配置。
  - 新增 `scripts/installer/macos/create_dmg.sh`，统一 DMG 生成脚本（支持版本号命名）。
  - build_installer 走 DMG 脚本并传入版本号。
  - 版本号升级至 v0.5.0-dev.4（backend）。
- 测试：未执行（需 macOS 下打包验证）。
- 问题：待在 macOS 真机验证 .app 产物与 DMG 拖拽安装流程。

## v0.5.0-dev.3 (2026-02-08)
- 目标：补齐 Windows 安装包脚本（NSIS）。
- 结果：
  - 新增 `scripts/installer/nsis/larksync.nsi`，支持安装/卸载、开始菜单与桌面快捷方式。
  - build_installer 支持传入版本号与根路径给 NSIS。
  - 版本号升级至 v0.5.0-dev.3（backend）。
- 测试：未执行（需 Windows 下安装/卸载验证）。
- 问题：待你实际安装测试确认。

## v0.5.0-dev.2 (2026-02-08)
- 目标：补齐 PyInstaller 打包配置，确保 bundle 资源可用。
- 结果：
  - 新增 `scripts/larksync.spec` 并纳入版本控制（.gitignore 放行）。
  - 打包资源路径调整：前端 dist、托盘图标、品牌资源随包内置。
  - 运行时路径支持 PyInstaller bundle（backend/tray 自动识别 _MEIPASS）。
  - 版本号升级至 v0.5.0-dev.2（backend）。
- 测试：`python -m pytest tests/test_paths.py`（apps/backend）。
- 问题：需在 Windows/macOS 真机验证 PyInstaller 产物启动与静态资源加载。

## v0.5.0-dev.1 (2026-02-08)
- 目标：为打包发布做准备，运行数据迁移到用户目录并支持覆盖配置。
- 结果：
  - data/logs/db 默认写入用户数据目录（安装版），开发模式保持仓库 data/。
  - 新增 `LARKSYNC_DATA_DIR` 环境变量覆盖运行数据目录。
  - 转码附件与图片资产目录迁移到新 data 目录。
  - 版本号升级至 v0.5.0-dev.1（backend）。
- 测试：`python -m pytest tests/test_paths.py`（apps/backend）。
- 问题：无。

## v0.4.0-dev.21 (2026-02-08)
- 目标：将升级计划迁入本地文档目录，并细化自动更新设计与版本号规则。
- 结果：
  - `docs/UPGRADE_PLAN.md` 迁移至 `docs/local_specs/UPGRADE_PLAN.md`（本地资料，不进 Git）。
  - 自动更新设计细化（更新源/清单/流程/回滚/配置项）。
  - 补充版本号规则：小改动递增 dev；中等变更递增 patch；阶段性变更递增 minor。
  - 版本号同步为 v0.4.0-dev.21（backend）。
- 测试：未执行（文档迁移与设计细化）。
- 问题：无。

## v0.4.0-dev.20 (2026-02-08)
- 目标：按升级计划补齐托盘状态回归测试，并新增自动更新规划。
- 结果：
  - 托盘状态聚合新增回归用例（running/paused/last_error 统计）。
  - 导出任务失败状态补充回归测试（job_status/job_error_msg）。
  - 升级计划新增“自动更新”阶段。
  - 版本号同步为 v0.4.0-dev.20（backend）。
- 测试：`python -m pytest tests/test_tray_status.py tests/test_sync_runner.py`（apps/backend）。
- 问题：无。

## v0.4.0-dev.19 (2026-02-08)
- 目标：定位数据库损坏根因并降低发生概率。
- 结果：
  - 托盘停止后端优先调用 `/system/shutdown`，后端先停调度器/监听器并释放数据库连接再退出。
  - SQLite 连接启用 WAL + busy_timeout/foreign_keys，提升异常退出场景的鲁棒性。
  - 版本号同步为 v0.4.0-dev.19（backend）。
- 测试：`python -m pytest tests/test_system_api.py tests/test_db_session.py`（apps/backend）。
- 问题：若仍出现损坏，请排查外部强杀/异常断电/网盘同步等系统层面因素。

## v0.4.0-dev.18 (2026-02-08)
- 目标：修复客户端启动超时（SQLite 损坏导致后端启动失败）。
- 结果：
  - 启动时检测 SQLite 损坏并自动备份为 `.corrupt-YYYYMMDD-HHMMSS`，随后重建数据库。
  - 保留原损坏库以便手动修复/恢复。
  - 版本号同步为 v0.4.0-dev.18（backend）与 0.4.0-dev.12（frontend）。
- 测试：`python -m pytest tests/test_db_session.py`（apps/backend）。
- 问题：如需恢复历史任务，请从备份 DB 手动迁移数据。

## v0.4.0-dev.17 (2026-02-08)
- 目标：修复剩余失败（DB 映射异常导致的同步失败）；新增日志保留与提醒设置。
- 结果：
  - SyncLink 数据库异常时降级为“仅记录日志、不阻断同步”，避免单文件失败。
  - 同步日志支持保留天数清理与容量提醒阈值，系统日志默认保留 1 天并支持配置。
  - 日志中心新增容量提醒展示；设置页新增“更多设置”可配置日志保留与提醒。
  - 版本号同步为 v0.4.0-dev.17（backend）与 0.4.0-dev.11（frontend）。
- 测试：`python -m pytest tests/test_sync_link_service.py tests/test_sync_event_store.py tests/test_log_reader.py`（apps/backend）。
- 问题：若 SQLite 仍提示损坏，请备份 `data/larksync.db` 后重建。

## v0.4.0-dev.16 (2026-02-08)
- 目标：修复表格导出轮询过早失败；日志中心恢复自动刷新。
- 结果：
  - 导出任务轮询对短时非 0 状态更宽容，避免误判失败，并补充超时状态提示。
  - 导出轮询默认次数提升至 20 次（约 20s）。
  - 日志中心同步/系统日志增加自动刷新轮询（5s）。
  - 版本号同步为 v0.4.0-dev.16（backend）与 0.4.0-dev.10（frontend）。
- 测试：`python -m pytest tests/test_sync_runner.py`（apps/backend）。
- 问题：若 sheet/bitable 仍失败，请提供导出任务结果 JSON（含 job_status/job_error_msg）。

## v0.4.0-dev.15 (2026-02-08)
- 目标：同步日志需持久化保留历史；系统日志不再为空；sheet/bitable 导出补齐子表 ID。
- 结果：
  - 新增同步日志 JSONL 持久化与 `/sync/logs/sync` 接口，日志中心/仪表盘改为读取历史日志。
  - 日志路径统一使用 core.paths 解析，系统日志读取与写入一致。
  - sheet/bitable 导出补齐子表 ID（缺失时尝试拉取子表列表），导出失败日志包含 sub_id。
  - 版本号同步为 v0.4.0-dev.15（backend）与 0.4.0-dev.9（frontend）。
- 测试：`python -m pytest tests/test_sync_event_store.py tests/test_sync_runner.py tests/test_log_reader.py`（apps/backend）。
- 问题：若 sheet/bitable 仍失败，请提供对应 API JSON 返回（含子表列表或导出任务结果）。

## v0.4.0-dev.14 (2026-02-08)
- 目标：修复表格导出仍失败的问题并确保系统日志读取到历史文件。
- 结果：
  - 表格导出在缺少 sub_id 时，自动通过 Drive 元数据补齐链接并解析 table/sheet id。
  - 系统日志 API 使用正确根路径读取 `data/logs/larksync.log`，历史日志可见。
  - 版本号同步为 v0.4.0-dev.14。
- 测试：`python -m pytest tests/test_sync_runner.py tests/test_log_reader.py tests/test_sync_runner_upload_new_doc.py`（apps/backend）。
- 问题：若导出仍失败，请提供带 table/sheet 参数的分享链接或最新错误日志。

## v0.4.0-dev.13 (2026-02-08)
- 目标：修复 sheet/bitable 导出失败并补齐日志历史展示与回流下载防护。
- 结果：
  - 表格导出失败时尝试携带 sub_id（从分享链接解析）进行重试。
  - 系统日志支持最早/最新排序；UI 默认最早优先，便于查看历史。
  - 上传完成后记录同步时间戳，避免云端更新回流重复下载。
  - 版本号同步为 v0.4.0-dev.13。
- 测试：`python -m pytest tests/test_sync_runner.py tests/test_log_reader.py tests/test_sync_runner_upload_new_doc.py`（apps/backend）。
- 问题：若 bitable/sheet 仍失败，请提供带 table/sheet 参数的分享链接或最新错误日志。

## v0.4.0-dev.12 (2026-02-08)
- 目标：避免云端未更新时重复下载；在线幻灯片导出改为跳过；导出失败信息更易排查。
- 结果：
  - 下载阶段基于已同步记录与云端 mtime 判断未更新则跳过下载。
  - 移除 slides 导出映射，在线幻灯片下载时直接跳过。
  - 导出任务失败信息包含 job_status 与 job_error_msg。
  - 版本号同步为 v0.4.0-dev.12。
- 测试：`python -m pytest tests/test_sync_runner.py`（apps/backend）。
- 问题：bitable 导出失败原因待确认，请提供最新错误日志（含 job_status / msg）。

## v0.4.0-dev.11 (2026-02-08)
- 目标：补齐在线幻灯片导出为本地 pptx。
- 结果：
  - 导出类型新增 slides → pptx。
  - 下载阶段覆盖幻灯片的导出落盘路径与测试用例。
  - 版本号同步为 v0.4.0-dev.11。
- 测试：`python -m pytest tests/test_sync_runner.py`（apps/backend）。
- 问题：官方导出指南未列出 slides 参数细节，若仍报错请提供 API JSON 样例以确认类型/扩展名。

## v0.4.0-dev.10 (2026-02-08)
- 目标：修复共享表格导出任务查询 400，并补充错误细节便于排查。
- 结果：
  - 导出任务查询携带源文档 token，符合导出指南说明。
  - 导出任务错误信息包含 HTTP 状态与 API code。
  - 版本号同步为 v0.4.0-dev.10。
- 测试：`python -m pytest tests/test_export_task_service.py tests/test_sync_runner.py`（apps/backend）。
- 问题：官方导出指南未包含 slides/pptx 导出，仍需补充官方 API 说明或 JSON 样例。

## v0.4.0-dev.9 (2026-02-08)
- 目标：修复非法文件名导致下载失败，补齐 sheet/bitable 导出下载，并优化日志读取性能与历史保留。
- 结果：
  - 新增导出任务服务，sheet/bitable 下载时自动导出为 xlsx 并落盘。
  - 下载与附件落盘统一做文件名净化，避免 Windows 非法字符。
  - 日志读取改为流式分页；日志文件显式追加写入。
  - 版本号同步为 v0.4.0-dev.9。
- 测试：`python -m pytest tests/test_export_task_service.py tests/test_log_reader.py tests/test_path_sanitizer.py tests/test_file_downloader.py tests/test_sync_runner.py`（apps/backend）。
- 问题：飞书导出任务未覆盖 slides（PPT 在线文档），需补充官方 API 说明或 JSON 样例。

## v0.4.0-dev.8 (2026-02-08)
- 目标：明确“非所有者共享文件夹需使用分享链接/Token”的提示，降低误解。
- 结果：
  - 新建任务 Step 2 的共享链接提示文案补充说明（非所有者共享需链接/Token）。
  - 版本号同步为 v0.4.0-dev.8。
- 测试：未执行（文案更新）。
- 问题：无阻塞问题。

## v0.4.0-dev.7 (2026-02-08)
- 目标：共享目录树缺失时支持通过分享链接/Token 手动选择云端目录。
- 结果：
  - 新建任务 Step 2 新增“共享链接 / Token”输入框，支持粘贴分享链接或直接输入 Token。
  - 可选“云端目录显示名称”，用于任务列表展示；未填写则回退到 token。
  - 版本号同步为 v0.4.0-dev.7。
- 测试：未执行（UI 交互变更）。
- 问题：无阻塞问题。

## v0.4.0-dev.6 (2026-02-08)
- 目标：支持共享文件夹目录选择，保证云端目录树覆盖“我的空间/共享文件夹”。
- 结果：
  - DriveService 支持 `root_folder_type=share` 获取共享根目录；`/drive/tree` 返回虚拟根节点“云空间”，包含“我的空间/共享文件夹”两棵子树。
  - 目录树解析新增快捷方式处理，遇到 `shortcut` 指向文件夹时自动展开为真实目录。
  - 前端目录树支持 `root` 节点展示但不可选，路径展示忽略虚拟根。
  - 版本号同步为 v0.4.0-dev.6。
- 测试：`python -m pytest apps/backend/tests/test_drive_service.py`。
- 问题：暂无阻塞问题。

## v0.4.0-dev.5 (2026-02-08)
- 目标：修复前端 Logo/Favicon 白色背景问题，优化图标大小和圆角。
- 问题分析：
  - 品牌 Logo 原图 (logo-horizontal.png) 带有白色/浅灰色不透明背景，在深色侧边栏上显示为丑陋的白色矩形。
  - Favicon 同样带有白色背景，浏览器标签中视觉效果差。
  - 侧边栏 Logo 尺寸 h-14/h-16 (56-64px) 对于 w-72 的侧边栏过大。
  - 亮色主题下 `bg-zinc-950/80` 未正确适配。
- 结果：
  - **新增 `scripts/process_logo.py` 图片处理工具**：
    - 基于 PIL/Pillow 自动去除品牌 Logo 白色/近白色背景像素，替换为透明。
    - 对边缘像素进行渐变透明处理（抗锯齿平滑过渡，smooth_range=25）。
    - 自动裁剪多余透明区域，并缩放到合理的 Web 尺寸（横版 Logo max_width=600px）。
    - 原始 2816x1536 (5.2MB) → 600x97 透明 PNG (59KB)。
  - **Favicon 重制**：
    - 去除白色背景后，改为完全透明背景，图标自然融入浏览器标签（适配深色/浅色主题）。
    - 192x192 PNG（padding=12）+ 32x32 ICO（padding=1 保证辨识度）。
  - **Sidebar.tsx Logo 样式优化**：
    - 高度从 `h-14 sm:h-16` → `h-9` (36px)，比例更协调。
    - 去除 Logo 容器的边框（`border border-zinc-800/70`）和深色背景（`bg-zinc-950/80`），Logo 直接融入侧边栏背景，与页面整体风格一致。
    - 保留品牌色光晕 `drop-shadow-[0_1px_6px_rgba(51,112,255,0.3)]`。
  - **亮色主题适配**：`index.css` 新增 `bg-zinc-950/80` 的亮色主题映射。
  - 版本号同步为 v0.4.0-dev.5。
- 修改文件：
  - `scripts/process_logo.py` (新增)
  - `apps/frontend/public/logo-horizontal.png` (重新生成 - 透明底色)
  - `apps/frontend/public/favicon.png` (重新生成 - 深色圆角)
  - `apps/frontend/public/favicon.ico` (重新生成 - 深色圆角)
  - `apps/frontend/src/components/Sidebar.tsx` (Logo 尺寸和样式)
  - `apps/frontend/src/index.css` (亮色主题 bg-zinc-950/80 适配)
- 测试：视觉验证，lint 无报错。
- 问题：无阻塞。

## v0.4.0-dev.4 (2026-02-08)
- 目标：托盘状态闭环，托盘提示未解决冲突，并补充状态接口测试；修复前端 Logo 清晰度。
- 结果：
  - `/tray/status` 接入冲突统计（读取 ConflictService），托盘检测到未解决冲突时切换 error 状态并去重提醒。
  - 新增回归测试 `tests/test_tray_status.py`，使用临时 SQLite 验证未解决冲突计数随解决状态变化。
  - 前端侧边栏产品 Logo 放大并加阴影，解决图标过小、压缩模糊问题。
  - 版本号同步为 v0.4.0-dev.4；CHANGELOG/UPGRADE_PLAN 进度更新。
- 测试：`python -m pytest apps/backend/tests/test_tray_status.py`（通过，存在 FastAPI on_event Deprecation 警告）。
- 问题：需后续补充 tray 聚合接口与状态机的更多用例；大文件模块回归测试仍待覆盖。

## v0.4.0-dev.3 (2026-02-07)
- 目标：统一托盘模式为唯一运行方式；增加 `--dev` 热重载开发支持；删除 Docker 部署。
- 结果：
  - **统一托盘模式**：LarkSync 不再有独立的"开发模式"和"生产模式"之分，所有场景统一通过托盘应用入口。区别仅在于是否启用热重载。
  - **`--dev` 参数**（`tray_app.py`）：
    - 新增 `--dev` 命令行参数，启动时同时拉起 Vite 前端开发服务器（3666）+ uvicorn --reload（8000）+ 系统托盘。
    - 前端改代码 → Vite HMR 即时生效；后端改代码 → uvicorn 自动重启。
    - Vite 子进程随托盘退出一起关闭（Windows 使用 taskkill /T 终止进程树）。
    - Vite 日志输出到 `data/logs/vite-dev.log`。
  - **`backend_manager.py` 增强**：`BackendManager` 构造函数接收 `dev_mode` 参数，dev 模式下 uvicorn 命令自动追加 `--reload`。
  - **`npm run dev` 改造**：根目录 `package.json` 的 `scripts.dev` 从 `node scripts/dev.js` 改为 `python apps/tray/tray_app.py --dev`。
  - **删除旧开发脚本**：移除 `scripts/dev.js`（Node.js 并行启动脚本）。
  - **删除 Docker 部署**：移除 `Dockerfile`、`docker-compose.yml`、`nginx.conf`。LarkSync 是桌面同步工具，Docker 部署不适用。
  - **URL 检测优化**（`config.py`）：`_detect_frontend_url()` 默认 fallback 改为 8000（而非 3666），确保无 dist 且无 Vite 时指向后端。
  - **文档全面更新**：README、USAGE.md、CHANGELOG、DEVELOPMENT_LOG、UPGRADE_PLAN 统一为托盘模式说明。
- 测试：Python 编译检查全部通过。
- 问题：无阻塞问题。

## v0.4.0-dev.2 (2026-02-07)
- 目标：修复托盘启动问题 + 品牌视觉集成 + 静态文件服务修复。
- 结果：
  - **端口冲突修复**（`backend_manager.py`）：启动前检测端口占用，已有后端自动复用（设为 `_external_backend` 模式）。子进程 stderr 重定向到 `data/logs/backend-stderr.log` 便于诊断。外部后端不可达时自动切换为自启模式。
  - **单实例锁**（`tray_app.py`）：通过绑定锁端口 48901 防止多实例启动。重复启动时直接打开浏览器并退出。
  - **BAT 简化**（`LarkSync.bat`）：移除 taskkill 进程清理（避免误杀开发环境进程），简化为纯启动器，进程管理由单实例锁负责。
  - **SPA fallback 修复**（`main.py`）：修复 dist 根目录静态文件（favicon.png、logo-horizontal.png 等）未被正确服务的问题。新逻辑：先检查 dist 下是否有对应文件，存在则直接返回（含 MIME 类型映射），不存在才走 SPA fallback。
  - **开发/生产 URL 自动检测**（`config.py`）：`_detect_frontend_url()` 函数根据端口活跃状态和 `dist/` 是否存在自动选择前端地址。
  - **品牌 Logo 集成**：
    - 托盘图标：基于 `assets/branding/LarkSync_Logo_Icon_FullColor.png` 生成 4 种状态变体（idle 原色 / syncing 增强 / error 红色着色 / paused 灰度），带裁白边 + 抗锯齿缩放。
    - Favicon：`favicon.ico`（16/32/48px）+ `favicon.png`（192px）写入 `public/`，`index.html` 添加引用。
    - 侧边栏：替换 SVG 占位图标为横版品牌 Logo（`logo-horizontal.png`）。
  - **品牌资源归档**：三个 Logo 文件统一存放在 `assets/branding/` 目录（Icon / Horizontal / CompactVertical）。
- 测试：`npx tsc --noEmit`（零错误）；Python 编译检查全部通过；`npm run build` 产物验证通过；8000 端口验证 favicon/logo/JS 均为新版。
- 问题：无阻塞问题。

## v0.4.0-dev.1 (2026-02-07)
- 目标：实现系统托盘桌面化，让 LarkSync 成为一个后台静默运行的桌面应用。
- 设计文档：`docs/design/v0.4.0-desktop-tray-design.md`
- 升级计划：`docs/UPGRADE_PLAN.md`
- 结果：
  - **FastAPI 静态文件服务**（`main.py`）：检测 `apps/frontend/dist/` 目录，自动挂载 `/assets` 静态资源 + SPA fallback（非 API 路径返回 `index.html`）。一个 uvicorn 进程即可提供完整服务。CORS 增加 `localhost:8000`。
  - **前端 API 基址可配**（`api.ts`）：`apiBase` 改为通过 `VITE_API_BASE` 环境变量配置，默认空字符串（同源服务无需前缀）。Docker/Nginx 部署时可设 `/api`。
  - **构建脚本**（`scripts/build.py`）：自动构建前端 + 验证产物 + 打印单进程启动指南。
  - **系统托盘应用**（`apps/tray/`）：
    - `tray_app.py`：pystray 主程序，右键菜单（打开面板/立即同步/暂停恢复/设置/日志/自启动/退出），双击图标默认打开浏览器。
    - `backend_manager.py`：后端进程管理器（subprocess 启动 uvicorn、健康检查、优雅关闭、异常自动重启最多 3 次）。Windows 使用 `CREATE_NO_WINDOW` 避免弹出终端。
    - `icon_generator.py`：Pillow 程序化生成 4 种状态图标（idle/syncing/error/paused），64px 带抗锯齿圆形。
    - `status_poller.py`（内置于 tray_app）：每 5 秒轮询 `/tray/status` 更新图标颜色。
    - `notifier.py`：plyer 跨平台通知 + 60 秒去重 + Windows PowerShell toast fallback。
    - `autostart.py`：Windows Startup 快捷方式（PowerShell/win32com）/ macOS LaunchAgent plist。
    - `config.py`：端口、超时、URL 等集中配置。
  - **一键启动器**：
    - `LarkSync.pyw`（Windows）：双击无终端启动托盘 → 自动拉起后端 → 打开浏览器。
    - `LarkSync.command`（macOS）：同上。
  - **后端新增接口**：`GET /tray/status` 返回任务/运行/错误聚合状态，供托盘轮询。
  - **打包支持**（`scripts/build_installer.py`）：
    - PyInstaller spec 自动生成 + 打包（`--windowed`，无终端）。
    - Windows NSIS 安装包 / macOS DMG 预留接口。
  - **依赖更新**：`requirements.txt` 新增 pystray、Pillow、plyer。
  - **`.gitignore`**：排除 `build/`、`dist/`、`*.spec`、`apps/tray/icons/`。
- 测试：`npx tsc --noEmit`（零错误）；Python 编译检查全部通过（11 个模块）。
- 问题：首次使用需 `pip install pystray Pillow plyer`。PyInstaller 打包需要在目标平台上执行（Windows 打 .exe，macOS 打 .app）。

## v0.3.0-dev.6 (2026-02-07)
- 目标：日志展示全面改造——页码分页、滚动优化、后端分页接口；飞书频率限制智能重试。
- 结果：
  - 前端：新建 `Pagination` 通用分页组件，支持页码导航、省略号折叠、每页条数选择器、总数摘要。
  - 前端（LogCenterPage）：「同步日志」和「系统日志」标签页均从"加载更多"改为完整页码分页；筛选器变更自动重置页码；列表区域限高 520px + 自定义滚动条。
  - 前端（DashboardPage）：仪表盘同步日志从 12 条增加到 20 条，高度从 384px 增加到 480px；新增总数提示和"查看全部 → 日志中心"快捷入口。
  - 后端：`GET /sync/logs/file` 接口返回格式从 `list[LogFileEntry]` 改为 `{total, items}` 分页结构；新增 `offset` 参数支持服务端分页。
  - 全局：自定义滚动条增加 Firefox 兼容（`scrollbar-width`/`scrollbar-color`）和明亮模式适配。
  - 后端（docx_service）：`_handle_create_children_error` 新增频率限制（99991400）检测——遇到频率限制先指数退避等待（2s → 4s → 8s，最多 3 次）再整体重试，而非立即拆分产生更多请求。
- 测试：`npx tsc --noEmit`（零错误）；Python 编译检查全部通过。
- 问题：日志文件较大时（>5MB），后端全量读取再过滤可能有性能瓶颈，后续可考虑流式读取或索引。

## v0.3.0-dev.5 (2026-02-07)
- 目标：云端目录显示文件夹名称；补齐完整历史日志查看能力。
- 结果：
  - 后端：SyncTask 模型新增 `cloud_folder_name` 字段，DB 迁移自动添加列；API 创建/更新/查询均支持。
  - 后端：新增 `GET /sync/logs/file` API，读取 loguru 日志文件，支持 limit/level/search 参数筛选。
  - 前端：新建任务时自动将 `selectedCloud.path`（如 "云盘/个人记录/"）存入 `cloud_folder_name`。
  - 前端：任务列表与仪表盘显示 `cloud_folder_name`，fallback 到 token。
  - 前端：日志中心新增「系统日志」标签页，直接展示 loguru 文件日志（含时间戳、级别、完整消息），支持级别筛选与关键词搜索，可查看 403/400 等历史错误。
- 测试：`npx tsc --noEmit`（零错误）；Python ast.parse 全部通过。
- 问题：已有任务的 `cloud_folder_name` 为空（旧数据），需要用户重新编辑或创建新任务才会有值。

## v0.3.0-dev.4 (2026-02-07)
- 目标：彻底消除非仪表盘页面的双重 Header；OAuth 教程页支持明亮模式。
- 结果：
  - 非仪表盘页面不再渲染 Header 组件——各页面（Tasks/LogCenter/Settings）自带头部卡片已包含标题，只需在其操作按钮区域融入 ThemeToggle 即可。
  - 新增 `ThemeToggle` 独立组件，供各页面复用。
  - Header 简化为仅服务仪表盘的 banner（不再有 NavKey / 多页逻辑）。
  - OAuth 教程页 `oauth-guide.html` 新增 light theme CSS 变量 + "切换主题"按钮，跟随主应用 localStorage 记忆。
- 测试：`npx tsc --noEmit`（零错误）。
- 问题：暂无阻塞问题。

## v0.3.0-dev.3 (2026-02-07)
- 目标：修复 Header 双重冗余、弹窗虚化、明亮模式策略配色、新增 OAuth 教程页。
- 结果：
  - Header 重设计：仪表盘保留完整 banner（标题+描述+状态+暂停+主题切换）；其他页改为轻量工具栏（页名+主题切换图标按钮），消除"双 header"冗余。
  - 弹窗遮罩：NewTaskModal 和 ConfirmDialog 去除 `backdrop-blur-sm`，改为纯暗色遮罩 `bg-black/50`。
  - 明亮模式修复：补齐 `bg-emerald-500/15`、`bg-[#3370FF]/15`、`bg-zinc-950/40`、`hover:border-zinc-700` 在 light theme 下的覆盖规则。
  - OAuth 教程页：新增 `public/oauth-guide.html` 静态页面，暗色主题、分步卡片、权限表格、常见问题；设置页 OAuth 区域添加"查看配置教程 ↗"链接，新标签打开。
  - 侧边栏移除主题切换按钮（已在 Header 中统一提供）。
- 测试：`npx tsc --noEmit`（零错误）。
- 问题：暂无阻塞问题。

## v0.3.0-dev.2 (2026-02-07)
- 目标：修复明亮模式交互缺陷，精简冗余 UI，优化设置与新建任务视觉。
- 结果：
  - Header 精简：非仪表盘页面移除连接状态/暂停控制/主题切换，仅保留标题描述；主题切换移至侧边栏底部。
  - 明亮模式修复：补齐 `hover:bg-zinc-800`/`bg-emerald-500/20`/`bg-amber-500/20` 等语义色在 light theme 下的覆盖规则，按钮悬浮不再出现深色主题底色。
  - 同步策略页重设计：默认同步模式改为卡片选择器；上行/下行间隔改为双列卡片布局，配图标与描述；移除拥挤的三列 grid。
  - 新建任务弹窗优化：步骤指示器改为 tab 式（编号+标签）；表单区与导航区分离（header/body/footer 三段式）；更新模式改为卡片选择器；任务摘要改为 key-value 表格。
  - Redirect URI 自动生成：基于 `window.location.origin + apiUrl("/auth/callback")` 计算，用户只需复制填入飞书后台，无需手动输入。
  - 云端 token 显示截短：任务列表与仪表盘中长 token 截断显示，hover 查看完整值。
- 测试：`npx tsc --noEmit`（零错误）。
- 问题：暂无阻塞问题。

## v0.3.0-dev.1 (2026-02-07)
- 目标：前端 UI/UX 全面重构——架构拆分、组件化、视觉对齐与实时增强。
- 结果：
  - 架构拆分：App.tsx 从 ~2200 行拆为 pages/components/hooks/lib 分层结构。
  - 数据层：引入 TanStack Query 替代原始 fetch，统一缓存与轮询。
  - UX 增强：新增 Toast 通知、确认弹窗、分步向导、冲突 Keep Both。
  - 视觉对齐：字体 Inter + JetBrains Mono；色板 Zinc + Lark Blue；移除 CSS !important hack。
  - 实时增强：WebSocket 日志流、骨架屏加载、空状态引导组件。
- 测试：`npx tsc --noEmit`（零错误）。
- 问题：sandbox 环境 npm 离线限制，部分外部包（lucide-react/sonner）以自定义组件替代，待线上安装。

## v0.2.0-dev.2 (2026-02-06)
- 目标：默认明亮主题；任务页按参考设计重做；同步策略支持秒/小时/天；配置指南仅保留文档。
- 结果：
  - 任务页重构为路径流向卡片 + 状态/进度/管理分区，操作按钮集中且可折叠管理。
  - 头部 banner 去除重复模块标题；明亮主题按钮对比度增强。
  - OAuth 设置页精简为 App ID/Secret/Redirect URI，权限说明移至文档。
  - 设置页移除“高级工具”入口（手动上传/本地监听），保留任务驱动同步流程。
  - 同步策略支持上传/下载“数值 + 单位（秒/小时/天）+ 按天时间”配置。
  - 更新 `docs/OAUTH_GUIDE.md`、`docs/USAGE.md`、`docs/SYNC_LOGIC.md` 与 README 同步说明。
- 测试：未执行（前端 UI/文档更新 + 调度配置调整）。
- 问题：暂无阻塞问题。

## v0.2.0-dev.1 (2026-02-06)
- 目标：重构前端信息架构与配置体验；补齐明亮主题可用性。
- 结果：
  - 新增日志中心页，支持日志筛选/搜索/加载更多，冲突管理作为子模块展示。
  - 同步任务加入简洁/详细视图切换，默认简洁展示，减少干扰。
  - OAuth 配置简化并新增“配置指南”独立页面与快速跳转。
  - 手动上传/本地监听收纳为高级工具，减少默认页面噪音。
  - 明亮主题补齐按钮与状态色对比度修正。
- 测试：未执行（前端 UI/样式调整）。
- 问题：暂无阻塞问题。

## v0.1.36-dev.37 (2026-02-06)
- 目标：修复前端编译错误并补齐明亮主题。
- 结果：
  - JSX 文本中的 `->` 改为字符串渲染，修复 Vite 解析报错。
  - 新增明亮主题配色与主题切换按钮，支持本地记忆。
  - 修复 CSS `@import` 顺序导致的 PostCSS 报错。
- 测试：未执行（前端 UI/样式修复）。
- 问题：暂无阻塞问题。

## v0.1.36-dev.36 (2026-02-06)
- 目标：依据 UX 说明书重构前端交互与信息架构。
- 结果：
  - 新增侧边栏导航与分区式页面（仪表盘/任务/冲突/设置/关于）。
  - 仪表盘补齐同步统计、活跃任务与实时日志卡片。
  - 任务管理 UI 覆盖同步模式、更新模式、进度与状态提示；保留任务创建向导。
  - 设置页补齐 OAuth、调度策略、手动上传与监听面板。
- 测试：未执行（纯前端 UI 调整）。
- 问题：暂无阻塞问题；如需明亮主题请告知偏好。

## v0.1.36-dev.35 (2026-02-06)
- 目标：落实默认同步调度策略；修复 Ctrl+C 后端口占用问题。
- 结果：
  - 新增同步调度器：本地变更队列每 2 秒上传一次，云端每日 01:00 下载一次（可配置）。
  - Watcher 仅入队，上传由调度器统一触发，避免频繁扫描。
  - 新增配置项 `upload_interval_seconds` 与 `download_daily_time`，并开放配置接口与文档说明。
  - dev 脚本在 Windows 下使用 taskkill 清理子进程，Ctrl+C 后端口可释放。
- 测试：
  - `python -m pytest tests/test_sync_scheduler.py -q`（apps/backend）。
- 问题：当前上传周期仅处理本地变更队列；如需强制全量扫描，请使用“立即同步”。

## v0.1.36-dev.34 (2026-02-06)
- 目标：修复本地改动在“原子保存/重命名”场景下未触发上传；输出当前同步逻辑说明文档。
- 结果：
  - Watcher 去抖/静默以 dest_path 为准，避免 moved 事件丢失真实变更。
  - 新增 Watcher 单测覆盖“dest_path 去抖/忽略”场景。
  - 新增 `docs/SYNC_LOGIC.md`，详细说明时间戳判断、接口调用与本地状态落库。
- 测试：
  - `python -m pytest tests/test_watcher.py -q`（apps/backend，2 passed）。
- 问题：当前仍无定时轮询，云端变更需手动触发同步任务。

## v0.1.36-dev.33 (2026-02-06)
- 目标：修复块级映射不一致导致 partial 失败；避免端口被占用时自动飘到 3667。
- 结果：
  - partial 更新遇到“块级映射不一致”时自动重建基线（bootstrap），再继续局部更新，避免直接失败。
  - 前端 dev server 开启 strictPort，端口固定为 3666，不再自动递增。
  - 新增单测覆盖映射不一致时的 bootstrap。
- 测试：
  - `python -m pytest tests/test_sync_runner_block_update.py -q`（apps/backend，2 passed）。
- 问题：无阻塞问题。

## v0.1.36-dev.32 (2026-02-06)
- 目标：修复“催办”标题下子内容未渲染问题。
- 结果：
  - 标题块支持渲染子块，确保标题下的待办/列表能落盘。
  - 新增单测覆盖“标题块子级 TODO”渲染。
- 测试：
  - `python -m pytest tests/test_transcoder.py -q`（apps/backend，19 passed）。
- 问题：无阻塞问题。

## v0.1.36-dev.31 (2026-02-06)
- 目标：修复“催办”任务与列表换行同步缺失问题，完善表格单元格内列表层级显示；前端端口固定为 3666。
- 结果：
  - Docx 解析增强：支持 line_break/hard_break 元素换行，补齐嵌套文本容器解析（如 todo.text）。
  - 表格单元格改用块渲染：保留列表换行与层级缩进，缩进使用 `&nbsp;` 保留显示。
  - 前端 dev/preview 端口改为 3666，同步更新 `docs/USAGE.md`。
  - 新增转码单测：line_break 列表续行、嵌套 todo 文本容器、表格单元格列表缩进。
- 测试：
  - `python -m pytest tests/test_transcoder.py -q`（apps/backend，18 passed）。
  - `python -m pytest tests/test_state_store.py -q`（apps/backend，2 passed）。
  - `python -m pytest apps/backend/tests/test_transcoder.py -q`（根目录仍会报 `ModuleNotFoundError: No module named 'src'`，需在 apps/backend 下运行）。
- 问题：若“催办”仍缺失请提供该段 Docx Block JSON 样例（含 block_type 与 todo/task 字段）。

## v0.1.36-dev.30 (2026-02-04)
- 目标：修复“本地较新但未上云”与云端同名文件导致映射漂移/重复处理问题。
- 结果：
  - partial 上行新增块状态自愈：当 `sync_block_states` 缺失时，自动基于云端根块 children 初始化占位块状态，避免直接报 `缺少块级状态，无法局部更新`。
  - 下载阶段新增同名去重策略：同一路径的多个云端节点仅保留一个候选；优先复用已持久化映射 token，其次选最新修改时间，避免 link 被重复文件反复覆盖。
  - 新建 Markdown 云端文档前先查同名 doc/docx，命中后复用而非再次创建，减少同名文档继续膨胀。
- 测试：
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py -q`（apps/backend，12 passed）。
  - `python -m pytest -q`（apps/backend，全量通过）。
- 问题：历史已经产生的同名云端文件不会自动删除；当前版本仅阻止继续漂移与重复创建。

## v0.1.36-dev.29 (2026-02-04)
- 目标：修复“本地改动未上云”与 partial 上行中频控导致的失败。
- 结果：
  - 双向下载新增“本地较新保护”：`bidirectional` 模式下若本地文件 mtime 晚于云端，则跳过下载，避免先被下行覆盖再导致上行跳过。
  - 飞书客户端新增频控重试：对 `code=99991400`（`request trigger frequency limit`）纳入指数退避重试，降低 Docx 块写入阶段的失败率。
  - 调整 README 功能说明：明确 partial 失败不再静默回退全量覆盖，并补充双向下载保护与频控重试说明。
  - 新增测试覆盖：`test_bidirectional_skips_download_when_local_file_is_newer`、`test_feishu_client.py`。
- 测试：
  - `python -m pytest tests/test_feishu_client.py tests/test_sync_runner.py tests/test_sync_runner_block_update.py tests/test_sync_runner_upload_new_doc.py tests/test_docx_service.py -q`（apps/backend，44 passed）。
- 问题：仍需你用真实云端文档回归验证“高频大文档 partial 上行”是否完全稳定；若仍有失败，请继续提供日志时间点，我会按 log_id 逐条跟进。

## v0.1.36-dev.28 (2026-02-04)
- 目标：解决“任务仍有失败 + 本地 Markdown 改动无法同步到云端”。
- 结果：
  - 从状态与日志定位根因：多个 `.md` 被历史错误映射为 `cloud_type=file`，导致上传阶段报 `云端类型不支持 Markdown 覆盖: file`。
  - 上传逻辑新增映射自愈：遇到 `.md -> file` 映射时，自动走导入任务创建 Docx，并重绑映射后继续上传，不再直接失败。
  - 导入创建 Docx 后不再重复执行全量覆盖，避免在创建后再次写入时触发“创建块失败”。
  - partial 更新失败（含缺少块级状态、局部插入失败）时自动回退全量覆盖，避免任务直接失败。
  - 新增单测覆盖迁移链路，验证旧映射可自动恢复为 `docx` 并成功覆盖内容。
- 测试：
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_sync_runner.py`（apps/backend，7 passed）。
  - `python -m pytest`（apps/backend，107 passed）。
- 问题：无阻塞问题。

## v0.1.36-dev.27 (2026-02-04)
- 目标：修复“本地监听触发上传时报参数缺失”的失败问题。
- 结果：
  - 通过运行日志与状态接口定位到错误：`SyncTaskRunner._upload_path() missing 2 required positional arguments: 'drive_service' and 'import_task_service'`。
  - 修复 `_handle_local_event` 的依赖注入与调用参数，补齐 `drive_service` / `import_task_service` 传递，并纳入生命周期关闭。
  - 新增回归测试，确保本地事件路径调用 `_upload_path` 时参数完整。
- 测试：
  - `python -m pytest tests/test_sync_runner.py`（apps/backend，5 passed）。
  - `python -m pytest`（apps/backend，106 passed）。
- 问题：无阻塞问题。

## v0.1.36-dev.26 (2026-02-04)
- 目标：实现“链接按同步状态本地化”——仅已同步且本地存在的目标改写为本地相对路径，未同步保持云端链接。
- 结果：
  - `SyncLinkService` 新增 `list_all()`，支持读取全量已同步映射。
  - 下载阶段在目录扫描映射外，额外合并历史映射；仅当本地文件真实存在时纳入改写，避免生成失效本地链接。
  - 增加 `_merge_synced_link_map` 逻辑和对应单测，确保不覆盖当前任务树内映射、不引入缺失文件路径。
- 测试：
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_link_service.py`（apps/backend，6 passed）。
  - `python -m pytest`（apps/backend，105 passed）。
- 问题：无阻塞问题。

## v0.1.36-dev.25 (2026-02-04)
- 目标：继续收敛 Markdown 上行与云端回写的一致性，重点修复列表续行、附件挂载和文本子块丢失问题。
- 结果：
  - `DocxService`：改进列表缩进归一化；续行占位符仅在“前缀续行”场景降级为文本；新增续行块重挂载逻辑；列表含附件/图片占位时改为挂到当前列表项 children，避免错误打平。
  - `DocxTranscoder`：列表多行文本按续行缩进渲染；文本块支持多行前缀渲染；文本块 children（含图片/附件）不再丢失。
  - 新增/更新单测覆盖上述边界场景。
- 测试：
  - `python -m pytest tests/test_docx_service.py tests/test_transcoder.py`（apps/backend，48 passed）。
  - 真实云端回归：`python scripts/compare_upload.py --source-local ... --upload-local ...`，最新对比目录：`data/example/compare/20260204_140805/`，差异已收敛至少量空白符与图片 token 差异。
- 问题：仍有极少数空白符差异（如个别段前后空行、双空格收敛），不影响主要结构与内容同步。

## v0.1.36-dev.24 (2026-02-04)
- 目标：把飞书开发文档“自动检查并下载”的动作固化为可执行规范。
- 结果：新增 `scripts/sync_feishu_docs.py`，可从飞书帮助中心页解析 zip 下载地址并同步到 `docs/feishu/`，同时生成 `_manifest.json` 记录检查结果；AGENTS 新增“开发前必须执行脚本”的要求；README 增补开发文档更新说明。
- 测试：`python scripts/sync_feishu_docs.py`（本次识别 3 个文档，均已存在，生成清单成功）。
- 问题：无。

## v0.1.36-dev.23 (2026-01-31)
- 目标：将飞书开发文档下载与更新入口写入协作规范。
- 结果：AGENTS 规范新增下载入口与本地文档更新流程（docs/feishu/）。
- 测试：未涉及代码逻辑变更。
- 问题：无。

## v0.1.36-dev.22 (2026-01-31)
- 目标：支持本地 Markdown 无映射时自动创建云端 Docx，便于上传对比与回归。
- 结果：新增导入任务服务（drive import_tasks）；上传侧自动上传 Markdown、创建 Docx 并落库映射；新增轮询定位新文档逻辑；补齐使用教程与功能列表。
- 测试：`python -m pytest tests/test_import_task_service.py tests/test_sync_runner_upload_new_doc.py`（在 apps/backend 目录执行）。
- 问题：仍需你用“日常记录 - 聂玮奇 副本 - 副本.md”实测云端对齐效果并反馈差异点。

## v0.1.36-dev.21 (2026-01-30)
- 目标：补齐“任务/提及/提醒”渲染缺失，避免云端内容遗漏。
- 结果：支持 mention_doc/mention_user/reminder 渲染；TODO 块支持完成状态；未知容器块（如 block_type=33）递归渲染子块；新增单测覆盖。
- 测试：`PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_transcoder.py`。
- 问题：仍需你确认本地任务/提醒展示是否符合预期文案。

## v0.1.36-dev.20 (2026-01-30)
- 目标：避免上传失败清空云端内容，并强化块级更新对表格/矩阵结构的兼容。
- 结果：创建子块仅在 index>=0 时传入 index；创建失败不会删除旧内容；块级替换先插入后删除降低数据丢失风险；下载后重建块级状态；表格 cells 支持矩阵展开；上传前基于 file_hash 判断未变更跳过。
- 测试：`PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_transcoder.py apps/backend/tests/test_sync_runner_block_update.py apps/backend/tests/test_markdown_blocks.py`。
- 问题：仍需真实文档验证 400 invalid param 是否完全消除。

## v0.1.36-dev.19 (2026-01-30)
- 目标：避免局部更新误匹配导致未改内容被覆盖。
- 结果：增加重复块签名与唯一锚点检测，低相似度时自动回退全量覆盖。
- 测试：`python -m pytest apps/backend/tests/test_docx_service.py`。
- 问题：请提供异常文档的 Markdown 与日志以继续精修策略。

## v0.1.36-dev.18 (2026-01-30)
- 目标：修复局部更新导致表格丢失与错位问题。
- 结果：局部更新使用 table.cells 作为子块；检测到表格或重复块签名时自动回退全量覆盖，避免误替换。
- 测试：`python -m pytest apps/backend/tests/test_docx_service.py`。
- 问题：如仍出现误同步，请提供对应 Markdown 与日志。

## v0.1.36-dev.17 (2026-01-30)
- 目标：修复上传表格丢失与时间戳判定问题，并优化同步日志展示。
- 结果：Markdown 转换缺失表格属性时按源表格补齐 row/column；支持 ISO 时间戳解析；同步事件带时间戳并前端按时间线展示；任务同步模式可在列表中更新。
- 测试：`python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_sync_runner.py`。
- 问题：如仍有表格缺失，请提供对应 Markdown 与日志。

## v0.1.36-dev.16 (2026-01-30)
- 目标：修复 Windows 下 dev 启动脚本的 spawn EINVAL。
- 结果：Windows 使用 shell 字符串启动并补充异常捕获日志；非 Windows 保持 spawn args 模式。
- 测试：未执行（启动脚本变更）。
- 问题：无。

## v0.1.36-dev.15 (2026-01-30)
- 目标：修复启动时 SQLite 迁移报错，并清理 dev 启动警告。
- 结果：ALTER TABLE 默认值改为字面量，避免参数占位导致语法错误；dev 启动脚本改为非 shell 模式调用，避免弃用警告。
- 测试：`python -m pytest apps/backend/tests/test_db_session.py`。
- 问题：无。

## v0.1.36-dev.14 (2026-01-30)
- 目标：确保开发控制台输出落盘，便于定位启动问题。
- 结果：新增 `scripts/dev.js`，`npm run dev` 输出同步写入 `data/logs/dev-console.log`；文档启动指令改为 `python -m uvicorn`。
- 测试：未执行（脚本与文档变更）。
- 问题：无。

## v0.1.36-dev.13 (2026-01-30)
- 目标：在界面中开放更新模式设置，并保存到任务配置。
- 结果：后端任务新增 update_mode 字段与迁移；前端新增“更新模式”选择与更新按钮；手动上传支持 update_mode。
- 测试：未执行（涉及前端交互与 DB 迁移）。
- 问题：如已有旧数据库，请先重启后端触发迁移。

## v0.1.36-dev.12 (2026-01-30)
- 目标：修复上传列表/表格/图片转换异常。
- 结果：Markdown 不再分段转换，改为图片占位单次转换以保留列表结构；表格创建时剥离 cells 并用 cells 作为子块创建；图片用占位文本替换为 image block 后再上传素材。
- 测试：`PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py`。
- 问题：若仍出现列表变代码或表格缺失，请提供最新日志与对应 Markdown 片段。

## v0.1.36-dev.11 (2026-01-30)
- 目标：修复上行图片/表格 block 的 400 invalid param。
- 结果：图片块改为先创建空块再上传素材；表格块移除 cells 引用并用 cells 作为子块创建；同步默认 update_mode=auto。
- 测试：`PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py`。
- 问题：若仍有 invalid param，将继续根据无效块日志调整 payload。

## v0.1.36-dev.10 (2026-01-30)
- 目标：针对 Markdown 上行做块级差异更新，减少全量覆盖。
- 结果：基于顶层 block signature 做 diff；仅对变更段落执行删除/插入；新增 update_mode 参数并默认对同步任务启用 partial。
- 测试：`PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py`。
- 问题：若仍有 400 invalid param，将在日志中定位具体 block payload 并继续修正。

## v0.1.36-dev.9 (2026-01-30)
- 目标：在 400 invalid param 时自动定位无效块并继续上传。
- 结果：创建子块失败时拆分重试，单块失败则记录 payload 并跳过；日志包含 block_type/keys 便于定位。
- 测试：未执行（逻辑变更，需要联调验证）。
- 问题：待确认具体无效块类型并按飞书规则修正。

## v0.1.36-dev.8 (2026-01-29)
- 目标：补齐上行日志并定位 400 invalid param。
- 结果：补充上传阶段逐文件错误日志；Docx 转换结果统计与根块规整；创建子块前输出块类型摘要；图片上传记录 token。
- 测试：`PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py`。
- 问题：若仍出现 400，请提供 log_id（日志已打印），便于对照飞书排障指引。

## v0.1.36-dev.7 (2026-01-29)
- 目标：避免云端文档被清空并补充同步日志。
- 结果：Docx 覆盖流程改为先创建再删除旧内容；上传去重与同文档互斥锁；同步阶段与失败信息写入日志；更新单测。
- 测试：`PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py`。
- 问题：全量 pytest 需配置 `PYTHONPATH=apps/backend`，否则出现 `ModuleNotFoundError: src`。

## v0.1.36-dev.6 (2026-01-29)
- 目标：自动记录运行日志与错误信息，便于排查同步问题。
- 结果：引入 Loguru 初始化；HTTP 请求日志与异常写入 `data/logs/larksync.log`；新增单测与使用文档说明。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.36-dev.5 (2026-01-29)
- 目标：修复上传时缺图导致 400 与图片路径不一致问题。
- 结果：下载时图片保存到文档同目录 `assets/`；上传时 base_path 使用文档所在目录；缺图仅插入占位文本不再生成无效 image block。
- 测试：`python -m pytest`（apps/backend）。
- 问题：如仍失败，请提供 docx API 400 的响应体。

## v0.1.36-dev.4 (2026-01-29)
- 目标：上传时本地缺图不再导致失败。
- 结果：缺图时自动回退使用文件名推断 token；无法推断则插入缺图占位文本；新增单测。
- 测试：`python -m pytest`（apps/backend）。
- 问题：若推断 token 无效，请提供图片 token 与下载响应样例。

## v0.1.36-dev.3 (2026-01-29)
- 目标：图片下载失败时不中断并增加兜底下载策略。
- 结果：图片下载失败后改用文件下载接口兜底；新增对应单测。
- 测试：`python -m pytest`（apps/backend）。
- 问题：若仍失败，请提供 image block JSON 与下载错误响应。

## v0.1.36-dev.2 (2026-01-29)
- 目标：避免本地运行数据误入版本库。
- 结果：`data/` 目录统一忽略。
- 测试：未执行（忽略规则变更）。
- 问题：暂无阻塞问题。

## v0.1.36-dev.1 (2026-01-29)
- 目标：修复本地上传时 Markdown 转换接口 404。
- 结果：Docx markdown convert 接口改为 v1 路径；更新单测。
- 测试：`python -m pytest`（apps/backend）。
- 问题：附件块字段与云端更新接口样例仍待补齐。

## v0.1.35-dev.1 (2026-01-29)
- 目标：修复双向上传未触发与附件下载失败问题。
- 结果：upload_only 预填充云端映射避免缺失；上传跳过逻辑在 upload_only 下关闭；附件下载增加 media 兜底并容错；新增附件块测试。
- 测试：`python -m pytest`（apps/backend）。
- 问题：Markdown 新建 Docx 与云端文件覆盖更新仍需导入/更新接口样例。

## v0.1.34-dev.1 (2026-01-29)
- 目标：补齐双向同步上传链路，修复表格内容缺失，并支持文档链接与附件本地化。
- 结果：同步任务支持 upload_only/bidirectional 执行；下载时建立云端 token→本地路径映射，Docx 转码支持链接改写与附件下载；表格单元格内容递归提取；新增 SyncLink 表与相关测试。
- 测试：`python -m pytest`（apps/backend）。
- 问题：新建 Markdown 文档需提供飞书导入接口样例；非 MD 文件的“覆盖更新”接口待补齐。

## v0.1.33-dev.1 (2026-01-28)
- 目标：补齐 Docx 转 Markdown 中列表/引用/代码块/待办等常见块的解析与层级遍历。
- 结果：转码器新增块类型映射与递归渲染；列表分组输出、引用/Callout 容器处理、代码块/分割线支持；新增单测覆盖。
- 测试：`python -m pytest`（apps/backend）。
- 问题：如仍有内容缺失，请提供 docx blocks 响应样例用于补齐字段解析。

## v0.1.32-dev.1 (2026-01-28)
- 目标：修复下载任务对快捷方式导致的 404，并展示失败细节。
- 结果：同步任务解析 shortcut 目标 token/type；失败事件附带 token/type；前端展示失败原因；补充文档与测试。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.31-dev.1 (2026-01-28)
- 目标：补偿 Docx 未识别文本块导致的空内容，并区分未支持文件类型。
- 结果：Docx 转码增加未知块文本回退；同步任务将非 docx/file 类型标记为“跳过”；任务状态展示跳过数；补充文档说明与测试。
- 测试：`python -m pytest`（apps/backend）。
- 问题：如仍出现空内容，请提供 docx blocks 响应样例。

## v0.1.30-dev.1 (2026-01-28)
- 目标：让下载模式任务具备真实执行与状态反馈，并支持删除。
- 结果：新增任务下载执行器与状态接口；任务创建/启用时自动触发下载；前端显示状态、进度与最近文件，并提供“立即同步/删除”操作；同步文档与 README。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.29-dev.1 (2026-01-28)
- 目标：修复权限提示误导，确保默认 scope 与文档一致。
- 结果：默认 scopes 更新为 `drive:drive.metadata:readonly`；补充 OAuth 指南与使用文档中的权限与排错说明；同步修正需求与调研文档中的权限名称。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.28-dev.1 (2026-01-28)
- 目标：优化同步任务交互，支持云端与本地目录选择，并切换为明亮主题。
- 结果：新增云端目录选择器与本地系统文件夹选择器；界面整体明亮化；补充系统选择接口与测试；更新使用文档与 README。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.27-dev.1 (2026-01-28)
- 目标：完善 OAuth 回调体验，授权后自动返回前端页面。
- 结果：/auth/login 支持 redirect 参数并在 callback 成功后重定向；前端登录链接带 redirect；状态存储新增重定向支持；使用文档更新。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.26-dev.1 (2026-01-28)
- 目标：增强 OAuth Token 错误可读性，避免 500 且便于定位。
- 结果：Token 请求失败时输出 HTTP 响应详情；补充网络错误与非 JSON 响应处理；新增单测覆盖。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.25-dev.1 (2026-01-28)
- 目标：修复飞书 OAuth Token 请求缺失 app_id/app_secret 的问题。
- 结果：授权地址参数改为 app_id；Token 交换与刷新改为 app_id/app_secret；新增凭证缺失单测。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.24-dev.1 (2026-01-28)
- 目标：优化 OAuth 配置向导说明，强调官方文档对齐。
- 结果：更新 `docs/OAUTH_GUIDE.md` 与向导提示文本。
- 测试：未执行（文档变更）。
- 问题：暂无阻塞问题。

## v0.1.23-dev.1 (2026-01-28)
- 目标：修复 Token 接口报空 grant_type。
- 结果：Token 请求改为 JSON body 发送；版本与变更记录更新。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.22-dev.1 (2026-01-28)
- 目标：完善 OAuth 配置向导说明并避免本地密钥误提交。
- 结果：优化前端向导提示；更新 `docs/OAUTH_GUIDE.md` 详细步骤；`.gitignore` 忽略 `data/config.json`。
- 测试：`npm run build`（apps/frontend）。
- 问题：暂无阻塞问题。

## v0.1.21-dev.1 (2026-01-28)
- 目标：修复 Token 响应缺少 access_token 的解析问题。
- 结果：AuthService 兼容 `code/msg/data` 包装格式；新增单测覆盖。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.20-dev.1 (2026-01-28)
- 目标：补充更详细的 OAuth 配置指南，提升可理解度。
- 结果：新增 `docs/OAUTH_GUIDE.md` 详细步骤；更新向导说明与使用文档。
- 测试：`npm run build`（apps/frontend）。
- 问题：暂无阻塞问题。

## v0.1.19-dev.1 (2026-01-28)
- 目标：提供网页配置 OAuth 参数并补充获取指南。
- 结果：新增 /config API；前端 OAuth 配置向导；补充配置获取步骤说明；Vite 代理新增 /config 与 /sync；新增配置 API 单测。
- 测试：`python -m pytest`（apps/backend）；`npm run build`（apps/frontend）。
- 问题：暂无阻塞问题。

## v0.1.18-dev.1 (2026-01-28)
- 目标：修复登录 500 与数据库未初始化导致的接口异常。
- 结果：/auth/login 捕获 AuthError 返回 400；启动时自动初始化 DB；新增登录 API 测试。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.17-dev.1 (2026-01-28)
- 目标：修复 Windows 下 `npm run dev` 找不到 uvicorn 的问题。
- 结果：根目录 dev 脚本改为 `python -m uvicorn`，避免 PATH 依赖。
- 测试：未执行（脚本变更，请按文档自行验证）。
- 问题：暂无阻塞问题。

## v0.1.16-dev.1 (2026-01-28)
- 目标：补充手动上传入口，便于验证图片上传与 Docx 覆盖链路。
- 结果：前端新增“手动上传 Markdown”表单，支持选择任务或手填 base_path；修正 Vite /api 代理正则；文档同步更新。
- 测试：`npm run build`（apps/frontend）。
- 问题：手动上传目前仅前端入口，后续可与任务触发器合并。

## v0.1.15-dev.1 (2026-01-28)
- 目标：同步任务配置向导、冲突持久化、base_path 接入。
- 结果：新增 SyncTask/ConflictRecord 数据表与服务；/sync/tasks 与 /sync/markdown/replace 接口；前端同步任务配置 UI；冲突记录持久化到 SQLite。
- 测试：`python -m pytest`（apps/backend）；`npm audit --omit=dev`（apps/frontend）。
- 问题：同步任务尚未驱动自动上传/下载，仅用于配置与手动上传触发。

## v0.1.14-dev.1 (2026-01-28)
- 目标：补齐 Markdown 图片上传链路并落地使用教程文档。
- 结果：新增 MediaUploader 与 DocxService 图片解析/上传；本地图片自动转 Docx 图片块；新增 `docs/USAGE.md` 教程。
- 测试：`python -m pytest`（apps/backend）；`npm audit --omit=dev`（apps/frontend）。
- 问题：图片上传依赖 `base_path` 指定 Markdown 所在目录，目前 UI 尚未暴露该参数。

## v0.1.13-dev.1 (2026-01-27)
- 目标：完成 Task 4.2 Docker 生产构建与部署配置。
- 结果：新增多阶段 Dockerfile、Nginx 反向代理配置与 docker-compose；前端生产环境自动使用 /api 前缀。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。生产镜像如需自定义端口或域名，请告知。

## v0.1.12-dev.1 (2026-01-27)
- 目标：完成 Task 4.1 冲突处理 UI 与后端冲突标记基础。
- 结果：新增 ConflictService 与 /conflicts 接口；前端冲突中心展示与“使用本地/云端”操作；补充单测。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。冲突数据目前为内存存储，后续可接入数据库持久化。

## v0.1.11-dev.1 (2026-01-27)
- 目标：完成 Task 3.3 通用文件上传（非 MD）与上传后状态记录。
- 结果：新增 FileUploader（upload_all + 分片上传）与 file_hash 计算；上传完成写入 SyncMapping。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。若需接入具体同步根目录与云端目录映射，请提供设计/字段。

## v0.1.10-dev.1 (2026-01-27)
- 目标：完成 Task 3.2 Markdown → Docx 全量覆盖上传与 429 指数退避。
- 结果：新增 DocxService（convert + blocks list/create/batch_delete 全量替换）；FeishuClient 支持 429/1061045 指数退避；新增 docx service 单测。
- 测试：`python -m pytest`（apps/backend）；`npm audit --omit=dev`（apps/frontend）。
- 问题：Markdown 内本地图片路径尚未做上传转 token；如需图片上行请提供期望的上传接口样例。

## v0.1.9-dev.1 (2026-01-27)
- 目标：完成 Task 3.1 本地文件系统监听、去抖与 WebSocket 推送。
- 结果：新增 WatcherService/WatcherManager 与 EventHub；提供 `/watcher/*` 与 `/ws/events`；前端监听控制与事件面板。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。若需接入具体同步根目录，请提供路径规划。

## v0.1.8-dev.1 (2026-01-27)
- 目标：完成 Task 2.5 非在线文档下载与本地落盘。
- 结果：新增 FileDownloader，支持通过 Drive 下载接口写入本地并设置 mtime；补充单测。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.7-dev.1 (2026-01-27)
- 目标：完成 Task 2.4 本地写入与 mtime 同步。
- 结果：新增 FileWriter 支持写入 Markdown/二进制并强制设置 mtime；补充单测。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。

## v0.1.6-dev.1 (2026-01-27)
- 目标：完成 Task 2.3 转码引擎基础能力（标题/加粗/表格/图片）。
- 结果：新增 DocxTranscoder/DocxParser，支持 H1/H2/Bold/Table/Image 转 Markdown；图片下载器与 assets 落盘；新增转码单测。
- 测试：`python -m pytest`（apps/backend）。
- 问题：暂无阻塞问题。若真实 Block JSON 字段与文档结构不一致，请提供样例。

## v0.1.5-dev.1 (2026-01-27)
- 目标：完成 Task 2.2 递归目录爬虫与前端目录树展示。
- 结果：新增 DriveService 与 `/drive/tree`；支持分页与递归；前端树形展示与刷新按钮；补充 Vite 代理。
- 测试：`python -m pytest`（apps/backend）；`npm audit`（apps/frontend）。
- 问题：暂无阻塞问题。若 /drive/v1/files 响应字段与文档不一致，请提供 JSON 样例。

## v0.1.4-dev.1 (2026-01-27)
- 目标：完成 OAuth2 登录链路的骨架、令牌安全存储与前端连接页面。
- 结果：新增 /auth/login、/auth/callback、/auth/status、/auth/logout；引入 keyring 安全存储；前端登录页与 Vite 代理配置完成。
- 测试：`python -m pytest`（apps/backend）；`npm audit`（apps/frontend）。
- 问题：暂无阻塞问题。若 Feishu token 响应字段不同，请提供 JSON 样例以调整解析。

## v0.1.3-dev.1 (2026-01-27)
- 目标：实现发布脚本与版本归档机制。
- 结果：新增 `scripts/release.py`，支持自动更新版本与 CHANGELOG 并执行 Git 提交与推送；新增开发日志规范。
- 测试：`python -m pytest`（apps/backend）。
- 问题：无阻塞问题。

## v0.1.2-dev.1 (2026-01-27)
- 目标：修复前端依赖漏洞，统一版本规范与 SyncMapping 字段。
- 结果：升级 Vite 至 7.3.1，esbuild 漏洞清零；SSOT Schema Reference 与 Task 1.2 字段统一为 file_hash 主键；版本与 CHANGELOG 规范落地。
- 测试：`python -m pytest`（apps/backend）；`npm audit`（apps/frontend）。
- 问题：无阻塞问题。
