# DEVELOPMENT LOG

## v0.5.44-disable-macos-default-release (2026-02-19)
- 目标：
  - 处理 macOS 发布流程中的 `upload-artifact` 403 问题带来的发布中断风险。
  - 按当前策略默认不发布 macOS，仅在需要时手动开启。
- 变更：
  - `.github/workflows/release-build.yml`
    - `workflow_dispatch` 新增布尔输入 `build_macos`（默认 `false`）。
    - `build-macos` job 改为仅在“手动触发 + 稳定版 tag + `build_macos=true`”时执行。
    - macOS 的 `Upload workflow artifact` 步骤改为 `continue-on-error: true`，避免 artifact 服务 403 直接中断整条 job。
  - `docs/USAGE.md`
    - 发布说明更新为：tag 自动发布默认仅 Windows；macOS 需要手动开启。

## v0.5.44-release-notes-automation (2026-02-19)
- 目标：
  - 修复发布时 Release 页面缺少版本改动说明的问题。
  - 支持“一个稳定版覆盖多个中间 dev 版本”时，自动汇总所有变更条目。
- 变更：
  - 新增 `scripts/release_notes.py`
    - 从 `CHANGELOG.md` 解析条目，定位当前稳定版与上一稳定版边界。
    - 自动汇总边界之间的全部条目（含多个中间版本），按版本分组输出 Markdown。
  - `apps/backend/tests/test_release_notes.py`
    - 新增解析、区间提取、分组渲染与无目标版本回退测试。
  - `.github/workflows/release-build.yml`
    - Windows/macOS 发布任务新增“生成 release-notes.md”步骤。
    - `softprops/action-gh-release` 增加 `body_path: release-notes.md`，上传安装包时同步写入版本说明。
  - `docs/USAGE.md`
    - 发布章节补充“Release 文案自动由 CHANGELOG 生成”的说明。

## v0.5.44-add-license-cc-by-nc-sa (2026-02-18)
- 目标：
  - 为仓库补齐标准许可证文件，明确对外许可条款。
- 变更：
  - 新增 `LICENSE`，内容为 CC BY-NC-SA 4.0 官方 legalcode 正文（来源：<https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode>）。
  - `README.md` 新增 License 区块，链接本地 `LICENSE` 与官方 legalcode 页面。

## v0.5.44-readme-balance-and-usage-release-guide (2026-02-18)
- 目标：
  - 修正 README 过度精简的问题，回到“有介绍但不冗长”的开源项目风格。
  - 保留三份核心文档入口，并在 README 做简要导读。
  - 恢复 `docs/USAGE.md` 的发布教学，便于维护者日常使用。
- 变更：
  - `README.md`
    - 补充“项目简介 / 适用场景 / 功能亮点”。
    - 保留 Logo 与双路径快速开始（本地开发、Release 下载）。
    - 移除当前不合适的“常见问题”段落。
  - `docs/USAGE.md`
    - 第 10 节调整为“本地打包、发布与安装包下载”。
    - 恢复维护者发布教学（`npm run release:publish`）与 GitHub Release 构建说明。
    - 保留使用者下载安装包路径。

## v0.5.44-public-readme-and-repo-hygiene (2026-02-18)
- 目标：
  - 面向公开仓库精简对外文档，避免暴露不必要的内部流程。
  - README 快速开始仅保留“本地开发”和“Release 下载安装包”两条主路径。
  - 启动器脚本文件改为本地保留、不再纳入 Git 跟踪。
- 变更：
  - `README.md`
    - 精简公开内容，移除 Git 发布流程与内部实现细节。
    - 新增产品 Logo 展示。
    - 新增关键文档链接：`docs/OAUTH_GUIDE.md`、`docs/USAGE.md`、`docs/SYNC_LOGIC.md`。
  - `docs/USAGE.md`
    - 第 10 节改为“本地打包与安装包下载”，移除 Git 发布操作说明。
  - `.gitignore`
    - 新增 `LarkSync.bat`、`LarkSync.pyw`、`LarkSync.command` 忽略规则。
  - Git 跟踪清理：
    - `git rm --cached LarkSync.bat LarkSync.pyw LarkSync.command`（仅停止跟踪，本地文件保留）。

## v0.5.44-docs-refresh-before-release (2026-02-18)
- 目标：
  - 在发布前重构 `README.md`，对齐优秀 GitHub 项目首页的结构与可读性。
  - 将项目定位补齐为“NAS + 飞书 + AI 文档工作流”三位一体场景。
  - 同步校正文档版本信息，避免 `USAGE` 与当前代码状态不一致。
- 变更：
  - `README.md`
    - 重构为“当前状态 / 项目价值 / 核心能力 / 快速开始 / 测试方式 / 发布方式 / 自动更新 / FAQ”结构。
    - 补充任务级 MD 模式、任务归属隔离、删除策略、自动更新和 GitHub Release 流程说明。
  - `docs/USAGE.md`
    - 版本信息统一更新到 `v0.5.44`。
    - 一行发布示例与自动更新前置条件（公开 Release）更新为当前真实行为。
  - `CHANGELOG.md`
    - 追加文档重构记录。

## v0.5.43-md-mode-update-release (2026-02-18)
- 目标：
  - 新增“一行稳定版发布”能力，自动获取下一稳定版号并发布。
  - 自动更新补齐为后台自动检查并自动下载更新包（不自动安装）。
  - 将 MD 上行策略从全局开关升级为任务级模式，默认改为增强模式。
  - 修复本地 Markdown 上云时图片路径解析不稳定（`file://`、URL 编码、query/hash）。
- 变更：
  - 发布流程：
    - `scripts/release.py`
      - 新增 `--publish` 模式：自动计算稳定版号、更新版本文件、更新 CHANGELOG、提交、打标签并推送。
      - 新增版本计算逻辑：读取 git tags 与当前版本，自动选择下一稳定版。
    - `package.json`
      - 新增 `release:publish` 与 `release:dev` 脚本，支持一行执行。
- 自动更新：
  - `apps/backend/src/services/update_scheduler.py`
      - 定时检查后若发现新稳定版，自动下载更新包（去重同版本重复下载）。
    - `apps/backend/src/api/system.py`
      - 修复 `/system/update/status|check|download` 的响应模型校验异常（避免前端“检查更新”报错）。
    - `apps/backend/src/api/auth.py`
      - OAuth 回调成功后异步触发一次更新检查，满足“每次登录检测更新”。
    - `apps/backend/src/services/update_service.py`
      - 增加 `auto_update_enabled()` 供调度器判断。
  - 任务级 MD 上传模式：
    - `apps/backend/src/db/models.py`、`apps/backend/src/db/session.py`
      - `sync_tasks` 新增 `md_sync_mode` 字段，并在启动迁移中自动补齐。
    - `apps/backend/src/services/sync_task_service.py`
      - 新建/更新/返回任务支持 `md_sync_mode`（`enhanced/download_only/doc_only`）。
      - 兼容旧配置回退：缺失模式时按历史 `upload_md_to_cloud` 推断。
    - `apps/backend/src/api/sync_tasks.py`
      - 创建/更新任务 API 与响应增加 `md_sync_mode`。
    - `apps/backend/src/services/sync_runner.py`
      - MD 上传与镜像行为改为按任务模式执行：
        - `enhanced`：上传云文档 + 维护 `_LarkSync_MD_Mirror`
        - `download_only`：跳过本地 MD 上行
        - `doc_only`：仅上传云文档，不保留镜像副本
    - `apps/frontend/src/components/NewTaskModal.tsx`、`apps/frontend/src/pages/TasksPage.tsx`、`apps/frontend/src/hooks/useTasks.ts`、`apps/frontend/src/types/index.ts`
      - 新建任务与任务管理新增 MD 上传模式配置与保存入口。
    - `apps/frontend/src/pages/SettingsPage.tsx`
      - 移除旧的全局 MD 上传开关展示，避免与任务级策略冲突。
  - 图片上传修复：
    - `apps/backend/src/services/docx_service.py`
      - 图片路径解析增强：支持 `file://`、URL 编码、query/hash 清理、Windows 路径前缀兼容。
  - 文档：
    - 更新 `README.md`、`docs/USAGE.md`、`CHANGELOG.md`。
- 测试：
  - 新增：
    - `apps/backend/tests/test_update_scheduler.py`
    - `apps/backend/tests/test_sync_runner_upload_new_doc.py`（MD 模式相关用例）
    - `apps/backend/tests/test_docx_service.py`（图片路径解析）
    - `apps/backend/tests/test_sync_task_service.py`（任务级 MD 模式）

