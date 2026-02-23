# CHANGELOG

[2026-02-23] v0.5.44 docs(openclaw-agent): 新增 `OPENCLAW_AGENT_GUIDE.md`（面向 OpenClaw 代理的执行 runbook：检查/初始化/首次授权边界/无人值守兜底/失败处理模板）；并在 `SKILL.md`、Skill README、`docs/OPENCLAW_SKILL.md`、`docs/USAGE.md` 增加入口链接
[2026-02-23] v0.5.44 feat(openclaw,wsl-autonomous): `larksync_wsl_helper.py` 新增无人值守兜底（未探测到可达 `:8000` 时自动在 WSL 本地启动后端，支持自动安装后端依赖）；后端新增 `token_store=file`（`LARKSYNC_TOKEN_STORE=file` + `LARKSYNC_TOKEN_FILE`）以适配无桌面 keyring 环境；补充对应测试与文档
[2026-02-23] v0.5.44 fix(tray,wsl-bridge): Windows 托盘后端默认绑定从 `127.0.0.1` 调整为 `0.0.0.0`（可通过 `LARKSYNC_BACKEND_BIND_HOST` 覆盖），默认 `BACKEND_URL` 仍走 `127.0.0.1` 供本机访问；WSL 诊断与 Skill 文档同步更新排查口径；新增 `test_tray_config.py` 覆盖绑定地址默认值与环境变量覆盖逻辑
[2026-02-23] v0.5.44 feat(openclaw-skill-wsl): 新增 `larksync_wsl_helper.py`，支持 WSL 下多地址探测（localhost / host.docker.internal / default gateway / resolv nameserver）与逐项诊断输出；未指定 `--base-url` 时自动选择可达地址；手动远程 `--base-url` 自动补 `--allow-remote-base-url`；补充对应 pytest 与文档，ClawHub 发布示例更新至 `0.1.3`
[2026-02-23] v0.5.44 docs(openclaw-skill): 补充 OpenClaw Skill 中英双语介绍（`SKILL.md` frontmatter description + 英文概览；README 英文概览）；ClawHub 发布示例版本更新至 `0.1.2`
[2026-02-23] v0.5.44 fix(openclaw-skill-security): `larksync_skill_helper.py` 新增 base-url 安全校验（默认仅允许 localhost/127.0.0.1/::1，远程地址需显式 `--allow-remote-base-url`）；补充对应 pytest；OpenClaw/USAGE 文档同步更新并将 ClawHub 发布示例提升至 `0.1.1`
[2026-02-23] v0.5.44 docs(openclaw,clawhub): 对齐 ClawHub 最新发布规范（`SKILL.md` 的 `metadata` 改为单行 JSON 对象）；上架命令改为 `clawhub login` + `clawhub sync --dry-run` + `clawhub publish <path> --slug --name --version --changelog`；文档术语统一为 ClawHub
[2026-02-23] v0.5.44 docs(openclaw): 强化 OpenClaw Skill 对外介绍文案（价值主张/Before-After/适用人群/30 秒上手），提升可读性与下载意愿；同步更新 Skill 定义与使用指南开场说明
[2026-02-23] v0.5.44 feat(openclaw,docs): 新增 OpenClaw Skill 包（`integrations/openclaw/skills/larksync_feishu_local_cache`）与辅助脚本 `larksync_skill_helper.py`，支持低频下行同步配置/建任务/立即执行；补充 OpenClaw Skill 使用与 clwuhub 上架文档；新增对应 pytest 覆盖核心参数与 payload 构造
[2026-02-19] v0.5.44 fix(ci,release): 默认停用 macOS 自动发布（tag 发布仅构建 Windows）；macOS 改为 workflow_dispatch + `build_macos=true` 手动开启；macOS 工作流产物上传改为非阻塞，降低 upload-artifact 403 对发布流程的影响
[2026-02-19] v0.5.44 feat(release-notes): 新增 `scripts/release_notes.py` 自动从 CHANGELOG 生成 Release 文案；GitHub Release 工作流上传资产时自动附带版本说明（覆盖当前稳定版与上一稳定版之间的全部中间版本条目）
[2026-02-18] v0.5.44 docs(license): 新增 `LICENSE`（CC BY-NC-SA 4.0 legalcode 正文）并在 README 增加许可证说明
[2026-02-18] v0.5.44 docs(readme,usage): README 从极简版调整为完整项目介绍版（补充简介/场景/亮点并保留三份核心文档导读，移除不当“常见问题”）；USAGE 恢复维护者发布教学并与下载安装路径并存
[2026-02-18] v0.5.44 docs(repo): README 精简为公开版（仅保留本地开发与 Release 下载两种快速开始，新增 Logo 与关键文档链接）；USAGE 移除 Git 发布说明；启动器文件（.bat/.pyw/.command）改为 ignore 并停止跟踪
[2026-02-18] v0.5.44 docs(readme,usage): 重构 README 为 GitHub 项目首页格式，补充项目定位/测试/打包/发布/自动更新说明；同步修正文档中的版本与发布示例到 v0.5.44 现状
[2026-02-18] v0.5.44 release: v0.5.44
[2026-02-18] v0.5.43 release: v0.5.43
[2026-02-18] v0.5.43-dev.4 feat(release,update,md-sync): 新增一行稳定版发布命令（自动计算版本/打 tag/push）；自动更新从“仅检查”补全为“可自动下载更新包”；同步任务新增任务级 MD 上传模式（enhanced/download_only/doc_only，默认 enhanced）并接入任务创建与任务管理；修复本地 MD 上云图片路径解析（支持 file://、URL 编码、query/hash）；修复“检查更新”接口响应校验异常并在每次 OAuth 登录后触发一次更新检查
[2026-02-17] v0.5.43-dev.3 fix(sync,task,ui): Markdown 新建 Docx 导入后自动清理同目录源 `.md`，避免云端出现三份文件；新增任务映射约束（同设备同账号下本地/云端一对一，且禁止本地父子目录并行任务）；任务管理页布局优化并增加状态概览卡片
[2026-02-17] v0.5.43-dev.2 fix(ui,sync): 设置页“更多设置”移除删除策略说明卡并重排；任务页删除策略补充行为说明与“分钟”单位；本地/云端删除执行时同步清理 `_LarkSync_MD_Mirror` 中同名 MD 副本；默认本地上传间隔由 2 秒调整为 60 秒
[2026-02-17] v0.5.42 fix(sync,task): 修复本地删除上云失败（云端删除接口改为携带 `type` 参数）；删除策略改为任务级配置（任务可单独设置 `off/safe/strict` 与宽限分钟），设置页移除全局删除策略入口
[2026-02-17] v0.5.42 fix(build): `scripts/build_installer.py` 新增 PYTHONPATH 版本净化（含当前进程与子进程），修复 Python3.14 打包时误混 Python3.12 site-packages 导致的 PyInstaller `numpy/matplotlib` 崩溃
[2026-02-16] v0.5.42 fix(logs,ux): 日志中心新增“所有日志（推荐）”选项并设为默认，查询默认全量状态（包含未来新增状态）；删除相关状态保持默认可见
[2026-02-16] v0.5.41 fix(logs,delete): 日志中心新增删除类目筛选与标签（待删除/删除成功/删除失败）；删除链路失败场景写入 `delete_failed` 同步事件，避免“有删除动作但日志无类目/无记录”
[2026-02-16] v0.5.40 feat(sync,settings): 新增删除同步策略（off/safe/strict）与墓碑宽限机制，补齐本地删除/云端删除联动；上传/下载改为优先使用本地哈希判定变更，减少误判与重复同步；设置页“更多设置”新增删除策略与宽限时间配置
[2026-02-16] v0.5.39 fix(ui,logs): 更多设置保存按钮移动到“展开/收起设置”旁；系统日志默认按最新优先并新增加载失败提示，避免空白页误判
[2026-02-16] v0.5.38 fix(ui,sync,logs): 更多设置拆分独立保存；任务完成率改为 completed/(total-skipped)；日志中心支持状态/任务复选且默认成功失败；新增云端 `_LarkSync_MD_Mirror` 专用目录的 MD 镜像上下行策略（并从下行扫描中排除）
[2026-02-16] v0.5.37 fix(sync,transcoder): 内嵌 sheet 单元格转码补齐 rich segment/mention link/formattedValue/formula 等结构；历史 `sheet_token` 占位文档在“云端未更新”场景下自动回刷重转；新增内部转码测试模板与对应回归用例
[2026-02-16] v0.5.36 fix(ui,transcoder): 设置页将“设备显示名称”迁移到“更多设置”；Docx→Markdown 补齐 `equation`/`add_ons`/`sheet` 转码（公式、mermaid 图与内嵌表格占位），修复生产测试文件夹新增文档同步后内容缺失
[2026-02-16] v0.5.35 fix(tasks,identity,ui): 同步任务改为后端显式 `is_test` 标记（新建任务默认正式任务，不再按名称/路径误判）；侧边栏连接状态改为显示可配置设备名称与飞书昵称；设置页新增“设备显示名称”可编辑项；OAuth 身份补齐同步缓存账号昵称
[2026-02-16] v0.5.34 fix(ui,ops): 侧栏移除“建议手动重新授权”提示文案；按测试需求完成数据库归档与新用户态切换（归档旧库并清空本地 token），用于隔离历史数据影响
[2026-02-16] v0.5.33 fix(auth,owner): OAuth token 缺失 open_id 时自动调用 authen/v1/user_info 补齐并持久化；/auth/status 自动修复身份字段；任务列表改为严格“设备ID+open_id”双重匹配并仅安全迁移本机路径任务；停止数据库启动时将历史空设备ID任务批量回填为当前设备
[2026-02-16] v0.5.32 fix(ui,identity): 同步任务路径展示改为“默认后半段 + 点击展开换行”，移除突兀白色路径框；连接状态文案明确区分“已连接但账号/设备ID未补齐”并给出重新授权提示
[2026-02-16] v0.5.31 fix(ui,docs): 测试任务显隐按钮仅在开发/测试模式且存在测试任务时显示；同步任务空态文案按模式区分；README/USAGE 同步更新并补充托盘不显示排查指引
[2026-02-16] v0.5.30 fix(ui,tray): 同步任务长路径改为可滚动展示并防溢出；测试任务按钮仅在存在测试任务时显示；登录引导页支持明暗主题且默认明亮；设备/账号状态文案完善；托盘启动增加运行时 PYTHONPATH 自清理并输出依赖错误详情
[2026-02-16] v0.5.29 fix(ui,auth,owner): 修复授权向导首屏闪现与侧栏压缩；任务页默认隐藏测试任务；任务归属强化为设备+账号并补齐设备标识透出
[2026-02-16] v0.5.28 fix(dev,test): `npm run dev` 启动后端时自动过滤不兼容 `PYTHONPATH`；修复 sync_runner/tray_status/logging/backend_manager 回归用例并恢复后端全量测试通过
[2026-02-16] v0.5.28 fix(core): 修复版本读取正则与空 refresh_token 还原；飞书文档同步脚本兼容改版页面并落清单；自动更新新增 sha256 校验；统一根/前端/后端版本；本地测试规范明确为 npm run dev + 打包体验测试
[2026-02-10] v0.5.27 feat(sync): 双向模式下默认关闭 MD→飞书文档上传，新增 upload_md_to_cloud 开关；更多设置可控
[2026-02-10] v0.5.26 feat(sync): SyncLink 新增 cloud_parent_token 字段记录云端父目录；前端"更多设置"新增"重置同步映射"维护工具
[2026-02-10] v0.5.25 fix(sync): 上传时按本地子目录结构在云端自动创建对应文件夹，修复所有文件上传到根目录的问题；新增 reset-links API 用于修复已错位的同步映射
[2026-02-10] v0.5.24 fix(sync): 双向同步首次调度时全量扫描未链接本地文件，修复模式切换后已有文件不上传；NSIS 安装器支持覆盖安装、卸载保留用户数据选项、中文界面
[2026-02-09] v0.5.23 fix(oauth): 回退至飞书 v1 OAuth 端点（app_id/app_secret），修复 drive 权限丢失；侧边栏令牌状态改为"自动续期中"
[2026-02-09] v0.5.22 fix(oauth): scope URL 编码修复 + drive 权限诊断 + 权限不足前端引导提示
[2026-02-09] v0.5.21 fix(oauth): 授权 URL 恢复 scope 参数，修复用户授权后缺少 drive/docs 权限
[2026-02-09] v0.5.20 fix(keyring): 拆分 token 存储，解决 Windows 凭据管理器 2560 字节限制导致 CredWrite 失败
[2026-02-09] v0.5.19 fix(error): 全局异常处理器，500 错误返回详细错误信息而非裸 Internal Server Error
[2026-02-09] v0.5.18 fix(oauth): refresh_token 改为可选，兼容飞书 v2 端点响应格式
[2026-02-09] v0.5.17 fix(oauth): 修正飞书 OAuth 端点为 v2 标准协议，修复 code=20003 错误
[2026-02-09] v0.5.16-hotfix docs(oauth): 修正 OAUTH_GUIDE 回调地址示例错误
[2026-02-09] v0.5.16 fix(oauth): OAuth 默认端点、redirect_uri 修正与引导向导完善
[2026-02-09] v0.5.15 feat(ui): 首次使用引导向导与弹窗定位优化
[2026-02-09] v0.5.14 fix(ui): 新建任务弹窗定位修复
[2026-02-08] v0.5.13 fix(build): 安装包支持完成后启动、Windows 图标与后端启动修复
[2026-02-08] v0.5.12 fix(build): 修复版本读取正则并简化 NSIS 路径定义
[2026-02-08] v0.5.11 fix(ci): 修正 NSIS 预处理指令拼写，避免构建失败
[2026-02-08] v0.5.10 fix(ci): NSIS 编译期校验输出，避免安装时误判缺失
[2026-02-08] v0.5.9 fix(ci): macOS DMG 识别 .app 路径并缺失即失败
[2026-02-08] v0.5.8 fix(ci): NSIS 打包路径校验与版本读取增强，确保安装包可生成
[2026-02-08] v0.5.7 fix(ci): NSIS 路径补齐，构建缺失安装包时直接失败
[2026-02-08] v0.5.6 fix(ci): Release 构建上传安装包资产并校验产物存在
[2026-02-08] v0.5.5 fix(ci): PyInstaller 运行时注入项目根路径，避免 __file__ 缺失
[2026-02-08] v0.5.4 fix(ci): Windows 下自动解析 npm 可执行文件
[2026-02-08] v0.5.3 fix(ci): 修复 Windows 构建脚本控制台编码导致的崩溃
[2026-02-08] v0.5.2 fix(ci): 修复版本校验正则，确保 Release 构建可读取版本
[2026-02-08] v0.5.1 fix(ci): 修复 Release Build 工作流 YAML 语法
[2026-02-08] v0.5.0 release: 打包/安装包、CI 构建、自动更新稳定版检查与下载
[2026-02-08] v0.5.0-dev.6 feat(update): 自动更新检查、下载与设置接入
[2026-02-08] v0.5.0-dev.5 feat(ci): GitHub Releases 自动构建并上传 Windows/macOS 安装包
[2026-02-08] v0.5.0-dev.4 feat(package): macOS .app bundle 与 DMG 打包流程补齐
[2026-02-08] v0.5.0-dev.3 feat(installer): 新增 NSIS 安装脚本与打包参数
[2026-02-08] v0.5.0-dev.2 feat(package): 补齐 PyInstaller spec 与打包资源路径，支持 bundle 前端/图标
[2026-02-08] v0.5.0-dev.1 feat(data): 运行数据目录支持用户目录，便于安装版隔离
[2026-02-08] v0.4.0-dev.21 docs(plan): 升级计划迁入本地文档目录并细化自动更新设计
[2026-02-08] v0.4.0-dev.20 fix(test,plan): 托盘状态回归测试补齐，升级计划新增自动更新
[2026-02-08] v0.4.0-dev.19 fix(db,shutdown): 托盘优雅关闭后端 + SQLite WAL/超时设置，降低损坏风险
[2026-02-08] v0.4.0-dev.18 fix(startup): SQLite 损坏自动备份重建，避免启动超时
[2026-02-08] v0.4.0-dev.17 fix(logs,db): 同步映射异常降级，日志保留与提醒设置
[2026-02-08] v0.4.0-dev.16 fix(export,logs): 表格导出轮询增强，日志中心自动刷新
[2026-02-08] v0.4.0-dev.15 fix(logs,export): 同步日志持久化与系统日志读取修复，表格导出补齐子表 ID
[2026-02-08] v0.4.0-dev.14 fix(export,logs): 表格导出补齐 sub_id 获取，系统日志读取根路径修复
[2026-02-08] v0.4.0-dev.13 fix(sync-download): 表格导出 sub_id 重试、日志历史排序、上传后避免回流下载
[2026-02-08] v0.4.0-dev.12 fix(sync-download): 云端未更新时跳过下载，在线幻灯片类型不导出
[2026-02-08] v0.4.0-dev.11 feat(export): 支持在线幻灯片导出为 pptx
[2026-02-08] v0.4.0-dev.10 fix(export): 导出任务查询携带文档 token 并增强错误信息，修复共享表格导出 400
[2026-02-08] v0.4.0-dev.9 fix(sync-download): 支持 sheet/bitable 导出下载、非法文件名自动净化、日志读取改为流式并保留历史
[2026-02-08] v0.4.0-dev.8 fix(ui): 共享链接说明补充“非所有者共享需使用链接/Token”
[2026-02-08] v0.4.0-dev.7 feat(ui): 新建任务支持粘贴共享链接/Token 选择云端目录
[2026-02-08] v0.4.0-dev.6 feat(drive): 目录树支持共享文件夹根节点与快捷方式展开，新增共享目录选择
[2026-02-08] v0.4.0-dev.5 fix(ui): Logo/Favicon 去除白色背景改为透明底色；侧边栏 Logo 去除边框容器直接融入背景(h-9)；Favicon 改为透明背景自适应浏览器主题；新增 scripts/process_logo.py 图片处理工具；亮色主题 bg-zinc-950/80 适配
[2026-02-08] v0.4.0-dev.4 fix(tray/ui): /tray/status 接入冲突统计，托盘检测未解决冲突时提示；新增 tray 状态接口回归测试；前端侧边栏产品 Logo 放大并增加阴影以提升可读性
[2026-02-07] v0.4.0-dev.3 refactor(tray): 统一托盘模式为唯一运行方式；tray_app.py 新增 --dev 参数（Vite HMR 3666 + uvicorn --reload 8000 + 托盘一体化启动）；npm run dev 改为调用 tray --dev；删除旧 scripts/dev.js 开发脚本；删除 Docker 部署文件（Dockerfile/docker-compose.yml/nginx.conf）；backend_manager 支持 dev_mode 热重载；全部文档统一为托盘模式说明
[2026-02-07] v0.4.0-dev.2 fix(tray): 端口冲突智能复用 + 单实例锁 + BAT 简化为纯启动器；SPA fallback 修复 dist 根目录静态文件（logo/favicon）；品牌 Logo 集成（托盘4状态变体 + favicon + 侧边栏横版Logo）；开发/生产模式 URL 自动检测
[2026-02-07] v0.4.0-dev.1 feat(desktop): 系统托盘桌面化 — pystray 托盘应用（启动/停止/菜单/状态轮询/图标变色）；FastAPI 静态文件服务（前后端一体化）；一键启动器 LarkSync.pyw/command；系统通知 plyer；开机自启动（Windows Startup/macOS LaunchAgent）；PyInstaller 打包配置；构建脚本 build.py/build_installer.py；后端新增 /tray/status 聚合接口
[2026-02-07] v0.3.0-dev.6 feat(ui): 日志中心页码分页重构（同步日志+系统日志）；新建 Pagination 通用分页组件；仪表盘日志面板增加条数+总数+查看全部入口；后端 /sync/logs/file 接口改为分页返回（offset+total）；自定义滚动条适配明/暗主题；docx_service 频率限制（99991400）增加指数退避延迟重试
[2026-02-07] v0.3.0-dev.5 feat: SyncTask 增加 cloud_folder_name 字段显示云端目录名；新增 /sync/logs/file API 读取 loguru 日志文件；日志中心新增「系统日志」标签展示完整历史日志
[2026-02-07] v0.3.0-dev.4 fix(ui): 非仪表盘页面移除独立 Header，主题切换融入各页面头部区域；OAuth 教程页支持明亮/深色主题切换
[2026-02-07] v0.3.0-dev.3 fix(ui): Header 改为仪表盘完整banner+其他页轻量工具栏；弹窗去掉 backdrop-blur；明亮模式同步策略卡片配色修复；新增 OAuth 配置教程页面（静态 HTML + 新标签打开）
[2026-02-07] v0.3.0-dev.2 fix(ui): Header 精简非仪表盘页面冗余信息；明亮模式按钮悬浮色修复；同步策略页面卡片化重设计；新建任务弹窗分步指示器优化；Redirect URI 改为自动生成+复制；云端 token 显示截短；主题切换移至侧边栏
[2026-02-07] v0.3.0-dev.1 feat(ui): 前端 UI/UX 全面重构 — 架构拆分为 pages/components/hooks/lib 分层；引入 TanStack Query 替代原始 fetch；新增 Toast 通知系统与确认弹窗；新建任务改为分步向导；冲突解决添加 Keep Both 按钮；字体切换 Inter + JetBrains Mono；色板对齐 Zinc + Lark Blue；移除 CSS !important hack；新增 WebSocket 实时日志流、骨架屏与空状态引导组件
[2026-02-06] v0.2.0-dev.2 feat(ui): 任务页重构 + 明亮主题按钮对比度优化；feat(config): 同步策略支持秒/小时/天；docs: 更新 OAuth/使用/同步逻辑说明
[2026-02-04] v0.1.36-dev.24 chore(docs): 新增飞书文档同步脚本并固化到协作规范
[2026-01-31] v0.1.36-dev.23 docs(agents): 增加飞书开发文档下载/更新规范
[2026-01-31] v0.1.36-dev.22 feat(sync): Markdown 新建 Docx 自动创建云端文档
[2026-01-30] v0.1.36-dev.21 fix(transcoder): 任务/提及/提醒渲染 + 容器块 children 透传
[2026-01-30] v0.1.36-dev.20 fix(sync): 块级状态重建与表格 cells 展开 + 创建子块参数校正
[2026-01-30] v0.1.36-dev.19 fix(sync): 局部更新锚点检测与重复签名保护
[2026-01-30] v0.1.36-dev.18 fix(sync): 局部更新表格子块 + 自动降级策略
[2026-01-30] v0.1.36-dev.17 feat(sync): 同步日志时间线 + 时间戳修正 + 表格上传补丁
[2026-01-30] v0.1.36-dev.16 fix(dev): Windows 下 dev 启动避免 spawn EINVAL
[2026-01-30] v0.1.36-dev.15 fix(db): SQLite 迁移默认值改为字面量
[2026-01-30] v0.1.36-dev.14 feat(dev): npm run dev 输出落盘到 dev-console.log
[2026-01-30] v0.1.36-dev.13 feat(ui): 同步任务支持更新模式配置
[2026-01-30] v0.1.36-dev.12 fix(docx): Markdown 图片占位单次转换 + 表格清洗
[2026-01-30] v0.1.36-dev.11 fix(docx): 图片占位后上传 + 表格子块修正
[2026-01-30] v0.1.36-dev.10 feat(sync): Markdown 上行局部更新（块级差异）
[2026-01-30] v0.1.36-dev.9 fix(sync): 创建子块失败时自动拆分定位无效块
[2026-01-29] v0.1.36-dev.8 fix(sync): 上行日志补全与转码根块规整
[2026-01-29] v0.1.36-dev.7 fix(sync): 文档覆盖先创建后删除 + 同步日志补充
[2026-01-29] v0.1.36-dev.6 feat(logging): 新增运行日志系统
[2026-01-29] v0.1.36-dev.5 fix(sync): 上传图片路径修正与缺图跳过
[2026-01-29] v0.1.36-dev.4 fix(docx): 上传缺图自动跳过并回退 token
[2026-01-29] v0.1.36-dev.3 fix(docx): 图片下载失败兜底
[2026-01-29] v0.1.36-dev.2 chore(repo): 忽略 data 运行数据目录
[2026-01-29] v0.1.36-dev.1 fix(docx): 修正 Markdown 转换接口路径
[2026-01-29] v0.1.35-dev.1 fix(sync): 上传预映射与附件下载兜底
[2026-01-29] v0.1.34-dev.1 feat(sync): 双向任务上传与链接/附件本地化
[2026-01-28] v0.1.33-dev.1 fix(transcoder): 完善 Docx 转码列表/引用/代码/待办等块解析
[2026-01-28] v0.1.32-dev.1 fix(sync): 解析快捷方式 token 并展示失败原因
[2026-01-28] v0.1.31-dev.1 fix(sync): 文档解析补偿与跳过未支持类型
[2026-01-28] v0.1.30-dev.1 feat(sync): 下载任务执行/状态/删除
[2026-01-28] v0.1.29-dev.1 fix(auth): 更新默认权限 scope 与文档说明
[2026-01-28] v0.1.28-dev.1 feat(ui): 同步任务支持目录选择器 + 明亮主题
[2026-01-28] v0.1.27-dev.1 fix(auth): 回调后自动跳转回前端
[2026-01-28] v0.1.26-dev.1 fix(auth): token 异常转为可读错误
[2026-01-28] v0.1.25-dev.1 fix(auth): token 请求使用 app_id/app_secret
[2026-01-28] v0.1.24-dev.1 docs(oauth): 明确向导字段来源与步骤
[2026-02-17] v0.5.43-dev.1 fix(sync-delete): 删除墓碑失败项纳入自动重试队列（5 分钟退避），云端“已删除”按幂等成功处理；旧任务空删除策略回退全局默认，避免显示与执行不一致
[2026-01-28] v0.1.23-dev.1 fix(auth): Token 请求改为 JSON 体
[2026-01-28] v0.1.22-dev.1 docs(oauth): 详细配置向导说明 + 忽略本地密钥配置
[2026-01-28] v0.1.21-dev.1 fix(auth): 兼容飞书 Token 包装响应
[2026-01-28] v0.1.20-dev.1 docs(oauth): 完善 OAuth 配置指南与向导说明
[2026-01-28] v0.1.19-dev.1 feat(config): 网页配置 OAuth 参数向导
[2026-01-28] v0.1.18-dev.1 fix(auth-db): 登录错误返回 400 + 启动时初始化数据库
[2026-01-28] v0.1.17-dev.1 fix(dev): npm run dev 使用 python -m uvicorn
[2026-01-28] v0.1.16-dev.1 feat(ui): 手动上传 Markdown 入口
[2026-01-28] v0.1.16-dev.1 fix(vite): 修正 /api 代理正则
[2026-01-28] v0.1.15-dev.1 feat(sync-task): 同步任务配置向导与冲突持久化
[2026-01-28] v0.1.14-dev.1 feat(docx-image): Markdown 图片上传与使用教程文档
[2026-01-27] v0.1.13-dev.1 feat(docker): 生产 Dockerfile 与 Nginx 反向代理
[2026-01-27] v0.1.12-dev.1 feat(conflict): 冲突检测接口与前端冲突中心
[2026-01-27] v0.1.11-dev.1 feat(upload): 非 MD 文件上传与 SyncMapping 记录
[2026-01-27] v0.1.10-dev.1 feat(docx-upload): Markdown 转 Docx 全量覆盖与指数退避重试
[2026-01-27] v0.1.9-dev.1 feat(watcher): 本地监听与 WebSocket 事件推送
[2026-01-27] v0.1.8-dev.1 feat(download): 非在线文档下载与本地落盘
[2026-01-27] v0.1.7-dev.1 feat(writer): 本地写入与 mtime 同步
[2026-01-27] v0.1.6-dev.1 feat(transcoder): Docx 转 Markdown 与图片落盘
[2026-01-27] v0.1.5-dev.1 feat(crawler): 递归目录树获取与前端展示
[2026-01-27] v0.1.4-dev.1 feat(auth): OAuth 登录、令牌存储与前端连接页
[2026-01-27] v0.1.3-dev.1 feat(release): 新增 release 脚本与版本归档日志
[2026-01-27] v0.1.2-dev.1 fix(security): 升级 vite 修复 esbuild 漏洞；统一 SyncMapping 字段与版本格式
[2026-01-27] v0.1.1-dev.1 feat(config-db): 新增配置中心与 SyncMapping 模型
[2026-01-27] v0.1.0-dev.2 fix(repo): 添加 .gitignore 并移除误提交的缓存文件
[2026-01-27] v0.1.0-dev.1 feat(scaffold): 初始化 monorepo 结构与前后端脚手架
[2026-02-04] v0.1.36-dev.25 fix(sync-upload): 修复 Markdown 上行的列表续行/附件挂载与多行渲染，云端回归差异显著收敛
[2026-02-04] v0.1.36-dev.26 fix(sync-link): 下载链路合并已同步映射，链接仅在本地文件存在时改写为相对路径
[2026-02-04] v0.1.36-dev.27 fix(sync-watcher): 修复本地监听上传参数缺失导致的批量 failed
[2026-02-04] v0.1.36-dev.28 fix(sync-upload): 自动迁移 Markdown 的历史 file 映射为 Docx，并在 partial 失败时回退全量覆盖
[2026-02-04] v0.1.36-dev.29 fix(sync-partial): 双向下载跳过本地较新文件 + 飞书频控码 99991400 自动重试，修复本地修改不上云
[2026-02-04] v0.1.36-dev.30 fix(sync-partial): 自动补齐缺失块状态并去重同名云端文件，修复“本地较新未上云”与重复映射漂移
[2026-02-06] v0.1.36-dev.31 fix(transcoder): 表格单元格列表换行与层级缩进、催办文本解析增强；前端端口改为 3666
[2026-02-06] v0.1.36-dev.32 fix(transcoder): 标题块子级内容渲染，修复“催办”下待办未同步
[2026-02-06] v0.1.36-dev.33 fix(sync-partial): 块级映射不一致自动重建基线；前端端口强制固定
[2026-02-06] v0.1.36-dev.34 fix(watcher): moved 事件去抖/静默以 dest_path 为准，修复本地改动未触发上传；docs(sync): 补充同步逻辑说明
[2026-02-06] v0.1.36-dev.35 feat(schedule): 本地变更 2 秒周期上传 + 云端每日 01:00 下载；修复 dev 退出后端口占用
[2026-02-06] v0.1.36-dev.36 feat(ui): 侧边栏仪表盘重构，任务/冲突/设置分区与日志面板
[2026-02-06] v0.1.36-dev.37 fix(ui): 修复 JSX 文本解析错误，新增明亮主题与主题切换
[2026-02-06] v0.2.0-dev.1 feat(ui): 日志中心改造与任务简洁视图；OAuth 配置简化 + 配置指南页面
