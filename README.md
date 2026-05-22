# LarkSync

<p align="center">
  <img src="assets/branding/LarkSync_Logo_Horizontal_Lockup_FullColor.png" alt="LarkSync Logo" width="520" />
</p>

本地优先的飞书文档同步工具，用于打通飞书云文档与本地文件系统（Markdown/Office）的协作链路。  
当前版本：`v0.7.17-dev.9`（2026-05-22），核心运行形态为托盘常驻 + Web 管理面板。

## 项目简介
LarkSync 面向“云端协作 + 本地知识管理”并行使用的用户场景。你可以继续在飞书中协作，同时把文档体系稳定地纳入本地目录、NAS 和后续 AI 助手工作流中，避免重复搬运和手工同步。

项目重点不只是“下载备份”，而是双向同步中的一致性与可维护性：任务级策略、设备与账号归属隔离、删除联动策略、更新检查与日志可观测性都已落地。

## 适用场景
1. 作为 NAS 与飞书联合应用的补充，把飞书纳入个人整体工作体系。
2. 本地文档可直接上传飞书，免去手工重复上传。
3. 为 OpenClaw 等 AI 助手做文档管理准备，降低飞书 API 额度与性能压力。
4. 打通本地编辑、云端协作、多设备同步。

## 功能亮点
- 飞书 Docx 与本地 Markdown 双向同步。
- 云端文件下载写回本地时，若目标文件被 WPS/Office 等进程占用，会短暂重试，并在日志里明确提示“目标文件正被其他程序占用，请关闭后重试”。
- 任务级 MD 模式：`enhanced` / `download_only` / `doc_only`。
- 删除联动策略：`off` / `safe` / `strict`。
- 文件夹会作为同步对象持久化映射；本地删除已同步文件夹会删除对应飞书文件夹并清理子映射，云端文件夹删除会按删除策略移动或删除本地目录。
- 设置页支持按任务配置“双向忽略目录”，可排除 `node_modules`、`.git`、构建产物和缓存目录；加入后这些子目录不会再参与上传、下载和删除联动。
- 设备 + 飞书账号双重归属隔离，避免跨设备串任务。
- 仪表盘改为同步健康总览，优先展示本地与飞书是否一致、待同步数量、失败与冲突，以及最近成功同步结果。
- 任务卡片默认聚焦“本地目录 ↔ 飞书目录”的同步关系与健康摘要，工程字段收进任务管理详情。
- 冲突管理支持连续为多条冲突选择“使用本地 / 使用云端”；前端会明确显示“已排队 / 处理中 / 等待任务空闲 / 已完成 / 处理失败”，并通过单 worker 严格串行提交请求，对“任务运行中”的冲突处理自动重试，避免连续点击时并发打到后端。
- 日志中心的“实际变更”、任务运行摘要和任务卡片现在会明确展示 `删除 / 待删除 / 删除失败` 等删除链路状态，不再只显示上传/下载。
- 日志中心切换任务时，默认先回到 `概览`，任务概览和运行摘要优先读取 `sync_runs` 摘要表；旧任务即使暂时没有 `sync_runs` 摘要，也不会在概览切换时回退扫描 `sync-events.jsonl`，只有真正打开事件/问题明细时才按需读取大日志。
- 日志中心新增 `sync_run_events` 事件持久化层：同步事件会双写到 SQLite 与 `sync-events.jsonl`，后台会按 checkpoint 持续回填/追平旧日志；任务诊断、问题列表和事件时间线现在优先读取数据库，回填未完成时才受控回退 JSONL，减少切任务和打开日志中心时的文件扫描卡顿。
- 更新安装与重置同步映射等维护动作统一使用应用内确认框，明确说明影响范围。
- 首次授权向导支持从“连接飞书”返回 OAuth 配置页，填错参数可直接修正重试。
- 自动更新检查与更新包下载（sha256 校验）。
- 自动更新检查在 GitHub Release API 被匿名限流返回 403/429 时，会回退到公开 Release 跳转页解析最新版本，避免安装包存在但检查失败。
- 自动更新支持校验来源回退：优先使用 GitHub Release 资产 `digest`，其后兼容 `.sha256` 文件与 Release 正文中的 sha256。
- 发布流程会同步上传 `.sha256` 资产并写入 Release 正文，兼容旧版本客户端自动更新。
- 更新包下载完成后支持“确认安装”安全流程：用户确认后由托盘延迟接管安装请求，避免前端请求被中断；Windows 端优先使用系统 ShellExecute 直接拉起安装包，失败时再回退 PowerShell，降低“程序退出但安装器未启动”的风险。
- Windows 静默更新 helper 现在使用 PowerShell `Start-Process -FilePath` 正确拉起安装器和重启当前版本，修复 `-LiteralPath` 参数错误导致 helper 接管后立即失败的问题。
- Windows 静默更新 helper 现在会以 detached + breakaway 方式脱离托盘进程，避免只写出 `installer_started` 就因主程序退出而中断，确保安装完成后仍能负责重启新版本。
- Windows 静默更新 helper 会在安装器退出码为空时复核安装目录版本，并对重启进程做多轮确认与重试；日志会记录目标版本、安装后版本、重启 attempt 和 `restart_failed`，便于定位升级后未自动拉起的问题。
- Windows 静默安装启动改为落地 bootstrap/worker `.ps1` 脚本并通过 PowerShell `-File` 拉起，避免嵌套 `-EncodedCommand` 过长触发 `WinError 206`，导致安装包已下载但静默安装没有启动。
- Windows 静默安装交接文件兼容 PowerShell 5.1 的 UTF-8 BOM，并改为无 BOM UTF-8 写入，避免 helper 已启动但托盘读取 handoff 失败后误报接管超时。
- Windows 静默安装现在会区分 bootstrap 与 worker 的 handoff 阶段；托盘只有在 worker 真正开始执行或安装器已启动后才退出，若只收到 bootstrap 的 `worker_pid` 暂存回执会保留当前版本并明确报错，不再误判为“已接管”。
- Windows 静默安装生成的 `bootstrap.ps1` / `worker.ps1` 现在改为带 BOM 的 UTF-8 脚本文件，兼容 Windows PowerShell 5.1 对 `.ps1` 编码的读取；避免脚本里的中文日志文本被误解码后直接触发 ParserError，导致 handoff 永远停在 `bootstrap_started`。
- 发布构建环境固定为 `Python 3.14.x + Node 25.x`；`python scripts/build_installer.py` 会在非基线环境下 fail fast，并输出完整构建环境摘要，避免“本地能打包、CI/正式版环境不一致”的漂移问题。
- FastAPI 应用生命周期已切换为 `lifespan`，统一管理数据库初始化、watcher、同步调度、更新调度和日志维护后台服务的启动与关闭顺序。
- SQLite 初始化已升级为显式 schema version 迁移流程：`init_db()` 会顺序执行迁移注册表并将当前版本写入 `sync_meta.schema_version`，旧库升级路径可以通过自动化测试稳定验证。
- 前端质量门补齐 `eslint + vitest` 页面级 smoke 回归，覆盖 App、任务页、日志中心和设置页的基础挂载与关键壳层文案。
- 日志中心正在按“组合层 + hook + 分区视图”继续拆分：任务诊断查询状态已收口到独立 hook，系统日志与冲突管理已拆成独立视图组件，为后续继续分离任务诊断详情视图和冲突队列状态做准备。
- 日志中心冲突处理队列状态机现已独立为 `useConflictResolutionQueue`，相关状态统计与状态文案判断也沉淀到了可测试 helper，页面不再直接维护队列 ref 和重试状态流转细节。
- 日志中心的任务诊断工作台已进一步拆成 `TaskSelectionPanel`、`RunHistoryPanel`、`TaskDiagnosticsDetailPanel` 三个视图组件，并新增独立 smoke test；`LogCenterPage.tsx` 已收口为查询编排与面板装配层，便于继续拆更细的任务详情视图。
- 日志中心任务诊断详情区现已继续细分为 `TaskDiagnosticsOverviewTab`、`TaskDiagnosticsProblemsTab`、`TaskDiagnosticsEventsTab` 三个独立展示组件，并补齐 tab 级 smoke test；`TaskDiagnosticsDetailPanel.tsx` 只保留 header、tab 切换与数据接线。
- 日志中心事件时间线状态与查询已进一步下沉到 `useTaskEventTimeline`，并新增 `taskEventTimeline` helper 测试覆盖查询参数拼装与轮询判断；`useLogCenterTaskDiagnostics.ts` 不再直接维护事件筛选、分页与时间线请求细节。
- 日志中心任务选择与运行选择状态现已下沉到 `useTaskDiagnosticsSelection`，相关默认选中、任务筛选与 active run 解析逻辑沉淀到 `taskDiagnosticsSelection` helper；`useLogCenterTaskDiagnostics.ts` 进一步收口为概览查询、诊断查询与子 hook 编排层。
- 新增 `python scripts/update_install_smoke.py`，可在 Windows 上用真实 PowerShell bootstrap/worker 链路验证静默安装接管是否能推进到目标 handoff 阶段。
- 更新检查会保留已校验且版本、大小、sha256 匹配的安装包路径，避免下载完成后再次检查把 `download_path` 清空，造成页面误判为尚未下载。
- 设置页更新区新增“打开安装包目录”，静默安装失败时可直接打开下载目录手动排查或重试安装。
- 静默安装接口会拒绝“当前版本或更旧版本”的重复安装请求，避免升级其实已成功、再次点击却只看到无效安装的误判。
- Windows 托盘会忽略“安装包版本小于等于当前运行版本”的过期静默安装请求，避免安装成功后因残留请求再次触发自更新，表现成打不开或反复重启。
- 日志中心与同步状态面板，便于排查同步异常。
- 日志中心运行详情的事件时间线支持按 `上传 / 下载 / 删除 / 问题 / 跳过 / 实际变更` 分别筛选，便于单独查看不同同步动作。
- 仪表盘拆分“当前运行”和“最近同步”任务视图，并用真实任务状态展示服务当前是否正在同步，避免启用、运行、最近活动混淆。
- 日志中心重构为任务诊断入口：后端提供任务概览与单任务诊断接口，事件带运行 ID，前端可按任务查看真实运行状态、当前处理文件、问题摘要和事件时间线，并保留系统日志与冲突管理。
- 日志中心进一步改为“任务 -> 运行 -> 事件”视图：每次同步执行单独生成一条运行记录，任务卡片和诊断概览默认只反映最近一次运行，历史失败不会继续污染后续成功运行；可按 `run_id` 单独查看某次同步的问题摘要和完整时间线。
- 后端新增 `sync_runs` 运行摘要表：每次同步的开始时间、结束时间、触发来源、上传/下载/失败/冲突计数和最近错误会单独持久化，日志中心优先读取该表展示运行列表与最近结果，`sync-events.jsonl` 继续保留为细粒度事件时间线。
- 日志中心任务诊断页继续收口：任务诊断工作区与侧边栏底边对齐，`概览` 去掉重复的当前处理文件卡片，改为展示本地目录和云端目录等同步目标信息。
- 正式 CLI 入口 `python scripts/larksync_cli.py`：覆盖授权状态、配置、任务、日志、更新、冲突与目录树等核心能力，并提供 `bootstrap-cache` 高层初始化命令、`workflow-template*` 标准工作流模板命令，以及支持恢复执行和运行记录索引化的 `workflow-plan` / `workflow-execute` / `workflow-run-*`，适合 Agent / Skill 自动化调用。
- 发布质量门会在 GitHub Actions 中执行后端 pytest、后端 editable 安装校验和前端构建，避免测试红灯或包元数据错误进入正式安装包发布。
- 内置 OpenClaw Skill 模板：支持“低频同步到本地再本地读取”的降 token 用法。
- 本地持续编辑静默窗口：连续修改同一文档时合并上传，避免重复上云。
- 双向同步的 Markdown 上行会在覆盖云端前复核云端修改时间；若云端相对本地基线已更新，会阻止覆盖并记录冲突，避免本地旧版本覆盖飞书协作版本。
- 冲突管理对同一文件、同一版本差异的未解决冲突做幂等处理，并折叠历史残留的重复未解决记录，避免页面出现两条相同冲突。
- 冲突管理中的“使用本地 / 使用云端”会真正执行一次定向同步：本地优先会强制把当前本地版本上传覆盖云端，云端优先会强制下载当前云端版本覆盖本地；执行失败时冲突不会被提前标记为已解决。
- 本地新建 Markdown 首次创建飞书文档后，会立即补齐 `local_hash/local_mtime/cloud_mtime/cloud_revision` 同步基线，避免同一轮后续上传把“刚由程序自己创建的云端文档”误判成冲突。
- 自动更新的安装包、状态文件与安装请求会在正式版中落到用户数据目录而不是安装目录；更新后会用当前程序版本重算更新状态，避免安装成功后仍误判“有可更新版本”。
- Windows 自动更新支持静默安装链路：更新请求默认走 NSIS `/S`，托盘会等待外部 helper 确认接管后再退出；helper 使用隐藏窗口的 PowerShell 进程组启动，避免 `DETACHED_PROCESS` 导致接管回执丢失；helper 负责等待安装器退出、记录 PID/退出码/重启动作，并在安装器未拉起或失败时恢复当前版本；如安装到 `Program Files`，Windows 仍可能弹出 UAC 权限确认。
- 非 MD 文件更新上传自动替换旧云端副本，避免 PDF 等附件多次修改后在飞书侧累积同名重复文件。
- 上传链路自动忽略常见临时文件与系统噪音文件（如 `~$*.docx`、`*.tmp`、`Thumbs.db`），避免本地编辑过程中的临时产物误传到飞书。
- Markdown 上行支持 HTML 内嵌 `data:image/...` 图片：会优先复用本地 `figures/`、`插图/`、`assets/` 中的对应图片资源并带 MIME 上传为飞书图片块，避免飞书前端显示“无法导入该图片”。
- Markdown 图片回填飞书图片块时会按源图像素尺寸写入等比显示宽高，避免空图片块默认尺寸导致插图被横向拉伸。
- Markdown 上行遇到失效的 `fig-数字` 图片相对路径时，会按图号回退查找同级 `figures/`、`插图/`、`assets/` 中的真实源图，避免重命名/迁移后的设计说明书缺图。
- 同步器会忽略 `figures/` 与 `插图/` 这类嵌入源图目录，避免源图被当作独立附件重复上传。
- Markdown 上行遇到超限表格时，会优先保留一张原生飞书表格：创建阶段先按飞书建表上限建立初始行，再通过表格行插入补齐剩余行，避免把 V1.5 这类长表拆成多张表；列宽按 Markdown 文档顺序匹配并覆盖飞书转换器的窄默认值，常见多列表格以 732 偏好总宽为目标，贴近飞书原生云文档默认表格宽度，短列保留最小宽度、长文本列按内容权重分配剩余空间，同时保留整表上限防止横向滚动；单元格内容写入后会清理默认空段落，避免内容被空行顶到下方；既有云端文档缺少当前表格渲染修复标记时，即使本地内容 hash 未变化，也会跳过局部 diff 并在原 doc token 内全量重建。
- 飞书 API 请求会对 429、飞书限频码以及 500/502/503/504 临时网关错误执行指数退避重试，降低 `blocks/convert` 瞬时 502 对同步任务的影响。
- 新建任务或距离上次运行超过 48 小时的任务，会先执行一轮“无删除补齐”：只下载/上传双方缺失的内容并跳过删除墓碑，再进入常规同步，降低首次运行和长时间离线后的误删除风险。
- 删除同步在执行云端删除前会检查同一云端 token 是否仍被其他本地路径使用，并静默程序自身移入 `.larksync_trash` 的文件事件，避免文件移动/回收触发反向误删。
- 云端下载写回本地前会预先静默 watcher，避免程序自己下载文件时又被当成本地修改排进上传队列，反向覆盖刚更新过的飞书文档。
- 上传与下载调度改为任务级独立循环：单个任务长时间同步、失败或卡在大文件处理时，不再拖住其他任务开启新的同步 run。
- `sync_links` 现在会单独记录 Markdown 本地资源基线：下载生成的图片/附件引用会和对应云端版本一起落库，后续只有正文或本地资源真正偏离该基线时才会重新上传，避免“云端刚下载到本地，随后同轮又被回传覆盖云端”。
- 日志中心任务诊断页改为更紧凑的排障工作台：保留全局侧边栏和顶部页头，任务选择上移到页头下方的上下文选择条，下方主区域只保留“左侧运行记录 / 右侧运行详情”；运行详情用摘要条替代碎片化统计卡，事件筛选仅在事件 Tab 下显示，整体更适合任务数量不多时的快速排障。
- 日志中心任务诊断页进一步压缩信息密度：任务上下文条收成更扁的一行半，运行记录卡与详情头部去除重复信息并采用更紧凑的两行结构，`run_id` 改为短码显示，减少拥挤与视觉噪音。
- 日志中心任务诊断页继续收口：`任务上下文` 更名为 `任务选择`，移除无意义说明文案和常驻任务筛选标签，右下常驻运行状态并入 `概览` 标签页，同时在头部保留最近活动时间，释放事件时间线的可视高度。
- 日志中心任务诊断页的任务选择器升级为可搜索 Combobox：任务选择框不再混入本地路径，只显示任务名；搜索、筛选和选择合并到一个下拉面板中，右侧详情头部的最近活动时间与任务名同排显示，并进一步减少多余分割线。
- 日志中心任务诊断页继续压缩：任务选择器只展示任务名、任务路径从选择框移出；右侧详情头部保留最近活动时间但并入标题行，常驻运行摘要维持在 `概览` 标签页中，默认详情区更聚焦事件时间线。
- 日志中心会把应用退出、更新或进程终止遗留的历史 `running` 运行显示为“已中断”，避免旧运行记录长期误显示为同步中；运行耗时按秒级时间戳正确计算。
- 同步事件中的等待上传记录会带上当前运行 ID，便于按单次运行完整筛选排障。
- 飞书文件上传失败会在错误信息中保留飞书错误码、HTTP 状态和请求 ID（如有），避免只显示 `unknown error.` 难以定位。
- 更新状态缓存会自动清理已过期或版本不匹配的下载包路径，避免页面拿旧安装包再次发起静默安装。
- `download_only` 任务不会创建或写入云端 `_LarkSync_MD_Mirror`，即使历史任务遗留了 `md_sync_mode=enhanced` 也只做纯下载。
- 设置页、新建任务与任务管理页会根据同步模式收起不适用的上传/下载配置，减少 `download_only` / `upload_only` 场景中的无效选项与误操作。

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