## v0.5.43-task-mapping-and-md-cleanup (2026-02-17)
- 目标：
  - 修复本地 Markdown 上云新建 Docx 后在原目录残留源 `.md` 的问题（避免云端出现 3 份文件）。
  - 增加任务映射约束，确保同设备同账号下“本地目录 ↔ 云端目录”一对一并规避本地父子目录冲突。
  - 优化同步任务页面布局，提升状态和策略信息可读性。
- 变更：
  - 后端同步：
    - `apps/backend/src/services/sync_runner.py`
      - Markdown 新建 Docx 导入链路新增导入源文件清理：导入成功/失败后都会尝试删除原目录临时 `.md` 上传文件。
  - 后端任务模型：
    - `apps/backend/src/services/sync_task_service.py`
      - 新增 `SyncTaskValidationError`。
      - 新建/更新任务时增加映射冲突校验：本地目录唯一、云端目录唯一、本地目录禁止父子并行。
    - `apps/backend/src/api/sync_tasks.py`
      - 创建/更新任务捕获映射校验错误并返回 `409`。
  - 前端任务页：
    - `apps/frontend/src/pages/TasksPage.tsx`
      - 顶部新增任务状态概览卡片（总数/同步中/失败/停用）。
      - 卡片视觉层次优化（信息区、路径区、策略区更清晰）。
  - 测试：
    - `apps/backend/tests/test_sync_runner_upload_new_doc.py`
      - 新增“导入失败仍清理源 md”回归用例。
      - 补充“导入成功清理源 md”断言。
    - `apps/backend/tests/test_sync_task_service.py`
      - 新增本地目录/云端目录唯一性与本地父子目录冲突测试。
    - `apps/backend/tests/test_tray_status.py`
      - 新增 API 层重复映射返回 `409` 的测试。
- 测试结果：
  - `$env:PYTHONPATH='apps/backend'; .\\.venv\\Scripts\\python -m pytest apps/backend/tests/test_sync_runner_upload_new_doc.py apps/backend/tests/test_sync_task_service.py apps/backend/tests/test_tray_status.py -q` 通过（25 passed）。
  - `npm run build --prefix apps/frontend` 通过。

## v0.5.43-ui-delete-polish (2026-02-17)
- 目标：
  - 调整“更多设置”布局，移除删除策略提示卡片。
  - 在任务管理中补齐删除策略说明与宽限时间单位，降低新用户理解成本。
  - 修复删除联动对云端 MD 镜像副本不生效问题。
  - 将默认本地上传间隔从 2 秒调整为 60 秒。
- 变更：
  - 前端 UI：
    - `apps/frontend/src/pages/SettingsPage.tsx`
      - “更多设置”移除删除策略说明卡，改为纯设备显示名配置块。
      - 上传间隔默认值由 `2` 调整为 `60`。
    - `apps/frontend/src/pages/TasksPage.tsx`
      - 删除策略卡片新增策略行为说明文案（off/safe/strict）。
      - 宽限输入补充“分钟”单位展示，并在 strict 模式下明确宽限固定为 0。
    - `apps/frontend/src/components/Sidebar.tsx`
      - 上传间隔展示默认值由 `2` 改为 `60`。
  - 后端同步：
    - `apps/backend/src/services/sync_runner.py`
      - 删除处理新增 `_cleanup_md_mirror_copy()`：本地删云端/云端删本地流程都会同步清理 `_LarkSync_MD_Mirror` 下对应 MD 副本。
      - 新增“不创建目录”的镜像目录定位方法，避免删除流程反向创建镜像目录。
      - `_find_subfolder()` 改为大小写不敏感匹配；`_should_ignore_path()` 增加本地镜像目录过滤。
  - 默认配置：
    - `apps/backend/src/core/config.py` 与 `apps/backend/src/api/config.py` 的 `upload_interval_value` 默认值由 `2.0` 改为 `60.0`。
  - 文档：
    - `docs/USAGE.md` 更新默认上行间隔样例与说明为 60 秒。
- 测试：
  - `$env:PYTHONPATH='apps/backend'; .\\.venv\\Scripts\\python -m pytest apps/backend/tests/test_sync_runner.py apps/backend/tests/test_config_api.py -q` 通过。
  - `npm run build --prefix apps/frontend` 通过。

## v0.5.43-sync-delete-retry (2026-02-17)
- 目标：
  - 修复“本地删除历史失败后不再重试，导致云端长期未删除”的问题。
  - 验证“删除策略任务级”在现网数据库中的实际生效状态。
- 根因：
  - 删除墓碑失败后状态会写成 `failed`，但执行器仅拉取 `pending`，历史失败项不会再次进入执行链路。
  - 生产日志中的旧报错 `field validation failed token=...` 来自修复前进程；修复后错误信息已包含 `type=...`。
- 变更：
  - `apps/backend/src/services/sync_tombstone_service.py`
    - `list_pending` 新增 `include_failed`（默认 `true`），将 `failed` 纳入可执行队列。
    - `mark_status` 新增 `expire_at` 参数，用于失败退避重试窗口。
  - `apps/backend/src/services/sync_runner.py`
    - `_process_pending_deletes` 在删除失败时写入 `expire_at = now + 300s`，5 分钟后自动重试，避免日志刷屏。
    - 新增“云端已删除”幂等判定：`file has been delete` 等错误按成功处理，直接清理映射并结束墓碑。
  - `apps/backend/src/services/sync_task_service.py`
    - 任务输出统一返回“已解析的有效删除策略”：旧任务 `delete_policy/delete_grace_minutes` 为 `NULL` 时，自动回退到全局默认，避免“页面显示与实际执行不一致”。
  - 测试：
    - `apps/backend/tests/test_sync_tombstone_service.py` 新增 `failed` 回退到可重试队列的测试。
    - `apps/backend/tests/test_sync_runner.py` 更新 FakeTombstone 行为，并校验失败后墓碑保留且带退避时间。
    - `apps/backend/tests/test_sync_task_service.py` 新增 legacy `NULL` 删除策略回退测试。
- 现场验证：
  - 运行 `init_db()` 后，`sync_tasks` 已存在 `delete_policy/delete_grace_minutes` 列（任务级设置迁移已就位）。
  - 对当前数据库执行一次删除墓碑处理：
    - 处理前：`failed=8, executed=2`
    - 处理后：`cancelled=6, failed=2, executed=2`
    - 说明：历史失败项已重新进入处理；其中 2 条返回 `file has been delete`（云端已不存在），属于可预期幂等场景。
  - 将剩余 `failed` 墓碑调整为到期后再次执行：
    - 处理前：`cancelled=6, failed=2, executed=2`
    - 处理后：`cancelled=6, executed=4`
    - 说明：两条“云端已删除”墓碑已按幂等成功清理完成。
- 测试结果：
  - `$env:PYTHONPATH='apps/backend'; .\\.venv\\Scripts\\python -m pytest apps/backend/tests/test_sync_task_service.py apps/backend/tests/test_sync_tombstone_service.py apps/backend/tests/test_sync_runner.py -k \"legacy_null_delete_settings or pending_deletes or tombstone\" -q` 通过（8 passed）。

## v0.5.42-sync-delete-hotfix (2026-02-17)
- 目标：
  - 修复“本地删除未联动云端删除”的生产问题。
  - 将删除联动策略从全局设置下沉为任务级配置，避免不同任务策略互相干扰。
- 日志定位：
  - `data/logs/sync-events.jsonl` 与 `data/logs/larksync.log` 中连续出现 `delete_failed`：
    - `删除文件失败: field validation failed token=...`
  - 结论：删除链路已触发并进入 `_process_pending_deletes`，失败点在 Drive 删除接口参数不完整。
