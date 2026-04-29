# LarkSync

<p align="center">
  <img src="assets/branding/LarkSync_Logo_Horizontal_Lockup_FullColor.png" alt="LarkSync Logo" width="520" />
</p>

本地优先的飞书文档同步工具，用于打通飞书云文档与本地文件系统（Markdown/Office）的协作链路。  
当前版本：`v0.6.2-dev.5`（2026-04-29），核心运行形态为托盘常驻 + Web 管理面板。

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
- 任务级 MD 模式：`enhanced` / `download_only` / `doc_only`。
- 删除联动策略：`off` / `safe` / `strict`。
- 设备 + 飞书账号双重归属隔离，避免跨设备串任务。
- 首次授权向导支持从“连接飞书”返回 OAuth 配置页，填错参数可直接修正重试。
- 自动更新检查与更新包下载（sha256 校验）。
- 自动更新支持校验来源回退：优先使用 GitHub Release 资产 `digest`，其后兼容 `.sha256` 文件与 Release 正文中的 sha256。
- 发布流程会同步上传 `.sha256` 资产并写入 Release 正文，兼容旧版本客户端自动更新。
- 更新包下载完成后支持“确认安装”安全流程：用户确认后由托盘延迟接管安装请求，避免前端请求被中断；Windows 端优先使用系统 ShellExecute 直接拉起安装包，失败时再回退 PowerShell，降低“程序退出但安装器未启动”的风险。
- 日志中心与同步状态面板，便于排查同步异常。
- 仪表盘拆分“当前运行”和“最近同步”任务视图，并用真实任务状态展示服务当前是否正在同步，避免启用、运行、最近活动混淆。
- 日志中心重构为任务诊断入口：后端提供任务概览与单任务诊断接口，事件带运行 ID，前端可按任务查看真实运行状态、当前处理文件、问题摘要和事件时间线，并保留系统日志与冲突管理。
- 正式 CLI 入口 `python scripts/larksync_cli.py`：覆盖授权状态、配置、任务、日志、更新、冲突与目录树等核心能力，并提供 `bootstrap-cache` 高层初始化命令、`workflow-template*` 标准工作流模板命令，以及支持恢复执行和运行记录索引化的 `workflow-plan` / `workflow-execute` / `workflow-run-*`，适合 Agent / Skill 自动化调用。
- 内置 OpenClaw Skill 模板：支持“低频同步到本地再本地读取”的降 token 用法。
- 本地持续编辑静默窗口：连续修改同一文档时合并上传，避免重复上云。
- 双向同步的 Markdown 上行会在覆盖云端前复核云端修改时间；若云端相对本地基线已更新，会阻止覆盖并记录冲突，避免本地旧版本覆盖飞书协作版本。
- 冲突管理对同一文件、同一版本差异的未解决冲突做幂等处理，并折叠历史残留的重复未解决记录，避免页面出现两条相同冲突。
- 冲突管理中的“使用本地 / 使用云端”会真正执行一次定向同步：本地优先会强制把当前本地版本上传覆盖云端，云端优先会强制下载当前云端版本覆盖本地；执行失败时冲突不会被提前标记为已解决。
- 自动更新的安装包、状态文件与安装请求会在正式版中落到用户数据目录而不是安装目录；更新后会用当前程序版本重算更新状态，避免安装成功后仍误判“有可更新版本”。
- Windows 自动更新支持静默安装链路：更新请求默认走 NSIS `/S`，托盘会等待外部 helper 确认接管后再退出；helper 负责等待安装器退出、记录 PID/退出码/重启动作，并在安装器未拉起或失败时恢复当前版本；如安装到 `Program Files`，Windows 仍可能弹出 UAC 权限确认。
- 非 MD 文件更新上传自动替换旧云端副本，避免 PDF 等附件多次修改后在飞书侧累积同名重复文件。
- 上传链路自动忽略常见临时文件与系统噪音文件（如 `~$*.docx`、`*.tmp`、`Thumbs.db`），避免本地编辑过程中的临时产物误传到飞书。
- Markdown 上行支持 HTML 内嵌 `data:image/...` 图片：会优先复用本地 `figures/`、`插图/`、`assets/` 中的对应图片资源并带 MIME 上传为飞书图片块，避免飞书前端显示“无法导入该图片”。
- Markdown 图片回填飞书图片块时会按源图像素尺寸写入等比显示宽高，避免空图片块默认尺寸导致插图被横向拉伸。
- Markdown 上行遇到失效的 `fig-数字` 图片相对路径时，会按图号回退查找同级 `figures/`、`插图/`、`assets/` 中的真实源图，避免重命名/迁移后的设计说明书缺图。
- 同步器会忽略 `figures/` 与 `插图/` 这类嵌入源图目录，避免源图被当作独立附件重复上传。
- Markdown 上行检测到飞书块级建表超限时，会自动改走飞书原生 Markdown 导入重建；若同一文档包含本地图片，则优先保留块级上传链路以确保图片进入飞书图片上传。
- 飞书 API 请求会对 429、飞书限频码以及 500/502/503/504 临时网关错误执行指数退避重试，降低 `blocks/convert` 瞬时 502 对同步任务的影响。
- 新建任务或距离上次运行超过 48 小时的任务，会先执行一轮“无删除补齐”：只下载/上传双方缺失的内容并跳过删除墓碑，再进入常规同步，降低首次运行和长时间离线后的误删除风险。
- 删除同步在执行云端删除前会检查同一云端 token 是否仍被其他本地路径使用，并静默程序自身移入 `.larksync_trash` 的文件事件，避免文件移动/回收触发反向误删。
- 云端下载写回本地前会预先静默 watcher，避免程序自己下载文件时又被当成本地修改排进上传队列，反向覆盖刚更新过的飞书文档。
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