### 开发质量门
```bash
npm --prefix apps/frontend run lint
npm --prefix apps/frontend run test
npm --prefix apps/frontend run build
python -m pytest -q        # 在 apps/backend 目录执行
python scripts/update_install_smoke.py  # Windows 静默安装 smoke
```

### 安装包构建基线
- 发布打包默认基线：`Python 3.14.x` + `Node 25.x`
- `python scripts/build_installer.py` 会打印 Python/Node/平台环境摘要，并在非基线环境下直接失败
- 如需临时绕过，可显式设置 `LARKSYNC_ALLOW_UNSUPPORTED_BUILD_PYTHON=1` 或 `LARKSYNC_ALLOW_UNSUPPORTED_BUILD_NODE=1`

### 方式 2：直接下载安装包（面向使用者）
- 打开发布页：<https://github.com/gooderno1/LarkSync/releases>
- Windows 下载 `LarkSync-Setup-*.exe`
- macOS 下载 `LarkSync-*.dmg`

## 文档导航（建议先读）
- 使用文档：[`docs/USAGE.md`](docs/USAGE.md)
- OAuth 配置：[`docs/OAUTH_GUIDE.md`](docs/OAUTH_GUIDE.md)
- 同步逻辑：[`docs/SYNC_LOGIC.md`](docs/SYNC_LOGIC.md)
- 发布标准：[`docs/RELEASE_STANDARD.md`](docs/RELEASE_STANDARD.md)
- CLI 契约：[`docs/CLI_AGENT_CONTRACT.md`](docs/CLI_AGENT_CONTRACT.md)
- OpenClaw Skill：[`docs/OPENCLAW_SKILL.md`](docs/OPENCLAW_SKILL.md)