- 变更：
  - 云端删除接口修复：
    - `apps/backend/src/services/drive_service.py`
      - `delete_file(file_token, file_type)` 新增 `type` 查询参数透传。
    - `apps/backend/src/services/sync_runner.py`
      - 删除墓碑执行时改为传入 `cloud_type`，避免 docx/file 等类型删除时校验失败。
      - 同步镜像目录旧文件清理也改为传入类型。
  - 删除策略任务级化：
    - 后端模型与迁移：
      - `apps/backend/src/db/models.py`：`sync_tasks` 新增 `delete_policy`、`delete_grace_minutes`。
      - `apps/backend/src/db/session.py`：`init_db` 补齐列迁移（含损坏重建分支）。
    - 后端任务服务/API：
      - `apps/backend/src/services/sync_task_service.py`：任务创建/更新/返回支持任务级删除策略；新任务默认继承全局默认值。
      - `apps/backend/src/api/sync_tasks.py`：任务创建/更新/响应模型新增删除策略字段。
    - 同步执行策略：
      - `apps/backend/src/services/sync_runner.py`：删除策略解析改为“任务级优先，配置级兜底”。
  - 前端交互：
    - `apps/frontend/src/components/NewTaskModal.tsx`：新建任务支持设置删除策略与宽限分钟。
    - `apps/frontend/src/pages/TasksPage.tsx`：任务管理新增删除策略卡片（单任务保存）。
    - `apps/frontend/src/pages/SettingsPage.tsx`：移除全局删除策略编辑项，改为任务级引导说明。
    - `apps/frontend/src/hooks/useTasks.ts`、`apps/frontend/src/types/index.ts`：补充任务级字段与更新接口。
  - 文档：
    - `README.md`、`docs/USAGE.md` 更新删除策略为“任务级”说明。
- 测试结果：
  - `$env:PYTHONPATH='apps/backend'; python -m pytest apps/backend/tests/test_drive_service.py apps/backend/tests/test_sync_task_service.py apps/backend/tests/test_sync_runner.py -q` 通过。
  - `$env:PYTHONPATH='apps/backend'; python -m pytest apps/backend/tests/test_tray_status.py -q` 通过。
  - `npm run build --prefix apps/frontend` 通过。

## v0.5.42-build-hotfix (2026-02-17)
- 目标：修复本机存在跨版本 Python 路径污染时，`scripts/build_installer.py` 在 PyInstaller 阶段崩溃的问题。
- 根因：
  - 当前解释器为 `Python 3.14`，但环境变量 `PYTHONPATH` 混入了 `Python312/site-packages`。
  - PyInstaller hook 进程导入 `numpy/matplotlib` 时加载到错误版本二进制扩展，触发 `numpy._core._multiarray_umath` 缺失。
- 变更：
  - `scripts/build_installer.py`
    - 新增 `_sanitize_pythonpath` / `_sanitize_runtime_pythonpath` / `_build_subprocess_env`。
    - 启动时自动清理不兼容 `PYTHONPATH`，并同步清理当前进程 `sys.path` 中的不兼容 `site-packages`。
    - `run()` 统一对所有子进程环境做净化，确保 PyInstaller 子进程不再继承错误路径。
  - 测试：
    - 新增 `apps/backend/tests/test_build_installer.py`，覆盖 `PYTHONPATH` 过滤与子进程环境净化逻辑。
  - 文档：
    - `docs/USAGE.md` 的“本地打包”章节补充自动净化说明。
- 验证结果：
  - `python scripts/build_installer.py --skip-frontend` 通过（本地复现环境下成功产出 `dist/LarkSync/LarkSync.exe`）。
  - `$env:PYTHONPATH=''; python -m pytest apps/backend/tests/test_build_installer.py -q` 通过（3 passed）。

## v0.5.42 (2026-02-16)
- 目标：避免日志默认筛选遗漏新状态，提升后续功能扩展时的可观测性。
- 变更：
  - `apps/frontend/src/pages/LogCenterPage.tsx`
    - 新增状态筛选项 `所有日志（推荐）`（值：`__all__`）。
    - 默认筛选改为 `__all__`，查询时不再传 `statuses`，后端返回全量状态。
    - 交互规则：选中“所有日志”后可一键回到全量；若逐个取消状态为空会自动回退到“所有日志”。
  - 文档同步：
    - `README.md`、`docs/USAGE.md` 更新为“默认所有日志”说明。
- 测试结果：
  - `npm run build --prefix apps/frontend` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.42`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.42`
  - 前端：`apps/frontend/package.json` → `0.5.42`

## v0.5.41 (2026-02-16)
- 目标：修复“删除动作在日志中心无单独类目/可见性差”的问题。
- 变更：
  - `apps/frontend/src/pages/LogCenterPage.tsx`
    - 同步日志状态筛选新增：`deleted`、`delete_pending`、`delete_failed`。
    - 状态徽章颜色映射优化：`delete_pending` 显示 warning，`delete_failed` 显示 danger。
  - `apps/frontend/src/lib/constants.ts`
    - 新增删除状态中文映射：待删除/删除成功/删除失败。
  - `apps/backend/src/services/sync_runner.py`
    - 删除流程失败分支新增 `delete_failed` 事件写入，避免仅 tombstone 状态变化而无同步日志记录。
  - 测试：
    - `apps/backend/tests/test_sync_runner.py` 新增 `test_process_pending_deletes_records_delete_failed_when_drive_delete_missing`。
- 测试结果：
  - `PYTHONPATH=apps/backend .venv\\Scripts\\python -m pytest apps/backend/tests/test_sync_runner.py apps/backend/tests/test_config_api.py -q` 通过（22 passed）。
  - `npm run build --prefix apps/frontend` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.41`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.41`
  - 前端：`apps/frontend/package.json` → `0.5.41`

## v0.5.40 (2026-02-16)
- 目标：落实删除联动设计（本地删/云端删）并把文件变更判定升级为“哈希优先”。
- 变更：
  - 删除联动主流程
    - `apps/backend/src/services/sync_runner.py`
      - 新增删除策略接入：`off / safe / strict`。
      - 新增墓碑处理链路：本地删除/云端删除检测、宽限到期执行、执行后清理映射与块状态。
      - 新增本地回收目录 `.larksync_trash/`（`safe` 模式下云删本地先入回收目录）。
      - 本地 watcher 不再直接忽略 `deleted` 事件，改为登记删除意图。
      - 下载阶段新增“云端缺失文件”检测，上传阶段新增“本地缺失文件”扫描。
      - `run_scheduled_upload` 在无上传文件时也会检测待处理删除墓碑。
  - 变更判定升级（哈希优先）
    - `apps/backend/src/services/sync_runner.py`
      - `_upload_file` 改为优先比较 `local_hash/local_size`，mtime 仅回退。
      - `_upload_markdown` 在缺块状态场景下新增 `link.local_hash` 快速跳过。
      - `_should_skip_download_for_unchanged` 新增本地哈希校验，避免仅凭 mtime 误判。
      - 下载/上传成功后统一回写 `SyncLink` 指纹字段（`local_hash/local_size/local_mtime/cloud_revision/cloud_mtime`）。
  - 数据与服务层
    - `apps/backend/src/services/sync_tombstone_service.py`
      - 刷新墓碑时保留最早过期时间，避免轮询场景反复刷新导致“永不过期”。
    - `apps/backend/src/api/sync_tasks.py`
      - 删除任务、重置映射时同步清理 tombstone 记录。
  - 设置页与配置
    - `apps/frontend/src/hooks/useConfig.ts`
      - 新增 `delete_policy`、`delete_grace_minutes` 类型与前端参数校验。
    - `apps/frontend/src/pages/SettingsPage.tsx`
      - “更多设置”新增删除策略与宽限时间输入，并支持独立保存。
  - 测试补充
    - 新增：`apps/backend/tests/test_sync_tombstone_service.py`。
    - 扩展：`apps/backend/tests/test_sync_runner.py`（删除事件/云端缺失/哈希判定）。
    - 扩展：`apps/backend/tests/test_sync_link_service.py`（指纹字段持久化）。
    - 扩展：`apps/backend/tests/test_config_api.py`（删除策略字段）。
    - 兼容修复：`apps/backend/tests/test_sync_runner_upload_new_doc.py` FakeLinkService 接口补齐。
- 测试结果：
  - `PYTHONPATH=apps/backend .venv\\Scripts\\python -m pytest apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py apps/backend/tests/test_sync_link_service.py apps/backend/tests/test_sync_tombstone_service.py apps/backend/tests/test_config_api.py -q` 通过（32 passed）。
  - `npm run build --prefix apps/frontend` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.40`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.40`
  - 前端：`apps/frontend/package.json` → `0.5.40`

## v0.5.39 (2026-02-16)
- 目标：优化“更多设置”操作路径，并修复“系统日志看起来为空”的可观测性问题。
- 变更：
  - `apps/frontend/src/pages/SettingsPage.tsx`
    - 将“保存更多设置”按钮移动到“展开/收起设置”按钮旁，减少滚动与跨区操作。
  - `apps/frontend/src/pages/LogCenterPage.tsx`
    - 系统日志默认排序由“最早优先”改为“最新优先”。
    - 增加系统日志加载失败提示，避免后端不可达时误显示为“暂无日志”。
- 诊断结论（删除行为，未改代码）：
  - 本地删除：当前 watcher 会忽略 `deleted` 事件，因此不会执行云端删除；下次下载会按云端重拉该文件。
  - 云端删除：当前下载阶段不会删除本地“云端已缺失”的文件；本地也不会自动上云重建（除非本地后续再次修改并触发上传逻辑）。
- 测试结果：
  - `npm run build --prefix apps/frontend` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.39`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.39`
  - 前端：`apps/frontend/package.json` → `0.5.39`

## v0.5.38 (2026-02-16)
- 目标：按最新反馈完善设置保存边界、任务完成率口径、日志筛选交互与 MD 云端副本策略。
- 变更：
  - 设置页保存拆分
    - `apps/frontend/src/pages/SettingsPage.tsx`：新增 `handleSaveMoreSettings` 与“保存更多设置”按钮；`更多设置`不再复用“同步策略”保存动作。
  - 完成率口径修正
    - `apps/frontend/src/lib/progress.ts`：新增统一进度计算工具，按 `completed / (total - skipped)` 计算。
    - `apps/frontend/src/pages/TasksPage.tsx`、`apps/frontend/src/pages/DashboardPage.tsx`：切换到新口径展示。
  - 日志中心筛选增强
    - `apps/frontend/src/pages/LogCenterPage.tsx`：状态筛选由单选改为复选，新增任务复选筛选；默认只勾选成功/失败核心状态。
    - `apps/backend/src/api/sync_tasks.py`：`/sync/logs/sync` 新增 `statuses`、`task_ids` 多值查询参数，并兼容旧参数 `status`、`task_id`。
    - `apps/backend/src/services/sync_event_store.py`：过滤逻辑支持多状态/多任务集合筛选。
  - MD 云端专用目录策略
    - `apps/backend/src/services/sync_runner.py`：新增 `_LarkSync_MD_Mirror` 机制：
      - 下行 Docx→MD 后自动同步 MD 到云端镜像目录。
      - 上行 MD 时同步更新镜像目录中的 MD 副本。
      - 下行扫描排除 `_LarkSync_MD_Mirror`，避免回流同步。
    - `apps/backend/src/services/drive_service.py`：新增 `delete_file()`，用于镜像覆盖前清理同名旧副本。
  - 测试补充
    - `apps/backend/tests/test_sync_event_store.py`：新增多选过滤用例。
    - `apps/backend/tests/test_sync_runner.py`：新增“跳过 `_LarkSync_MD_Mirror` 下行扫描”用例。
    - `apps/backend/tests/test_sync_runner_upload_new_doc.py`：新增“上传时同步云端 MD 镜像”用例。
- 测试结果：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_event_store.py apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py -q` 通过（26 passed）。
  - `npm run build --prefix apps/frontend` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.38`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.38`
  - 前端：`apps/frontend/package.json` → `0.5.38`

## v0.5.37 (2026-02-16)
- 目标：解决 NPI 文档；内嵌表格“历史占位不回刷”问题，并一次性补齐 Sheet 常见单元格转码结构。
- 变更：
  - 下载回刷策略
    - `apps/backend/src/services/sync_runner.py`：
      - 新增历史占位检测 `_contains_legacy_docx_placeholder()`。
      - 对 `doc/docx` 下载跳过判断新增“legacy `sheet_token` 占位”例外：若本地仍是旧占位，云端即使未更新也强制重下重转。
  - Sheet 转码补强
    - `apps/backend/src/services/transcoder.py`：
      - 内嵌 sheet 转码失败增加 warning 日志，避免静默吞错。
      - `_sheet_cell_text` 扩展支持 rich segment 样式、mention/link 对象、`formattedValue`、`formula`、bool/number、`richText`/`segments`/`runs` 与嵌套对象兜底。
      - 新增 `_sheet_extract_link`、`_sheet_apply_inline_style` 辅助方法。
  - 测试与内部基线
    - `apps/backend/tests/test_sync_runner.py`：新增 `test_runner_redownloads_docx_when_legacy_sheet_placeholder_present`。
    - `apps/backend/tests/test_transcoder.py`：新增 `test_transcoder_sheet_block_supports_rich_cell_variants`。
    - `docs/internal/transcoder_coverage.md`：补充“legacy 回刷 + rich sheet 单元格”覆盖项。
    - 新增 `docs/internal/transcoder_test_fixture.md`：提供全类型人工回归模板。
  - 文档同步
    - `README.md`、`docs/USAGE.md`：补充内嵌 sheet 单元格转码增强与历史占位自动回刷说明。
- 真实回归（飞书在线文档）：
  - 文档：`JRdXdv02toS6ByxqDP6cGDLtnIf`（NPI 清单副本）
  - 结果：5 个内嵌 sheet 全部转为 Markdown 表格，`placeholder_count=0`，`table_header_count=5`。
  - 产物：`F:/File/temp/test/自研具身智能机器人项目 - NPI全流程关键文档输出清单 副本.md`
- 测试结果：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sheet_service.py apps/backend/tests/test_transcoder.py apps/backend/tests/test_sync_runner.py -q` 通过（44 passed）。
- 版本更新：
  - 根：`package.json` → `v0.5.37`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.37`
  - 前端：`apps/frontend/package.json` → `0.5.37`

## v0.5.36 (2026-02-16)
- 目标：按用户反馈收敛设置入口与飞书新增文档转码缺失问题。
- 变更：
  - 设置页入口调整
    - `apps/frontend/src/pages/SettingsPage.tsx`：将“设备显示名称”输入从 OAuth 区块迁移到“更多设置”折叠面板，保留内部 ID 仅用于归属隔离的说明。
  - Docx 转码补齐
    - `apps/backend/src/services/transcoder.py`：
      - 新增 `equation` 元素渲染，公式输出为 `$...$` / `$$...$$`。
      - 新增 `block_type=40(add_ons)` 解析，Mermaid 数据输出 ```mermaid``` 代码块。
      - 新增 `block_type=30(sheet)` 占位渲染，输出 `内嵌表格（sheet_token: ...）`。
    - `apps/backend/tests/test_transcoder.py`：补充/更新 equation、sheet、add_ons 场景断言。
  - 线上回放验证（本地）
    - 清理目标任务 4 个文档的 `sync_links` 映射后重跑：
      - 任务 ID：`fabae395-0534-45e6-a52d-93d39434c8b9`
      - 结果：4 个目标文档重新下载成功。
      - 对比：专利文档公式与 mermaid 图恢复；NPI 文档中的内嵌表格不再丢失，改为可追踪的 sheet token 占位。
- 测试结果：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_transcoder.py -q` 通过。
  - `npm run build --prefix apps/frontend` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.36`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.36`
  - 前端：`apps/frontend/package.json` → `0.5.36`

## v0.5.35 (2026-02-16)
- 目标：修复“新建任务被误判测试任务”并优化连接状态展示为用户可读标识。
- 变更：
  - 测试任务识别改造（显式字段）
    - `apps/backend/src/db/models.py`：`SyncTask` 新增 `is_test` 字段（默认 `False`）。
    - `apps/backend/src/db/session.py`：启动迁移补齐 `sync_tasks.is_test` 列。
    - `apps/backend/src/services/sync_task_service.py`：`create/update/list` 全链路支持 `is_test`。
    - `apps/backend/src/api/sync_tasks.py`：任务创建/更新/响应模型新增 `is_test`。
    - `apps/frontend/src/pages/TasksPage.tsx`：移除按名称/路径关键词判定测试任务，改为仅使用后端 `is_test`；显隐按钮仅在 DEV 且存在 `is_test=true` 任务时显示。
  - 连接状态展示改造（设备名 + 飞书昵称）
    - `apps/backend/src/core/device.py`：新增 `current_device_name()`。
    - `apps/backend/src/core/config.py`、`apps/backend/src/api/config.py`：新增配置项 `device_display_name`，可持久化更新。
    - `apps/frontend/src/pages/SettingsPage.tsx`、`apps/frontend/src/hooks/useConfig.ts`：设置页新增“设备显示名称”编辑与保存。
    - `apps/backend/src/core/security.py`：`TokenData` 增加 `account_name`，并写入/读取 keyring。
    - `apps/backend/src/services/auth_service.py`：通过 `authen/v1/user_info` 同步补齐并缓存 `open_id + name`。
    - `apps/backend/src/api/auth.py`：`/auth/status` 返回 `account_name`。
    - `apps/frontend/src/hooks/useAuth.ts`、`apps/frontend/src/components/Sidebar.tsx`：侧边栏显示设备名称与飞书昵称，不再直接展示内部 ID。
  - 测试补充：
    - `apps/backend/tests/test_sync_task_service.py` 新增 `is_test` 覆盖用例。
    - `apps/backend/tests/test_auth_service.py`、`apps/backend/tests/test_security.py` 新增账号昵称缓存用例。
    - `apps/backend/tests/test_device.py` 新增设备显示名解析用例。