## CLI 示例
```bash
python scripts/larksync_cli.py check
python scripts/larksync_cli.py workflow-template-list
python scripts/larksync_cli.py workflow-template --template daily-cache
python scripts/larksync_cli.py workflow-plan --template daily-cache --entrypoint helper --set "local_path=D:\\Knowledge\\FeishuMirror" --set "cloud_folder_token=<TOKEN>"
python scripts/larksync_cli.py workflow-execute --template daily-cache --dry-run --from-step bootstrap --to-step inspect-task --output-json-file data\\workflow.json --set "local_path=D:\\Knowledge\\FeishuMirror" --set "cloud_folder_token=<TOKEN>"
python scripts/larksync_cli.py workflow-execute --template daily-cache --run-id demo-run --skip-completed --set "local_path=D:\\Knowledge\\FeishuMirror" --set "cloud_folder_token=<TOKEN>"
python scripts/larksync_cli.py workflow-run-list --limit 10
python scripts/larksync_cli.py workflow-run-show --run-id demo-run
python scripts/larksync_cli.py workflow-run-prune --keep 20
python scripts/larksync_cli.py task-list
python scripts/larksync_cli.py bootstrap-cache --local-path "D:\\Knowledge\\FeishuMirror" --cloud-folder-token "<TOKEN>" --sync-mode download_only --download-value 1 --download-unit days --download-time 01:00 --run-now
python scripts/larksync_cli.py task-create --name "Agent Sync" --local-path "D:\\Knowledge\\FeishuMirror" --cloud-folder-token "<TOKEN>" --sync-mode download_only
python scripts/larksync_cli.py update-status
python scripts/larksync_cli.py logs-sync --limit 20
```

## OpenClaw 集成
- Skill 目录：`integrations/openclaw/skills/larksync_feishu_local_cache/`
- 设计目标：通过 LarkSync 低频同步飞书文档到本地，让 OpenClaw 优先本地检索，减少飞书 API 调用次数。
- WSL helper 已收敛为“诊断 + 安全转发”，不再自动安装依赖或自动拉起后端，降低 ClawHub 安全扫描误报风险。

## License
本项目采用 **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**。  
完整法律文本见 [`LICENSE`](LICENSE) 或官网：<https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode>