- 测试结果：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_task_service.py apps/backend/tests/test_auth_service.py apps/backend/tests/test_security.py apps/backend/tests/test_device.py apps/backend/tests/test_config_api.py -q` 通过（30 passed）。
  - `npm run build --prefix apps/frontend` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.35`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.35`
  - 前端：`apps/frontend/package.json` → `0.5.35`

## v0.5.34 (2026-02-16)
- 目标：按用户反馈优化连接状态区文案，并切换到“新用户测试态”排除历史数据干扰。
- 变更：
  - `apps/frontend/src/components/Sidebar.tsx`
    - 删除“OAuth 已连接，但身份标识未补齐。建议点击手动重新授权...”提示文案。
    - 保留设备/账号状态本身与操作按钮，减少干扰信息。
  - 运行环境操作（本地数据）：
    - 停止旧后端进程后，将 `data/larksync.db`、`data/larksync.db-wal`、`data/larksync.db-shm` 归档到：
      - `data/archive/db-20260216-212539/`
    - 清空本地 token 存储（模拟新用户未登录态）。
    - 重新初始化空数据库并启动 `npm run dev` 进行联调。
  - 结果核验：
    - 新实例 `GET /auth/status` 返回已包含 `device_id` 字段，当前为新用户态：`connected=false, open_id=null`。
    - 新库任务计数为 0，历史任务不再影响当前测试。
- 测试结果：
  - `cd apps/frontend && npm run build` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.34`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.34`
  - 前端：`apps/frontend/package.json` → `0.5.34`

## v0.5.33 (2026-02-16)
- 目标：修复“已授权但账号/设备 ID 不显示”与“跨设备任务串扰”。
- 根因定位：
  - 飞书 v1 token 响应在部分场景不返回 `open_id`，导致本地凭证长期缺失账号标识。
  - 任务过滤逻辑对 `owner_open_id` 存在空值放行，弱化了双重绑定。
  - 数据库初始化存在“空设备ID任务自动回填为当前设备”的逻辑，可能错误认领历史任务。
- 变更：
  - `apps/backend/src/services/auth_service.py`
    - 新增 `ensure_cached_identity()`：当缓存 token 缺失 `open_id` 时，自动调用 `authen/v1/user_info` 补齐并写回 TokenStore。
    - `_request_token()` 在 token 响应无 `open_id` 时，自动走用户信息接口补齐。
  - `apps/backend/src/api/auth.py`
    - `/auth/status` 在返回状态前自动尝试补齐身份字段，避免前端长期显示“无ID”。
  - `apps/backend/src/services/sync_task_service.py`
    - 任务列表/读写删除权限改为严格 `owner_device_id + owner_open_id` 匹配。
    - 移除 `owner_open_id` 空值自动放行逻辑。
    - 增加“安全迁移”：仅对可确认为本机路径的历史空 `owner_open_id` 任务自动补齐账号归属。
  - `apps/backend/src/db/session.py`
    - 移除启动阶段对 `sync_tasks.owner_device_id` 的批量回填，避免把历史未归属任务误绑定到当前设备。
  - 测试：
    - `apps/backend/tests/test_auth_service.py` 新增用例：验证 token 缺失 `open_id` 时可通过用户信息接口补齐。
    - `apps/backend/tests/test_sync_task_service.py` 调整历史空 open_id 任务用例，验证严格双重绑定后不会被误放行。
- 测试结果：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_auth_service.py apps/backend/tests/test_sync_task_service.py -q` 通过（19 passed）。
  - 本地脚本实测：`ensure_cached_identity()` 已将当前凭证 `open_id` 从 `None` 修复为真实值。
- 版本更新：
  - 根：`package.json` → `v0.5.33`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.33`
  - 前端：`apps/frontend/package.json` → `0.5.33`

## v0.5.32 (2026-02-16)
- 目标：修复同步任务路径展示视觉突兀，并明确“连接正常但账号/设备 ID 缺失”的状态语义。
- 变更：
  - `apps/frontend/src/pages/TasksPage.tsx`
    - 路径展示改为默认显示后半段（地址尾部），避免超长路径冲击布局。
    - 本地目录/云端目录都支持“点击展开/收起”，展开后按换行完整显示。
    - 移除路径区域内部的高对比背景框，保持与页面主体一致的卡片风格。
  - `apps/frontend/src/components/Sidebar.tsx`
    - 连接状态文案细化为：
      - 设备：`未获取设备ID`（已连接但缺失）/`待识别`（未连接）。
      - 账号：`已连接(未获取账号ID)`（已连接但缺失）/`未登录`。
    - 当已连接但 `open_id` 或 `device_id` 缺失时，增加提示文案，指引手动重新授权并刷新。
  - `docs/USAGE.md`
    - 登录与连接状态章节补充“已连接但 ID 未补齐”的解释与恢复建议。
- 测试结果：
  - `cd apps/frontend && npm run build` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.32`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.32`
  - 前端：`apps/frontend/package.json` → `0.5.32`

## v0.5.31 (2026-02-16)
- 目标：收敛“测试任务入口只在测试场景出现”的产品预期，并补充托盘排查说明。
- 变更：
  - `apps/frontend/src/pages/TasksPage.tsx`
    - 新增 `isDevMode = import.meta.env.DEV`，测试任务“显示/隐藏”按钮改为仅在开发/测试模式且存在测试任务时展示。
    - 空状态文案按模式区分：开发模式可提示“显示测试任务”，正式模式提示“测试任务已自动隐藏”。
  - 文档同步：
    - `README.md` 与 `docs/USAGE.md` 同步更新测试任务按钮规则。
    - `docs/USAGE.md` 补充托盘不显示时的本地排查要点（旧实例/48901 端口/pystray 与 Pillow 依赖）。
- 测试结果：
  - `cd apps/frontend && npm run build` 通过。
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_tray_lock.py apps/backend/tests/test_device.py apps/backend/tests/test_sync_task_service.py -q` 通过。
- 版本更新：
  - 根：`package.json` → `v0.5.31`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.31`
  - 前端：`apps/frontend/package.json` → `0.5.31`

## v0.5.30 (2026-02-16)
- 目标：修复你新反馈的 UI 体验问题，并继续收敛“托盘不显示”根因。
- 变更：
  - 同步任务页面：
    - `apps/frontend/src/pages/TasksPage.tsx` 将本地/云端长路径从单行截断改为“可滚动多行容器”，避免测试任务长路径溢出卡片。
    - “显示/隐藏测试任务”按钮改为仅在检测到测试任务时显示，正常使用场景不再出现无关按钮。
  - 登录页主题：
    - `apps/frontend/src/main.tsx` 在 React 启动前写入初始主题（默认 `light`）。
    - `apps/frontend/src/hooks/useTheme.ts` 默认主题改为明亮模式。
    - `apps/frontend/src/components/OnboardingWizard.tsx` 增加主题切换按钮，登录引导页支持明/暗主题。
  - 连接状态显示：
    - `apps/frontend/src/components/Sidebar.tsx` 设备/账号文案改为显式状态（如“待识别/未登录/已连接(无 open_id)”），避免空白误解。
  - 托盘可见性收敛：
    - `apps/tray/tray_app.py` 增加运行时 `PYTHONPATH` 自清理，自动移除与当前 Python 版本不兼容的 `site-packages` 条目，避免 `pystray/Pillow` 导入被污染环境破坏。
    - 托盘依赖导入失败时输出详细异常原因，便于定位（不再仅显示笼统“托盘缺失”）。
- 测试结果：
  - 前端：`cd apps/frontend && npm run build` 通过。
  - 后端（关键回归）：`PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_tray_lock.py apps/backend/tests/test_sync_task_service.py apps/backend/tests/test_device.py -q` 通过。
  - 本地启动验证：`npm run dev` 可正常拉起托盘进程并监听单实例锁端口 `48901`，Vite 监听 `3666`。
- 版本更新：
  - 根：`package.json` → `v0.5.30`
  - 后端：`apps/backend/pyproject.toml` → `v0.5.30`
  - 前端：`apps/frontend/package.json` → `0.5.30`

## v0.5.29 (2026-02-16)
- 目标：修复你反馈的“授权弹窗闪现/侧栏压缩/测试任务干扰/跨设备任务串扰”问题，并明确任务归属策略。
- 变更：
  - 前端鉴权加载态：
    - `apps/frontend/src/hooks/useAuth.ts`、`apps/frontend/src/hooks/useConfig.ts` 去除 React Query `placeholderData`，避免首屏在真实状态返回前误判为未登录而闪现授权向导。
  - 任务与侧栏体验：
    - `apps/frontend/src/App.tsx` + `apps/frontend/src/components/Sidebar.tsx` 保证桌面侧栏不被主内容区挤压。
    - `apps/frontend/src/pages/TasksPage.tsx` 默认隐藏测试任务，并提供显隐切换按钮。
    - `apps/frontend/src/components/Sidebar.tsx` 增加当前设备 ID / open_id 摘要展示，便于确认归属。
  - 任务归属强化：
    - `apps/backend/src/core/device.py`：设备标识改为“机器指纹优先，文件随机值兜底”。
    - `apps/backend/src/api/auth.py`：`/auth/status` 增加 `device_id` 字段。
    - `apps/backend/src/services/sync_task_service.py`：历史无 `owner_open_id` 任务在首次访问时自动归属当前账号，避免同设备多账号串任务。
  - 测试：
    - 新增 `apps/backend/tests/test_device.py`，覆盖设备 ID 的 env/机器指纹/文件兜底三条路径。
    - `apps/backend/tests/test_sync_task_service.py` 新增历史任务账号归属锁定用例。
  - 版本更新：
    - 根：`package.json` → `v0.5.29`
    - 后端：`apps/backend/pyproject.toml` → `v0.5.29`
    - 前端：`apps/frontend/package.json` → `0.5.29`
- 测试结果：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q` 通过。
  - `cd apps/frontend && npm run build` 通过。

## v0.5.28 (2026-02-16)
- 目标：修复代码巡检发现的高优先级问题，并将测试规范明确为“本地联调 + 打包体验”双轨制。
- 变更：
  - `core/version.py`：修复版本正则错误（`\s` 被误写为 `\\s`），`get_version()` 可正确读取后端版本。
  - `core/security.py`：修复 Keyring 空 refresh_token 的占位值 `_empty_` 读取还原逻辑，避免伪 token 参与刷新。
  - `scripts/sync_feishu_docs.py`：
    - 增加直接 zip URL 解析策略，兼容旧/新页面结构。
    - 当页面未发现 zip 时不再直接失败，改为写入 `_manifest.json`（`status=no_zip_found`）并返回成功，避免流程阻塞。
  - `update_service.py`：自动更新下载新增 sha256 完整性校验（读取 checksum 文件并校验本地包），校验失败立即中止。
  - `main.py`：全局异常默认不回显内部细节，返回通用错误 + `error_id`，可通过 `LARKSYNC_DEBUG_ERRORS=1` 开启详情。
  - `scripts/release.py`：
    - 版本解析支持稳定版与 dev 版。
    - 当前版本优先读取后端 `pyproject.toml`，降低版本源漂移风险。
    - 同步版本时前端沿用 npm 风格（默认去掉 `v` 前缀）。
  - 版本统一：根 `package.json`、后端 `pyproject.toml`、前端 `package.json` 分别更新为 `v0.5.28` / `v0.5.28` / `0.5.28`。
  - 文档更新：
    - 新增代码审查报告 `docs/reviews/review-2026-02-16.md`。
    - `AGENTS.md` 明确测试分层：本地开发测试 `npm run dev`，打包体验测试 `python scripts/build_installer.py`（可加 `--nsis` / `--dmg`）。
    - `docs/USAGE.md` 同步更新当前版本与双轨测试命令。
- 测试：
  - 前端：`cd apps/frontend && npm run build` 通过。
  - 后端：新增/更新单测（version/security/update/release/sync_feishu_docs 脚本）；建议在项目虚拟环境中执行 `python -m pytest`。
- 问题：无阻塞问题。
- 补充修复（同日）：
  - `apps/tray/backend_manager.py`：后端子进程启动前自动净化 `PYTHONPATH`，过滤与当前解释器版本不匹配的 `site-packages`，修复本机环境污染导致 `npm run dev` 后端起不来的问题。
  - 回归测试修复：`sync_runner` 系列测试桩补齐 `cloud_parent_token` 参数、`SyncTaskItem.cloud_folder_name` 新字段；`tray_status` 用例改为隔离重载 `src.api` 模块；`logging` 用例补齐队列日志 flush。
  - 结果：`cd apps/backend && python -m pytest tests -q` 全量通过。

## v0.5.27 (2026-02-10)
- 目标：MD↔飞书文档转换尚不完善，双向模式下默认仅支持云端飞书文档→本地 MD（下行），不开放本地 MD→飞书文档（上行），通过配置开关可手动开启。
- 变更：
  - `config.py`（AppConfig）：新增 `upload_md_to_cloud: bool = False`，默认关闭。
  - `api/config.py`：`ConfigResponse`、`ConfigUpdateRequest`、`update_config` 均新增该字段，支持读写。
  - `sync_runner.py`：
    - `_upload_path`：在 `.md` 分支增加判断，双向模式 + `upload_md_to_cloud=False` 时跳过 MD 上传并记录事件。
    - `_scan_for_unlinked_files`：同条件下不将 `.md` 文件加入待上传队列，避免无效扫描。
  - 注意：`upload_only` 模式不受此限制，用户显式选择上传时 MD 仍正常上传。
  - `SettingsPage.tsx`：在"更多设置 → 同步行为"区域新增「双向模式：允许 MD→飞书文档上传」开关（默认关闭），附使用说明。
- 版本号升级至 v0.5.27。

## v0.5.26 (2026-02-10)
- 目标：SyncLink 记录云端父目录信息，方便追踪排错；前端"更多设置"提供重置同步映射维护入口。
- 变更：
  - `models.py`：SyncLink 新增 `cloud_parent_token` 可空字段，记录文件上传/下载时所在的云端父文件夹 token。
  - `sync_link_service.py`：`SyncLinkItem` 数据类和 `upsert_link()` 方法均支持 `cloud_parent_token` 参数；`_to_item()` 同步映射。
  - `session.py`（init_db）：新增 `_ensure_column` 调用，自动为 `sync_links` 表添加 `cloud_parent_token` 列（兼容旧库升级）。
  - `sync_runner.py`：所有 `upsert_link` 调用（上传侧 × 4、下载侧 × 4）均传入 `cloud_parent_token`：
    - 上传侧使用 `_resolve_cloud_parent()` 解析的 parent_token。
    - 下载侧使用 `node.parent_token`。
  - `useTasks.ts`：新增 `resetLinks`、`resettingLinks` 以调用 `POST /sync/tasks/{task_id}/reset-links` API。
  - `SettingsPage.tsx`：在"更多设置"展开区底部新增"维护工具"板块，列出所有同步任务并提供"重置映射"按钮（含确认弹窗）。
- 版本号升级至 v0.5.26。

## v0.5.25 (2026-02-10)
- 目标：修复上传文件时忽略本地子目录结构、全部上传到云端根目录的问题。
- 根因分析：
  1. `_upload_file()` 和 `_create_cloud_doc_for_markdown()` 始终使用 `task.cloud_folder_token`（任务根目录）作为上传的父目录。
  2. 完全没有计算文件相对于同步根目录的路径，也没有在云端创建对应的子文件夹。
  3. 导致本地 `sync_root/sub1/sub2/doc.md` 上传后出现在云端根目录而非 `sub1/sub2/` 下。
- 修复：
  - `drive_service.py`：新增 `create_folder()` 方法，调用飞书 `POST /drive/v1/files/create_folder` 创建云端子文件夹。
  - `sync_runner.py`：新增 `_resolve_cloud_parent()` 方法，根据本地文件的相对路径逐层在云端查找/创建对应子文件夹，并用 `_cloud_folder_cache` 缓存避免重复 API 调用。
  - `sync_runner.py`：新增 `_find_subfolder()` 辅助方法，按名称查找云端子文件夹。
  - `_upload_file()` 和 `_create_cloud_doc_for_markdown()` 所有对 `task.cloud_folder_token` 的直接引用改为调用 `_resolve_cloud_parent()` 获取正确的父目录 token。
  - `sync_link_service.py`：新增 `delete_by_task()` 方法，支持按任务 ID 批量清除同步映射。
  - `sync_tasks.py`：新增 `POST /sync/tasks/{task_id}/reset-links` API，用于清除指定任务的所有同步映射，修复已错位的文件。
- 测试：27 项核心同步测试全部通过。
- 版本号升级至 v0.5.25。
- 已错位文件处理方案：用户手动删除云端根目录的错位文件，调用 reset-links API 清除旧映射，下次同步自动重新上传到正确位置。

## v0.5.24 (2026-02-10)
- 目标：修复双向同步模式切换后已有本地文件不上传的问题；NSIS 安装器增强。
- 根因分析：
  1. 调度上传 `run_scheduled_upload()` 仅处理 watchdog 检测到的文件变更（`_pending_uploads`）。
  2. 从 download_only 切换到 bidirectional 时，watcher 才启动，但已存在的本地文件不会触发 watchdog 事件。
  3. 因此这些文件永远不会被加入待上传队列，即使它们在云端并不存在。
- 修复：
  - `sync_runner.py`：新增 `_scan_for_unlinked_files()` 方法，全量扫描本地目录，将没有 SyncLink 的文件加入待上传队列。
  - `run_scheduled_upload()` 首次调度时自动执行初始扫描（通过 `_initial_upload_scanned` 集合避免重复）。
  - watcher 停止时（`_stop_watcher`）清除已扫描标记，确保重启后重新扫描。
- NSIS 安装器改进：
  - 安装前自动关闭运行中的 LarkSync 进程（支持覆盖安装）。
  - 卸载时弹出对话框询问是否删除用户数据（%APPDATA%\LarkSync + 凭据管理器）。
  - 默认保留用户数据，重新安装后无需再次授权。
  - 界面改为简体中文。
- 测试：156 项通过，5 项预存在失败与本次改动无关。
- 版本号升级至 v0.5.24。
- 问题：无。

## v0.5.23 (2026-02-09)
- 目标：回退至飞书 v1 OAuth 端点，修复之前误迁移至 v2 导致的 drive 权限丢失问题；优化令牌状态 UI 显示。
- 根因分析：
  1. 用户 `data/config.json` 保留了此前正常运行的 v1 OAuth 配置（`/authen/v1/index`、`/authen/v1/access_token`、`app_id`/`app_secret`），但 v0.5.17–v0.5.22 的修改逐步将端点迁移到 v2（`client_id`/`client_secret`、不同端点路径），导致授权后 token 缺失 drive 权限。
  2. 侧边栏显示短期 access_token 的 `expires_at`（约 2 小时），与用户实际数天连续使用的体验不符，容易误导。
- 修复：
  - `apps/backend/src/core/config.py`：默认值回退到 v1 端点；迁移逻辑改为仅修正已知错误 URL，保留正确的 v1 配置不变。
  - `apps/backend/src/services/auth_service.py`：`build_authorize_url` / `exchange_code` / `refresh` 全部改回使用 `app_id` / `app_secret` 参数（v1 协议），移除 `scope` / `response_type` 参数。
  - `apps/backend/src/api/config.py`：`ConfigResponse` 默认端点对齐 v1。
  - `apps/frontend/src/components/OnboardingWizard.tsx`：硬编码端点回退到 v1。
  - `apps/frontend/src/components/Sidebar.tsx`：连接状态时间改为显示"自动续期中"，避免误导。
  - `apps/backend/tests/test_auth_service.py`：断言改为检查 `app_id` 而非 `client_id`。
  - `docs/OAUTH_GUIDE.md`：文档端点回退到 v1。
- 测试结果：用户实测授权成功、云端目录正常获取。
- 版本号升级至 v0.5.23。
- 问题：无。

## v0.5.22 (2026-02-09)
- 目标：修复 OAuth scope 编码问题 + 增加 drive 权限诊断 + 前端权限不足引导。
- 根因分析：
  1. `urlencode` 默认用 `quote_plus` 将冒号编码为 `%3A`，导致 `drive:drive` → `drive%3Adrive`，飞书可能不识别。
  2. 用户授权后无直观方式判断 token 是否具有 drive 权限。
  3. 前端获取目录失败时仅显示裸错误，缺乏操作指引。
- 修复：
  - `build_authorize_url`：改用 `quote_via=quote` 保留冒号不编码，并打日志记录授权 URL。
  - `/auth/status` 增加 `drive_ok` 字段，实时检测 token 是否可访问 Drive API。
  - 前端 `App.tsx`：已连接但 `drive_ok=false` 时显示权限不足警告横幅。
  - 前端 `NewTaskModal.tsx`：目录树加载失败且涉及权限关键字时，显示详细操作指引。
- 测试：12 项全部通过。
- 版本号升级至 v0.5.22。
- 问题：无。

## v0.5.21 (2026-02-09)
- 目标：修复 OAuth 授权后缺少 drive/docs 权限的问题。
- 根因：切换到飞书 v2 OAuth 端点时，`build_authorize_url` 移除了 `scope` 参数。没有 scope，飞书只授予基本权限（用户身份），不包含 `drive:drive`、`docs:doc` 等资源访问权限。
- 修复：
  - `AuthService.build_authorize_url()` 恢复 `scope` 参数，将 `auth_scopes` 配置以空格分隔拼接到授权 URL。
  - 默认 scopes：`drive:drive`、`docs:doc`、`drive:drive.metadata:readonly`、`contact:contact.base:readonly`。
- 测试：12 项全部通过。
- 版本号升级至 v0.5.21。
- 问题：无。

## v0.5.20 (2026-02-09)
- 目标：修复 OAuth 回调时 Windows 凭据管理器报错 `CredWrite 1783` 的问题。
- 根因：Windows Credential Manager 单条凭据限制 2560 字节，飞书 access_token (JWT) + refresh_token + expires_at JSON 合并后超限。
- 修复：
  - `KeyringTokenStore` 拆分存储：access_token / refresh_token / expires_at 分别作为独立凭据条目。
  - 保留旧版合并格式的读取兼容（`oauth_tokens` key），确保升级后旧 token 仍可读取。
  - `set()` 写入后自动清除旧版合并记录。
  - `clear()` 清除所有 key（新旧格式）。
- 测试：12 项全部通过。
- 版本号升级至 v0.5.20。
- 问题：无。

## v0.5.19 (2026-02-09)
- 目标：诊断并修复 "Internal Server Error" 500 裸报错问题。
- 修复：
  - `main.py`：新增全局 `@app.exception_handler(Exception)` 处理器，所有未捕获的异常现在返回 JSON `{detail, path}`，不再显示裸 "Internal Server Error"。
  - `auth.py` `/auth/callback`：增加 `except Exception` 兜底，捕获 keyring 等非 AuthError 异常并返回详细错误。
  - 异常日志：`logger.error` 记录异常摘要，`logger.debug` 记录完整 traceback。
- 目的：即使仍有后端异常，前端/浏览器也能显示实际错误信息，方便定位根因。
- 版本号升级至 v0.5.19。
- 问题：待用户安装后观察实际错误详情。

## v0.5.18 (2026-02-09)
- 目标：修复飞书 v2 OAuth 端点不返回 refresh_token 导致认证流程中断的问题。
- 修复：
  - `_parse_token_response`：refresh_token 改为可选，缺失时设为空字符串并记录 warning 日志。
  - `_request_token`：新增 `_log_token_response` 方法，脱敏记录飞书 token 响应结构，方便排查。
  - `refresh()`：新增空 refresh_token 提前检测，提示"refresh_token 不可用，请重新登录"。
  - `KeyringTokenStore.get()`：兼容存储中缺少 refresh_token 的旧数据。
  - 新增 3 个测试：验证无 refresh_token 解析、空 refresh_token 刷新拒绝、空 refresh_token 存储往返。
- 测试：12 项全部通过，lint 无报错。
- 版本号升级至 v0.5.18。
- 问题：无。

## v0.5.17 (2026-02-09)
- 目标：修复飞书 OAuth 授权流程中 "missing required parameter: code (code=20003)" 错误。
- 根因分析：
  - 旧 token 端点 `/authen/v1/oidc/access_token` 要求 `Authorization: Bearer <app_access_token>` 头部鉴权，但我们发送的是 body 中的 `app_id`/`app_secret`，导致飞书忽略请求体。
  - 旧 authorize 端点域名 `open.feishu.cn` 不正确，应为 `accounts.feishu.cn`。
  - 参数名使用了旧版 `app_id`/`app_secret`，v2 标准协议要求 `client_id`/`client_secret`。
- 修复：
  - 授权端点改为：`https://accounts.feishu.cn/open-apis/authen/v1/authorize`。
  - Token 端点改为：`https://open.feishu.cn/open-apis/authen/v2/oauth/token`（标准 OAuth2，body 中直接传 client_id/client_secret）。
  - `auth_service.py`：`build_authorize_url` 参数 `app_id` → `client_id`；`exchange_code`/`refresh` 参数 `app_id`/`app_secret` → `client_id`/`client_secret`。
  - `config.py`：`_load_config` 增加旧 URL 自动迁移，已保存的错误端点会自动修正为新端点。
  - `OnboardingWizard.tsx`：保存时始终使用正确的新端点常量，不再保留旧配置值。
  - `OAUTH_GUIDE.md`：更新默认端点说明。
  - 测试：`test_auth_service.py` 断言更新，9 个测试全部通过。
- 版本号升级至 v0.5.17。
- 问题：无。

## v0.5.16 (2026-02-09)
- 目标：修复 OAuth 配置不完整导致授权失败的问题，完善引导向导的配置保存逻辑。
- 结果：
  - 后端 AppConfig 为 auth_authorize_url 和 auth_token_url 设置飞书标准默认值，不再强制用户手动填写。
  - OnboardingWizard 保存时自动填充 authorize_url / token_url（已有值则保留），确保只需填写 App ID 和 Secret 即可完成配置。
  - 修正 redirect_uri 生成逻辑：统一使用 `origin + /auth/callback`，移除 apiUrl() 多余调用。
  - SettingsPage redirect_uri 同步修正，保持一致。
  - 版本号升级至 v0.5.16。
- 测试：lint 检查通过，无 TS 类型报错。
- 问题：无。

## v0.5.15 (2026-02-09)
- 目标：重设计应用启动引导流程，增加飞书连接状态检测与引导向导；优化新建任务弹窗位置。
- 结果：
  - 新增 OnboardingWizard 组件：全屏两步引导（Step 1 OAuth 配置 → Step 2 连接飞书）。
  - App.tsx 增加门控逻辑：加载中显示骨架屏，OAuth 未配置或未连接时展示引导向导，已连接才渲染主 UI。
  - DashboardPage 移除冗余的大型 onboarding banner，简化为防御性一行提示。
  - NewTaskModal 弹窗从 items-start 改为 items-center 实现垂直居中。
  - 版本号升级至 v0.5.15。
- 测试：lint 检查通过，无 TS 类型报错。
- 问题：无。

## v0.5.14 (2026-02-09)
- 目标：修复新建任务弹窗位置过高导致顶部不可见的问题。
- 结果：
  - 弹窗使用 Portal 挂载到 body，避免父级 transform 影响定位。
  - 覆盖层改为可滚动容器，顶部留出安全边距。
  - 版本号升级至 v0.5.14（backend）。
- 测试：未执行（UI 视觉修正）。
- 问题：无。

## v0.5.13 (2026-02-08)
- 目标：修复安装包体验与打包后端启动异常。
- 结果：
  - 安装完成页增加“立即启动”选项。
  - Windows 图标改为品牌 Logo（安装包/快捷方式/EXE）。
  - 打包环境后端启动改为 LarkSync.exe --backend，修复 uvicorn 参数报错。
  - 版本号升级至 v0.5.13（backend）。
- 测试：本地打包通过；`python -m pytest apps/backend/tests/test_backend_manager.py`。
- 问题：无。

## v0.5.12 (2026-02-08)
- 目标：修复本地 NSIS 构建失败与版本号读取异常。
- 结果：
  - 修正版本读取正则，避免返回 0.0.0。
  - NSIS 脚本改用 __FILEDIR__ 推导项目根路径，避免空格/引号导致的解析问题。
  - 版本号升级至 v0.5.12（backend）。
- 测试：本地 `python scripts/build_installer.py --nsis` 成功生成安装包。
- 问题：无。

## v0.5.11 (2026-02-08)
- 目标：修复 NSIS 构建阶段的预处理指令错误。
- 结果：
  - 修正 !ifexist 指令拼写，避免构建失败。
  - 版本号升级至 v0.5.11（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.10 (2026-02-08)
- 目标：修复 Windows 安装包在安装时误报缺失构建产物。
- 结果：
  - NSIS 脚本改为编译期校验输出，不在安装期检查 CI 路径。
  - NSIS 打包路径改用 Windows 原生路径格式。
  - 版本号升级至 v0.5.10（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.9 (2026-02-08)
- 目标：修复 macOS Release 未生成 DMG 的问题。
- 结果：
  - DMG 生成逻辑支持 dist/LarkSync.app 与 dist/LarkSync/LarkSync.app 两种路径。
  - 缺失 .app bundle 时直接失败，避免静默跳过。
  - 版本号升级至 v0.5.9（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.8 (2026-02-08)
- 目标：修复 NSIS 打包阶段找不到输出目录的问题。
- 结果：
  - NSIS 脚本改用固定 SOURCE_DIR 并校验输出文件存在。
  - build_installer 版本读取增强，支持 LARKSYNC_VERSION 与 UTF-8 BOM。
  - workflow 将 tag 版本注入 LARKSYNC_VERSION。
  - 版本号升级至 v0.5.8（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.7 (2026-02-08)
- 目标：修复 Windows Release 中 NSIS 安装包未生成的问题。
- 结果：
  - workflow 增加 NSIS 路径写入 PATH。
  - build_installer 找不到 makensis 时直接失败，并校验安装包产物存在。
  - 版本号升级至 v0.5.7（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.6 (2026-02-08)
- 目标：修复 Release 构建未上传安装包的问题。
- 结果：
  - workflow 增加 dist 列表与 upload-artifact，缺失产物直接失败。
  - action-gh-release 启用 fail_on_unmatched_files，避免空发布。
  - 版本号升级至 v0.5.6（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.5 (2026-02-08)
- 目标：修复 PyInstaller spec 在 CI 下缺失 __file__ 的问题。
- 结果：
  - build_installer 运行 PyInstaller 时注入项目根路径并固定工作目录。
  - spec 支持从环境变量/工作目录解析 project_root。
  - 版本号升级至 v0.5.5（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.4 (2026-02-08)
- 目标：修复 Windows runner 下 npm 可执行文件解析失败。
- 结果：
  - build_installer 在 Windows 下自动解析 npm.cmd/npx.cmd，避免 FileNotFoundError。
  - 版本号升级至 v0.5.4（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.3 (2026-02-08)
- 目标：修复 Windows Release 构建脚本的控制台编码错误。
- 结果：
  - build_installer 增加 UTF-8 输出配置，避免中文日志在 Windows runner 触发崩溃。
  - 版本号升级至 v0.5.3（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.2 (2026-02-08)
- 目标：修复 Release 版本校验正则，确保 workflow 可读取版本号。
- 结果：
  - 调整 workflow 中版本解析正则转义，避免读取为空。
  - 版本号升级至 v0.5.2（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.1 (2026-02-08)
- 目标：修复 Release Build 工作流 YAML 语法并重新触发构建。
- 结果：
  - 修复 workflow 中的版本校验脚本（避免 YAML 语法错误）。
  - 版本号升级至 v0.5.1（backend）。
- 测试：待 tag 构建验证。
- 问题：无。

## v0.5.0 (2026-02-08)
- 目标：v0.5.x 打包大里程碑收束并发布稳定版。
- 结果：
  - 打包链路完成（PyInstaller / NSIS / DMG），Release 自动构建并上传产物。
  - 自动更新稳定版检查与下载流程可用（设置页可配置）。
  - 版本号升级至 v0.5.0（backend）。
- 测试：未执行（需触发 Release tag 构建后验证产物与更新下载）。
- 问题：无。

## v0.5.0-dev.6 (2026-02-08)
- 目标：完成自动更新（稳定版）检查与下载流程。
- 结果：
  - 新增更新检查服务与调度器，支持 GitHub Releases 稳定版检查与下载。
  - 配置中心新增自动更新开关、检查间隔、dev→稳定版提示配置。
  - 设置页新增自动更新面板与手动检查/下载入口。
  - 版本号升级至 v0.5.0-dev.6（backend）。
- 测试：`python -m pytest tests/test_update_service.py`（apps/backend）。
- 问题：需在真实 tag 发布后验证 Release 产物下载流程。

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
