# LarkSync

<p align="center">
  <img src="assets/branding/LarkSync_Logo_Horizontal_Lockup_FullColor.png" alt="LarkSync Logo" width="520" />
</p>

本地优先的飞书文档同步工具：把飞书云文档稳定同步到本地 Markdown / 文件系统，同时保留继续在飞书协作的工作方式。
当前稳定版本：`v0.9.1`（2026-09-01）。核心运行形态为 Windows / macOS 桌面壳 + 托盘或菜单栏常驻。
当前代码基线：`v0.9.2-dev.1`。

## 快速入口

| 你要做什么 | 入口 |
| --- | --- |
| 直接试用 | [下载最新版安装包](https://github.com/gooderno1/LarkSync/releases) |
| 首次安装和创建任务 | [快速开始](docs/QUICK_START.md) |
| 配置飞书开放平台 | [OAuth 配置指南](docs/OAUTH_GUIDE.md) |
| 了解数据边界 | [安全与隐私说明](docs/SECURITY_AND_PRIVACY.md) |
| 在正式版旁安全测试 v0.8 | [真实数据安全测试指南](docs/REAL_DATA_TESTING.md) |
| 遇到问题 | [反馈与排障指南](docs/FEEDBACK.md) / [FAQ](docs/FAQ.md) |

## 适合谁

- 飞书重度用户：需要把云端协作文档沉淀到本地目录、NAS 或长期知识库。
- Obsidian / VS Code 用户：希望把飞书 Docx 同步成可检索、可版本化的 Markdown。
- AI Agent 用户：希望先把飞书内容低频缓存到本地，再让 OpenClaw 等工具高频读取本地文件。
- 需要双向工作流的个人或小团队：本地编辑、云端协作、多设备同步同时存在。

## 3 分钟试用路径

第一次试用建议从低风险的 `download_only` 模式开始，只同步一个小型飞书测试目录。

1. 从 [GitHub Releases](https://github.com/gooderno1/LarkSync/releases) 下载 Windows 安装包或对应架构的 macOS DMG。
2. 启动 LarkSync，在首次使用页点击“开始扫码连接”；应用注册与账号授权由 LarkSync 按官方 `lark-cli` Device Flow 协议原生完成。
3. 按 [快速开始](docs/QUICK_START.md) 创建 `download_only` 任务，把少量文档同步到本地。若组织禁止自动创建个人应用，可从高级入口手动填写 App ID / App Secret 后扫码。
4. 在「活动管理」确认同步事件，并在「问题中心」查看需要处理的问题，再决定是否扩大目录或启用双向同步。

## 界面预览

![LarkSync 同步状态与最近运行结果](assets/promotion/log-center-success.png)

## 核心能力

- v0.9.0-dev.1 原生接入官方 `lark-cli` v1.0.92 验证过的 App Registration 与 OAuth Device Flow：安装后可直接用手机扫码，桌面端轮询官方端点取得 Token，不再依赖手机回调桌面 `localhost`，也不要求用户安装 CLI。
- 支持多个飞书/Lark 账号同时登录和同步。左侧账户切换器显示各账户未读消息与同步错误；任务、运行、映射、冲突、问题、通知、Token 与刷新锁均按 `account_id` 隔离。
- v0.9.1 按账号记录 `legacy_v1` / `device_v2` 认证协议：升级账号继续使用 V1 兼容端点刷新，不会因 access token 到期中断；重新授权成功后才原地升级为 Device Flow V2，后续启动不会被旧全局凭据覆盖。
- v0.9.2-dev.1 将完整 Token 包编码后按 900 个 ASCII 字符分片写入 Windows 凭据管理器，以版本化活动清单做原子切换并校验长度与 SHA-256；超长 V2 Token 不再触发 `CredWrite 1783`，写入或数据库提交失败时回退旧凭据，v0.9.1 分字段格式和更早合并格式继续自动兼容。
- 设置页提供账号切换、手动刷新授权、原账号重新授权、暂停/恢复、断开本机和软移除。重新授权保留原 `account_id`、任务、状态和历史；扫码身份不一致时拒绝覆盖。暂停只停止该账号的调度，不影响其他账号。
- 新版本首次启动会向仍使用 V1 兼容授权的账号发送一次通知，明确说明兼容模式仍可继续使用，并提供“立即重新授权”直达入口。
- 自动创建个人应用采用连续两步状态机：第一次扫码成功后由同一会话响应直接携带第二次账号登录会话，不再轮询已结束会话或要求退出重来；已有应用和手动 App ID/Secret 复用同一账号登录步骤。
- 从 v0.8 升级时自动执行 schema v9：升级前创建 SQLite 在线备份，原任务、运行、问题、映射和凭据自动归入原账号；安全存储写入成功后才从 `config.json` 清除旧明文 App Secret。正常升级不需要手动迁移。
- v0.8.24-dev.1 将开机自启动纳入“设置 → 当前设备”：页面直接读写 Windows Startup 快捷方式或 macOS LaunchAgent，并在操作后回读系统状态。托盘菜单改为“打开、立即同步、活动与问题、设置、更多、退出”的原生层级，使用原生勾选态，并移除只改变托盘图标、不暂停后端的误导性“暂停同步”。真正跨设备扫码登录的 HTTPS 回调中继 + PKCE 方案见 [设计说明](docs/design/v0.8.24-settings-tray-qr-login-plan.md)。
- v0.8.23 修复问题中心“重试任务”成功后仍等待定时扫描：手动运行会按任务同步模式映射恢复方向，双向任务成功可同时验证上传和下载，单向任务只验证自身方向；升级后已有的成功手动重试也能作为恢复证据自动结案。
- v0.8.22 修复“下载异常已恢复但问题中心仍未结案”：数据库按任务与上传/下载方向分别保存后台检测结果，同方向后续扫描即使没有文件变化也可作为恢复事实，反方向扫描不会误结案；飞书文件清单异常同时保留错误码、HTTP 状态与请求 ID，便于后续精确定位服务端故障。
- v0.8.21-dev.1 修复文件或目录移动后的旧路径上传竞态：监听器会撤销源路径及其子项队列并排队新位置，执行中已消失的源文件记为跳过而不是失败；问题中心按上传/下载方向采信后续成功扫描，即使本轮全是未变化跳过项也能自动结案，并一次性排除历史完成汇总对异常次数的污染。无文本异常会显示异常类型，不再生成空白错误。
- v0.8.20-dev.4 将 Apple Developer 凭据改为可选：未配置时正式 Release 仍会生成经过 ad-hoc 签名和安装 smoke 的 macOS arm64、x86_64 DMG；凭据六项齐全时自动启用 Developer ID、notarization、stapling 和 Gatekeeper 校验。无公证版本首次打开需在 macOS「系统设置 → 隐私与安全性」选择「仍要打开」。
- v0.8.20-dev.3 增加 macOS 正式发布凭据解阻工具：在本机交互读取 Developer ID P12 密码和 Apple 应用专用密码，通过标准输入写入六项 GitHub Actions Secrets，不把敏感值写进文件或命令参数；`Release Build`手动凭据预检模式可在当前发布分支验证 Developer ID 私钥可签名、时间戳服务可用以及`notarytool`公证账户有效，正式发布命令缺少任一 Secret 时会在改版本、提交或打 Tag 前停止，并同步冻结前端 lockfile 版本元数据。
- v0.8.20-dev.2 补齐 macOS App/Finder/Dock/DMG 与菜单栏图标、响应式 OAuth 引导和二维码状态、Cocoa 窗口恢复、现代 LaunchAgent、原生通知与 Keychain/WKWebView 安装验收；正式 DMG 强制 Developer ID 签名、Apple notarization、stapling 和 Gatekeeper 校验。
- v0.8.20-dev.1 修复内嵌 Sheet 转码失败后的周期性重复下载：历史 `sheet_token` 占位仅针对同一云端文档版本和同一转码迁移版本回刷一次；若回刷后仍为占位，后续内容未变化的扫描按正常规则跳过，云端更新时间或转码迁移版本变化后才重新尝试。
- v0.8.19 正式补齐 v0.8.18 的历史问题迁移：未解决或已忽略的问题只要最新证据严格匹配`完成: total=N ok=N failed=N skipped=N`运行汇总，就自动以`workflow_summary_not_problem`结案并保留原始活动证据；扫描同时兼容已被旧迁移改成`task_run`且分类器已是 v3 的记录，真实下载、认证和对象错误不会被误结案。
- v0.8.18 正式修复飞书刷新凭据 `20026` 的跨进程重复失败：刷新前重读系统凭据并通过跨进程锁串行轮换，只有观察到新 Token 才安全恢复，确实失效时明确提示重新连接；问题中心保留真实认证错误并过滤空汇总误报，更新安装前确认旧桌面与后端完全退出。
- v0.8.18-dev.1 修复多进程共用飞书凭据时旧 `refresh_token` 被重复使用并触发 `20026`：刷新、授权交换、身份补齐和退出登录统一通过跨进程锁串行化，刷新前强制从系统凭据库重读；只在确认凭据已被其他进程轮换时改用新值重试，凭据确实失效则明确提示重新连接。任务级真实错误会在运行汇总前单独入库，问题中心不再把 `failed=0` 的完成汇总识别为下载问题；更新安装也会先确认桌面与后端完全退出，避免安装期间残留旧进程继续刷新凭据。
- v0.8.17 正式修复 Windows 托盘唤醒窗口后仍被其他应用遮挡：已有窗口恢复时获得跨进程前台权限，并以原生激活和一次性临时置顶回退确保本次打开位于最上层；回退完成后立即解除 TopMost，不影响后续正常窗口层级。
- v0.8.17-dev.1 修复 Windows 托盘唤醒窗口后仍被其他应用遮挡：托盘进程会把前台激活权限授予 WebView 子进程，窗口宿主恢复后显式置前；若系统仍拒绝激活，则仅在本次唤醒中临时置顶并立即解除，不会把 LarkSync 设为永久 TopMost。
- v0.8.16 正式发布自然高度双栏：设置页主栏依次放置账号与设备、默认同步策略和折叠 OAuth，辅助栏放置忽略规则与数据保护；更新与维护页按`3:2`承载版本安装与本机维护。两页取消强制满高、等高、内部滚动和底部锚定，正常桌面窗口保持双栏，逻辑宽度低于`900px`时才回退单栏。
- v0.8.16-dev.2 完成上述业务页面实现、响应式回归测试与 1280×720、1080×720、860×720 隔离预览。
- v0.8.16-dev.1 完成对应设计：设置页收敛为“主栏配置 + 380–420px 辅助栏”，更新与维护页取消强制等高、满高和底部锚定；两张最新版 imagegen 设计图已归档。
- v0.8.15 正式发布设置与更新维护页的默认窗口尺寸修正；正式版自动更新可通过 GitHub Latest Release 获取 Windows NSIS 与 macOS 双架构安装包。
- v0.8.15-dev.1 设置页取消左右独立滚动与强制满高外框，辅助栏固定为 380–420px，OAuth 凭证默认真正折叠；默认窗口下页面无需滚动。更新与维护页使用标题区加剩余工作区两行布局，双主面板等高延伸至内容区底部，消除原先约 200 逻辑像素的页面底部留白。
- v0.8.14 实装维护页 v3：左侧`版本与安装`、右侧`本机维护`使用顶底对齐的双主面板；检查更新回归版本模块，自动更新与日志配置分别保存，安装详情按安装活动、失败或未确认状态自动展开，危险任务按需展开。更新按钮按`up_to_date / available / downloaded / error`状态显示，不再在已是最新时保留无意义的禁用按钮。1080×720 和 1360×900 隔离预览均无横向溢出或内部双滚动。
- v0.8.14-dev.3 继续只做设计：设置页 v2 保持不变；更新与维护页从“左右两组独立堆卡”收敛为“版本与安装｜本机维护”两张顶底对齐的主面板。安装详情折叠在左主面板底部，危险操作以单层风险语义锚定右主面板底部；已是最新时不再显示禁用的下载、安装按钮。标准与紧凑两张 v3 imagegen 设计图已归档，业务页面仍未修改。
- v0.8.14-dev.2 继续只做设计：设置页固定为“账号设备与同步策略｜忽略规则、OAuth 与数据保护”，维护页固定为“版本安装｜日志与危险操作”。1080×720、1360×900 和宽屏均保持相同双栏，只由 1360 设计画布整体缩放或增加留白；仅在逻辑宽度低于约 900px 时提供单栏安全兜底。四张 v2 imagegen 设计图已更新，业务页面仍未修改。
- v0.8.14-dev.1 仅完成设计：设置与更新维护页统一为一套信息架构、单栏/双栏两种排布；取消少量表单的双独立滚动，检查更新归回版本模块，自动更新从日志管理移回更新模块，空闲安装详情默认折叠，忽略规则改为摘要加独立管理入口。四张 imagegen 设计图已归档，等待确认后再开发。
- v0.8.13 撤销设置与更新维护页在 v0.8.12 引入的 `1240px` 居中窄版，统一为“固定页头 + 满高工作区 + 主/侧栏独立滚动”。设置页账号、设备、同步策略和 OAuth 表单按实际列宽重新排布；维护页恢复页头主操作和 `360px` 维护侧栏。两页均以真实后端只读数据在 1360×900、1920×1080 下完成截图复核。
- v0.8.12 将活动详情查询收敛到 `run_id` 索引，避免同时携带任务条件后扫描百万级任务历史；Watchdog 只接收创建、修改、移动和删除事件，内存中的瞬时上传排队不再写入活动历史。旧 `queued` 记录原样保留并移至“历史排队”，默认“处理结果”只显示可审计事实。问题中心可正确打开任务目录，标准/宽屏事件详情改为可用 Esc 或遮罩关闭的居中弹窗。
- v0.8.11 修复代码目录中零字节标记文件触发“文件大小不能为空”并导致整轮上传失败：零字节普通文件现在保留本地内容并明确记为跳过，不伪造 1 字节文件。问题分类器升级为 v3，具体对象问题结合运行方向分类，任务完成汇总只保留在活动管理；旧任务汇总和旧零字节失败会保留证据后自动结案。更新下载参考 Codex Companion 增加检查、下载、校验、完成和失败阶段，实时展示百分比、已下载/总大小与速度，并使用 `.part` 临时文件和 SHA256 校验后的原子替换。
- v0.8.10 将活动管理标准模式调整为顶部任务下拉框、左侧运行记录和右侧具体事件；全局字阶从 `11/12/13/14px` 提升到 `12/13/14/15px`，控件高度、事件行高和响应式栏宽同步配适。问题中心通过 schema v6 实装单条忽略与恢复：忽略必须填写原因，不等同于解决，证据和动作历史继续保留；同指纹失败保持忽略，出现严格匹配的后续成功事实时自动转为已解决。
- v0.8.9 通过 schema v5 归档旧版“先记录待删、同轮又确认云端对象仍存在”的历史运行；只有全部待删事件都能严格匹配“cloud / cancelled / 云端文件已恢复”墓碑、且没有任何真实传输或错误事实时才隐藏，原始运行、事件和墓碑仍保留。
- v0.8.8 修复大历史库活动详情筛选对索引列使用 `coalesce/lower` 导致的全量扫描；下载扫描在建立 cloud missing 墓碑前先用完整云端 token 集合确认对象存在，避免“待删后立即恢复”的重复空活动；问题后台按任务停用、授权/运行恢复、当前忽略规则和上传目标已消失等可审计证据收敛旧问题，仍存在且没有恢复证据的错误继续保留。
- v0.8.7-dev.1 为上传和下载分别持久化调度检查点，升级后不再立即执行尚未到期的全量检查；周期上传先按 `local_size/local_mtime` 过滤无变化触碰，未到期删除墓碑不触发运行，同一待删除事实只记录一次。schema v4 通用重分类所有用户历史中的纯空成功运行；活动摘要补充“删 / 待删 / 删失败”，飞书返回 `not found. token=...` 时按删除幂等成功收敛。
- v0.8.6-dev.1 针对大历史库升级后的长时间卡顿增加启动热修复：问题中心首次建立 `problem_event_cursor_v4` 实时基线，保留旧历史断点但不再自动追赶数万条历史事件；已有 SQLite 事件时，重复 JSONL 回填直接对齐文件尾，原始 JSONL 继续保留。实时问题批次从 250 降至 20，且只加载本批失败指纹涉及的问题；游标或日志维护准备异常会降级到后台处理，不再阻断桌面启动。
- v0.8.5-dev.1 将问题中心页面查询与历史问题处理彻底分离：页面只读已持久化问题，后台按持久游标每批处理 250 条失败或恢复事件，不再构造数千路径条件扫描 250 万事件表。活动标准模式只保留左侧任务列表和一个运行选择器，默认展示全部真实活动；旧版无动作检查归档保留但不进入默认列表和统计。活动与问题页面分别显示加载、失败和真实空状态，接口异常不再显示为 0 条。
- v0.8.4-dev.1 修复活动页存在事件却显示为空：任务切换不再关闭事件查询，默认运行选择最近的真实活动，时间范围使用最后事实时间。无变化检查改为每任务一行的检测摘要，历史空运行默认不进入活动列表。问题中心使用解决键匹配同任务、同对象、同操作族的后续成功事件自动结案，后续失败可重新打开；`delete_pending` 作为正常安全等待状态退出未解决问题队列。
- v0.8.1 完成桌面页面逐页配适：总览摘要卡压缩图标与留白，任务表格在 1080×720 最小窗口保留统计与操作列，活动页四项摘要改为 2×2 并禁止筛选标签竖排；首次引导三栏和任务详情右侧检查器改为独立滚动，避免低高度窗口裁切内容；顶栏账号区同步释放可读宽度。
- v0.8.2 修复托盘已有窗口无法恢复的问题：关闭按钮隐藏窗口但保留宿主，托盘双击会恢复、导航并置前同一窗口；桌面子进程使用轻量入口并取消固定启动等待。正式版默认后端端口迁移到 `18765`，减少与常用开发端口冲突。
- v0.8.3-dev.3 将活动管理 / 问题中心的紧凑、标准、宽屏布局细化为可验收规格，补齐断点滞回、低高度降级、筛选与选中迁移、实时更新、加载/空/异常、键盘焦点和长文本策略。复核后废弃活动紧凑 v2 的五列表格/半屏详情，以及问题标准 v2 的标题操作同排结构；新增六张 v3 设计图。当前条目只完成方案与设计，不代表页面和问题状态机已经实装。
- v0.8.3 实装活动管理与问题中心：活动页读取全部任务并按任务、运行、时间、类型和关键字分页审计事件；紧凑态使用双行列表与整页详情，标准态使用任务/事件两栏，宽屏态使用任务/运行/事件三栏。问题中心新增统一问题、出现记录和动作记录，按稳定指纹合并同步失败与冲突，服务端返回真实 `available_actions`，动作完成后必须通过源冲突终态或后续成功运行验证；历史问题在后台按 1000 条分批回溯，避免拖慢桌面启动。
- 桌面版优先完成 API 和首屏渲染：日志维护延后 20 秒并把 JSONL 清理移入工作线程；自动同步延后 12 秒，任务按 0.75 秒错峰且最多同时运行 2 路。运行摘要继续串行写入，首次本地扫描使用单次映射查询并在线程中遍历目录，避免大型历史库和多任务在启动时冻结界面。
- Windows 桌面壳默认窗口与设计画布为 `1360x900`，常规尺寸保持 1:1 渲染，大窗口不继续放大，小于设计画布时才按比例缩放到 `1080x720` 下限；界面使用本机系统 UI 字体和带配套行高的 `12/13/14/15px` 四级字阶，侧栏、顶栏、运行卡、控件高度和正文留白同步适配。
- 飞书授权状态只回答本机“已授权 / 未授权”，不在启动检查中刷新 Token、补用户资料或请求飞书 Drive；真实 API 调用仍会按需刷新 Token 并返回明确业务错误。扫码回调只等待必需的 Token 交换和安全存储，用户昵称在首屏稳定 2 秒后异步补齐，登录后的更新检查延后 5 秒。
- 总览页生产数据态只展示真实运行任务、未解决冲突和已采集指标；日志未提供数据量、耗时或连接延迟时明确显示 `—` / `未采集`，零传输事件显示空状态。设计样例仅在开发环境显式访问 `?ui-demo=dashboard` 时启用。
- 总览页侧栏固定常驻，不提供含义不明确的折叠入口；右侧“优先处理 / 任务状态 / 今日传输”与主区三层严格对齐，并移除与顶栏重复的立即同步、任务管理及与侧栏重复的连接状态。次级文字、表格字重和面板边框已提高对比度；右上账号区提供明确的账户菜单，可进入“账号与授权”和“更新与维护”。
- 同步任务页按原始浅色设计恢复 8 行高密度任务表：搜索、状态、模式、健康筛选与唯一主操作位于同一工具栏；本地路径允许两行阅读，三种同步模式使用独立色彩，状态与健康拆为两层信息，运行、启停、详情和三点设置保持固定顺序；开发环境默认使用稳定演示数据，`?ui-data=live` 可切回真实数据，生产环境始终使用真实后端数据；三点任务设置使用独立居中弹窗并通过一次保存提交全部变更。
- 新建任务采用五步单页向导：每次只显示当前决策，右侧常驻展示目录、模式、删除策略和风险等级；未完成本地/云端目录选择时不可越级，首次创建默认使用低风险的仅下载模式。
- 独立任务详情页恢复原始浅色设计：固定使用“同步任务 / 任务名称”面包屑和“任务详情”标题，主列完整展示任务身份、本地与云端关系、当前或最近运行、5 条运行历史；右侧 300px 依次保留问题摘要、任务操作、策略摘要、忽略目录和常驻危险操作五张独立卡片。同步关系区使用“电脑端点—LarkSync 品牌 Logo—云端端点”；品牌图按原图 214×97 的完整有效像素显示，并以文字、图标和按钮的实际渲染边界校准视觉中心，1536/1440/1280 三档左右间距误差不超过 0.4px；对称连接线箭头保留。任务表中的项目名称与右侧文件夹按钮均可进入详情。详情页“编辑策略”复用任务表三点按钮的居中设置弹窗，本地目录通过后端接口调用系统文件管理器打开；开发演示任务可直接进入详情，`?ui-data=live` 切换真实数据。
- 活动管理按物理窗口切换三档布局：标准态使用顶部任务选择器，下方为 296px 运行记录与事件工作区；宽屏态保持任务/运行/事件三栏；紧凑态使用任务/运行两个选择器和 68px 双行事件列表。事件详情支持复制并携带任务、运行、事件标识跳转问题中心。
- 问题中心统一展示同步失败、删除异常、中断和内容冲突，并以“对象问题 / 任务异常 / 内容冲突”标签区分层级；任务完成汇总留在活动管理但不重复生成问题。页面支持状态、分类、严重级别、任务、时间与关键字筛选以及服务端分页。标准态为问题队列与诊断工作台，宽屏态增加独立动作栏，紧凑态使用列表/详情主从切换；真实修复动作由后端能力决定，人工忽略必须填写原因且可恢复，不提供伪单文件重试或批量忽略。
- 设置页将账号与当前设备合并为同一上下文区，默认同步策略、OAuth 等修改统一由页面右上角一次保存；更新与维护页仅保留一个更新检查入口，并将重置同步映射的任务列表默认收起。
- 活动、冲突、设置和维护页在开发环境默认使用带“前端演示数据”标识的完整数据态，占满桌面工作区并覆盖典型问题、冲突、规则和更新场景；首屏列表按完整卡片容量收敛并提供剩余数量提示，设置与维护内容重新分区，避免卡片被壳层遮挡；使用 `?ui-data=live` 可切换到真实后端数据，生产构建始终使用真实数据。
- 桌面壳按统一信息架构重组：228px 侧栏负责导航、后端/飞书状态、最近同步、版本和维护入口；56px 顶部命令栏只显示任务范围、立即同步、任务管理和账号入口；职责重复的全局底部状态栏已删除。Windows 原生标题栏继续保留系统缩放、贴边布局、窗口菜单和无障碍能力，并使用 `#EAF2F8` 标题背景、`#24364F` 文字和 `#B9CBE0` 边线形成克制的冷色层次；六个核心页面已完成三档边界与控制台复核。
- 飞书 Docx 与本地 Markdown 双向同步，图片会下载到本地 `assets/` 并以相对路径引用。
- 任务级同步模式：`enhanced` / `download_only` / `doc_only`，首次试用推荐 `download_only`。
- 删除联动策略：`off` / `safe` / `strict`，避免首次运行或长时间离线后的误删除。
- 事件管理统一展示待删除、失败、取消和冲突事件，并会把 `forbidden`、云端镜像目录创建失败、Docx 块写入失败和删除目标不存在解释成具体问题；冲突仍支持“使用本地 / 使用云端”定向解决。
- 活动管理按任务和运行记录查看上传、下载、删除、跳过、失败、待删除和冲突事件；问题中心集中完成诊断、证据查看、冲突决策、任务重试和后续验证。
- Windows 桌面壳已接入统一浅色科技风导航与命令栏，以及总览工作台、表格化同步任务页、独立任务详情页、活动与问题、冲突处理、设置和更新维护入口。
- OAuth token 本地保存，支持自动续期；详见 [安全与隐私说明](docs/SECURITY_AND_PRIVACY.md)。
- 设置、维护、任务和新建向导统一使用同一语义开关组件，轨道内留有固定边距，修复开机自启动与自动更新开关圆点越界。
- macOS 安装版提供专用 `.icns` 应用图标和深浅色自适应菜单栏 Template 图标；首次授权页在窄窗口自动切为单列，明确区分“需要配置、生成中、二维码可用、生成失败”四种状态。
- macOS PR 与无 Apple 凭据的正式构建会用 ad-hoc 签名执行 Bundle、Keychain 与 LaunchServices/Cocoa 启动阶段 smoke；交互式 Mac 直接验证 WKWebView，GitHub 托管 Mac 在 App 自身进入`webview_starting`后依赖独立 Linux headless Playwright WebKit 门禁验证相同首屏。配置完整 Apple 凭据后，正式 Release 自动增加 Developer ID、notarization、stapling 和 Gatekeeper 校验，详见 [macOS 发布与验收](docs/operations/macos-release.md)。
- 内置 CLI 和 OpenClaw Skill 模板，适合 Agent / 自动化工作流读取本地飞书缓存。
- 新增 `production`、`synthetic_test`、`snapshot_test`、`live_readonly`、`live_bidirectional` 五类运行配置档；测试配置使用独立端口、实例锁、数据目录和 Token Store，桌面侧栏常驻显示非生产环境标识。
- 新增正式数据库 SQLite online backup 脱敏快照、快照配置校验和只读查询基准脚本；快照会停用全部任务、终止遗留 `running`、重映射本地路径、伪名化云端 Token，并且不导出 keyring 凭据。
- 飞书请求统一经过全局令牌桶和 429/5xx 指数退避；真实只读配置按 endpoint 语义拒绝云端写入，专用双向配置要求任务根目录命中 allowlist，并可输出不含 Authorization、请求正文和 URL 查询参数的 JSONL 请求审计。

## 当前边界

- v0.9 起首次授权二维码承载 Device Flow 的`verification_uri_complete`，手机确认后由桌面端轮询官方 Token 端点闭环；旧版`localhost` OAuth 授权码流程仅保留为兼容入口。
- 非 Markdown 文件已支持“先上传新文件、再清理旧的同名云端副本”；该流程不能保持旧文件 Token 不变，若旧副本清理失败会保留最新映射并记录警告，需要在专用测试目录完成真实回归后再扩大使用范围。
- 在线文档内嵌 `sheet` 优先转 Markdown 表格；权限不足、接口异常或超限时会回退为 `sheet_token` 占位。同一云端文档版本和转码迁移版本最多强制回刷一次，避免占位无法消除时被每轮重复计为下载；云端更新或转码能力升级后会再次尝试。
- 文档内附件块若字段结构与当前样例不同，需要提供 docx blocks JSON 样例后继续完善解析。
- 双向同步会修改云端或本地内容。首次试用请使用测试目录或 `download_only` 模式。

<details>
<summary>近期工程化与同步细节</summary>

- 飞书 Docx 与本地 Markdown 双向同步。
- 超长 Docx 全量回写在根块子节点接近飞书上限时，会自动将过多一级块压缩为透明容器，并在必要时先最小化删除尾部旧块腾位，避免 `too many children in block (1770007)` 导致整段内容被误跳过。
- Docx 全量替换在根块已接近上限时，透明容器块现会写入合法的零宽字符段落；若创建过程中途失败，也会回滚本轮刚插入的顶层块，避免一次失败把云端文档越写越大并持续触发 `invalid param`。
- Markdown 上行现在会跳过 fenced code 中的图片/附件示例，不再把代码示例里的 `![...]()` 误当成真实资源上传；若历史链路仍产出空 code block，也会在发往飞书前自动补零宽占位，避免 `block_type=14` 空 `elements` 触发 `1770001 invalid param`。
- 默认 OAuth 权限说明与本地配置已切换到新版 Docx scopes：新环境会直接要求 `docx:document` / `docx:document.block:convert`，历史 `docs:doc` 配置会在运行时自动迁移，减少首次授权后仍缺文档权限的问题。
- OAuth 自动续期链路已串行化 refresh；若飞书 token 响应未返回新的 `refresh_token`，会保留当前已存值，降低并发续期触发 `code=20026` 或误清空本地 refresh token 的风险。
- 云端文件下载写回本地时，若目标文件被 WPS/Office 等进程占用，会短暂重试，并在日志里明确提示“目标文件正被其他程序占用，请关闭后重试”。
- 任务级 MD 模式：`enhanced` / `download_only` / `doc_only`。
- 删除联动策略：`off` / `safe` / `strict`。
- 文件夹会作为同步对象持久化映射；本地删除已同步文件夹会删除对应飞书文件夹并清理子映射，云端文件夹删除会按删除策略移动或删除本地目录。
- 设置页支持“默认忽略隐藏/缓存路径”开关：默认会跳过所有以 `.` 开头的文件或目录以及 `__pycache__`；同时仍可按任务配置“双向忽略目录”，单独排除 `node_modules`、构建产物或其他自定义子目录。
- 设备 + `account_id` 双重归属隔离；同一设备可让多个账号并行同步，切换界面账户不会停止其他账号的后台任务。
- 仪表盘改为同步健康总览，优先展示本地与飞书是否一致、待处理事件、失败与冲突，以及最近成功同步结果。
- 仪表盘现在会把 `待删除` 与同步队列分开说明：`delete_pending` 表示安全删除宽限队列，到期后自动执行，不再被写成待上传。
- 仪表盘主内容区改为更保守的宽屏两列触发条件，任务路径和事件消息会自动换行，降低中等宽度窗口下的卡片拥挤和路径溢出。
- 仪表盘整体外壳在宽屏下与左侧边栏同高；顶部 Header 固定在外壳内，“任务概览”和“需要关注”共享剩余高度并各自内部滚动，中等宽度仍保持自然纵向布局。
- 任务卡片默认聚焦“本地目录 ↔ 飞书目录”的同步关系与健康摘要，工程字段收进任务管理详情。
- 事件管理保留冲突处理队列，支持连续为多条冲突选择“使用本地 / 使用云端”；前端会明确显示“已排队 / 处理中 / 等待任务空闲 / 已完成 / 处理失败”，并通过单 worker 严格串行提交请求，对“任务运行中”的冲突处理自动重试，避免连续点击时并发打到后端。
- 事件管理改为和任务诊断一致的排障工作台：顶部选择任务，左侧选择同步运行进程，右侧展示该进程的具体问题、原因、建议动作和原始事件；左侧进程列表和右侧问题详情都具备独立滚动边界。
- 事件管理中的同一同步进程支持多类问题并列展示：运行卡片会显示“问题类型数 / 事件数”，右侧会按问题类型拆分多张详情卡。
- 事件管理默认只展示需关注事件，普通上传、下载、跳过和完成日志默认隐藏；用户可切换“显示全部事件”做完整审计。
- 事件管理会把增强 MD 模式下 `_LarkSync_MD_Mirror` 创建 forbidden、Docx `blocks/children` 写入 forbidden、删除目标 not found 分别识别为“镜像目录权限”“文档写入权限”和“删除状态已失效”，避免只显示笼统待处理数量。
- 事件管理配色收敛为中性工作台 + 状态胶囊，只有失败、冲突和待删除等状态使用小面积提示色，避免整页被警告/成功色块占满。
- 活动与问题页、任务运行摘要和任务卡片现在会明确展示 `删除 / 待删除 / 删除失败` 等删除链路状态，不再只显示上传/下载。
- 活动与问题页任务诊断默认只显示有上传、下载、删除、待删除、失败、冲突或正在运行的任务；全 0 无动作任务会折叠隐藏，并可在任务选择区切换显示全部。
- 任务管理页的任务卡不再只显示笼统的“待处理”数量，而会展开为 `队列 / 待删 / 删失败 / 失败 / 冲突` 的组成，并说明每一类对应的处理方式。
- 桌面化总览页改为 v3 浅色科技风布局：摘要卡、主列“正在运行/最近同步”和右侧处理轨分层展示；当前桌面壳使用 1360x900 设计画布，常规窗口 1:1 呈现，最小窗口按 1080x720 等比缩放，同时 shell 反向占满 viewport，避免外层白边。
- 同步任务页提供独立任务详情入口；任务详情页采用主列 + 右侧 300px 五张独立卡片，运行中显示当前进度，已完成显示“最近一次运行”，从未运行时不显示误导性的 0% 进度环；本地目录按钮调用 `/sync/tasks/{task_id}/open-local-folder` 打开任务配置中的真实目录。
- 新建任务向导由五列同屏改为五步单页结构，正文采用“当前步骤 + 280px 配置摘要”；删除策略改为三张可比较卡片，启用状态使用标准语义开关，底部每一步只保留一个主操作。
- 桌面壳内的页面适配参考 codex-companion 的固定画布缩放方法：左侧栏固定 228px、顶部命令栏固定 56px，总览、任务、任务详情、活动与问题、冲突处理、设置、更新维护和首次授权页均保持同一设计结构，再由外层画布统一缩放；大窗口不再居中露出背景边。
- 桌面壳新增 `/system/desktop/status` 聚合状态接口，为侧栏运行摘要和顶部任务范围提供后端运行、OAuth、任务、冲突、更新和最近同步数据；端口、数据库和进程等诊断字段只在更新与维护页按需查看，托盘 `/tray/status` 继续保持旧字段兼容。
- 托盘启动后优先打开 pywebview/WebView2 桌面窗口；关闭窗口时改为隐藏到托盘，双击托盘或选择设置/活动入口会通过本机回环控制通道恢复、导航并置前已有窗口，不再重复冷启动 WebView；桌面子进程使用轻量快速入口且不再固定等待 0.4 秒；若桌面宿主不可用，仍会自动回退浏览器入口。
- 正式版默认后端端口由常见的 `8000` 迁移到专用端口 `18765`，仍可通过 `LARKSYNC_BACKEND_PORT` 覆盖；OAuth 旧本地回调会迁移到 `18765`，升级后重新授权前需在飞书应用安全设置中登记 `http://localhost:18765/auth/callback`。
- “活动管理 / 问题中心”改版暂不改页面代码，详细职责边界、数据口径、交互、性能和验收方案见 `docs/design/v0.8.2-activity-problem-center-plan.md`。
- 开发期新增 `npm run dev:test` 隔离测试入口，默认使用 `18000` 后端、`13666` 前端、独立单实例锁和项目内 `data/dev-test` 测试数据目录，可在安装版运行时查看桌面化开发效果，避免影响安装版实例。
- `npm run dev:test` 会校验已有后端的数据目录；若默认 `18000` 指向其他测试目录，会自动切换到后续可用后端端口，并让 Vite 代理跟随，避免桌面测试页误连旧库。
- 项目内 `data/dev-test` 可放置隔离历史样例数据，用于在不影响安装版和默认网页版本的情况下审查真实数据态页面。
- 桌面总览页已按真实数据态继续对齐 v3 设计稿：统计卡高度、主表格行高、模块间距和右侧上下文栏密度进一步收紧。
- 桌面总览页新增设计到工程契约与模块审计口径；摘要卡图标语义、长值显示、运行表速度列、样例冲突卡和实时连接折线已按 `03-dashboard-light-v3.png` 继续收敛，并保留 1080/1440/1536/1920 截图证据。
- 首次授权页接入桌面聚合状态，展示窗口宿主、后端、前端资源、运行模式和数据目录；扫码授权完成后会轮询进入桌面壳，并保留当前 hash 路由。
- 首次授权页新增 `lark-cli auth status --json --verify` 只读状态探测，展示 CLI 安装、用户身份和 docs/drive scope 检测结果；该入口只做辅助诊断，不导入 CLI token，也不在前端暴露 open_id。
- 更新与维护页会读取真实 `install-request.json` 和 `install-handoff.json`，保守展示校验、托盘接管、helper、静默安装和自动重启阶段，不把未确认状态写成成功。
- 活动与问题页切换任务时，任务概览和运行摘要优先读取 `sync_runs` 摘要表；旧任务即使暂时没有 `sync_runs` 摘要，也不会在概览切换时回退扫描 `sync-events.jsonl`，只有真正打开事件/问题明细时才按需读取大日志。
- `sync_run_events` 事件持久化层会将同步事件双写到 SQLite 与 `sync-events.jsonl`，后台按 checkpoint 持续回填/追平旧日志；任务诊断、问题列表和事件时间线优先读取数据库，回填未完成时才受控回退 JSONL。
- 更新安装、重置同步映射和删除任务等高风险维护动作统一使用浅色应用内确认框，明确说明影响范围。
- 首次授权向导支持从“连接飞书”返回 OAuth 配置页，填错参数可直接修正重试。
- 设置页已收敛为 `OAuth / 同步策略 / 设备显示名 / 本地忽略目录`；自动更新、日志保留和同步映射重置统一放在更新维护页，避免桌面端配置入口重复。
- 任务页与“新建任务”向导已拆成独立浅色卡片/步骤组件，并将路径摘要、任务健康、手动云端目录解析和创建 payload 组装下沉为可测试 helper，便于继续治理任务管理流程。
- 任务表格三点按钮打开独立“任务设置”弹窗：任务表不再插入行内面板或改变高度；弹窗右侧实时展示变更数量和风险，原先四个独立“应用”已合并为单次组合 PATCH，删除任务收进默认折叠的维护操作；存在未保存修改时，关闭或按 `Escape` 会先提示是否放弃。
- 后端 `sync_tasks` 接口已抽出独立的请求/响应模型与任务诊断/同步日志服务层，任务 CRUD、任务诊断和日志查询的边界开始收口，便于继续拆解剩余的大型后端模块。
- `sync_runner` 的云端父目录解析、MD 镜像目录查找/创建、目录缓存与导入后文档探测逻辑已下沉到独立 `SyncCloudFolderService`，主同步 runner 正在从“巨型总控器”收口为组合服务。
- `sync_runner` 的删除墓碑、本地回收目录、删除映射清理与云端幂等删除判断逻辑已下沉到独立 `SyncDeleteSyncService`，主同步 runner 继续朝“编排层 + 专项服务”结构收口。
- `sync_runner` 的 Markdown 云端文档导入/重导入、导入源文件清理、同名旧文档清理与新建文档时间戳兜底逻辑已下沉到独立 `SyncMarkdownCloudDocService`，上传链路开始从主 runner 中剥离。
- `sync_runner` 的下载候选构建、表格/多维表格 `sub_id` 补齐、导出任务轮询、导出文件下载和候选去重逻辑已下沉到独立 `SyncDownloadSupportService`，下载链路开始从主 runner 中剥离。
- `docx_service` 的 Markdown 资源占位与回填逻辑已下沉到独立 `DocxMarkdownAssetService`，本地图片、HTML 图片、附件链接和 placeholder 替换开始从文档服务主类中剥离。
- `docx_service` 的表格运行时逻辑已下沉到独立 `DocxTableRuntimeService`，大表格降级、单元格回填和插行补足开始从文档服务主类中剥离。
- `docx_service` 的块级局部更新 diff、重复签名规避与锚点匹配逻辑已下沉到独立 `DocxPartialUpdateService`，文档服务主类进一步向“飞书文档 API 编排层”收口。
- `docx_service` 的子块创建、失败拆分重试、图片/附件回填逻辑已下沉到独立 `DocxBlockCreateService`，主类开始从“内容替换执行器”收口为更薄的文档编排层。
- `docx_service` 的内容替换、`convert -> create` 写入编排与 Markdown 块插入逻辑已下沉到独立 `DocxContentWriteService`，文档服务主类继续向“API 能力集合 + 薄编排层”收口。
- `docx_service` 的 Markdown convert 前后 continuation/placeholder 处理已下沉到独立 `docx_markdown_convert_helper.py`，Markdown 预处理与块文本修补开始从文档服务主类中剥离。
- `sync_runner` 的上传全量扫描、按路径上传批次、运行时服务组装与失败归档逻辑已下沉到独立 `SyncUploadOrchestrationService`，上传主编排开始从同步 runner 中剥离。
- `sync_runner` 的下载树扫描、候选筛选、写回循环、删除联动前置判定与运行时服务组装已下沉到独立 `SyncDownloadOrchestrationService`，下载主编排开始从同步 runner 中剥离。
- `sync_runner` 的上传路径分发、通用文件上传与旧云端文件清理逻辑已下沉到独立 `SyncPathUploadService`，单文件上传细节开始从主 runner 中剥离。
- `sync_runner` 的 Markdown 上传主编排已下沉到独立 `SyncMarkdownUploadService`，冲突校验、块级状态、同 token 覆盖与导入重建回退开始从主 runner 中剥离。
- `transcoder` 中的块类型常量、`DocxParser` 与解析辅助逻辑已下沉到独立 `docx_parser.py`，`transcoder.py` 继续兼容导出原入口，转码编排与块解析职责正式分层。
- `transcoder` 的内嵌 sheet 预览转码、表格矩阵裁剪和 add-ons 文本块渲染已下沉到独立 `transcoder_sheet_helper.py`，表格/附加块渲染开始从主转码器中剥离。
- `tray_app` 的 Windows 安装脚本构造、PowerShell helper 启动参数与静默安装 bootstrap/worker 文本模板已下沉到独立 `windows_install_helper.py`，托盘主入口继续保留兼容函数名，但安装链路开始从主托盘文件中剥离。
- Windows 开机自启动现已区分开发态与打包态入口：开发态快捷方式优先指向受版本控制的 `apps/tray/launcher.py`，安装版直接指向当前 `LarkSync.exe`，托盘启动时还会自动修复旧的失效快捷方式，避免菜单显示“已启用”但实际开机不拉起。
- macOS 安装版链路已补齐：更新包版本识别同时支持 `LarkSync-Setup-*.exe` 与 `LarkSync-*.dmg`，LaunchAgent 会在开发态使用受版本控制的 `launcher.py`、在打包态直接启动 `.app` 内可执行文件，托盘后端日志统一落到用户数据目录，避免安装到 `/Applications` 后继续回写应用目录。
- GitHub Release 正式版 tag 现会默认同时构建 Windows `exe` 与 macOS `dmg`，减少发布时漏传 mac 安装包的风险；仅手动重跑工作流时才允许按需跳过 mac 构建。
- 安装版托盘管理面板固定打开后端 `18765` 提供的生产静态页面；`3666` 仅保留给显式 `--dev` 的 Vite 热重载开发模式，避免本机仍有开发服务运行时新安装版误打开测试页面。
- GitHub Actions 现额外在 PR / `main` 非 tag 场景执行 macOS 定向后端回归 + 打包 smoke，尽量把 `.app` / `dmg` 与 LaunchAgent / 更新链路问题提前暴露，而不是等到正式发布时才首次发现。
- macOS CI 现已进一步补齐安装/启动级 smoke：构建出 DMG 后会自动挂载镜像、显式校验卷内 `Applications` 安装入口、复制 `.app` 到临时安装目录，并直接启动 bundle 内 `LarkSync --backend` 做 `/health` 检查；若启动超时或提前退出，会回抛 bundle stdout/stderr 与 `larksync.log` 尾部，并将默认等待时间提高到 60 秒，避免 GitHub runner 上再次出现“只知道 Connection refused、不知道为什么没起来”的黑盒失败。
- 后端运行时现在将 `greenlet` 作为显式依赖声明，安装包构建也会显式打入该模块，避免 Python 3.14 arm64 等环境里 `sqlalchemy.ext.asyncio` 初始化数据库时因上游不再自动携带 `greenlet` 而直接崩溃，导致安装后启动 smoke 卡在 `/health` 之前。
- macOS 双架构 CI matrix 现已显式关闭 `fail-fast`：即使某个架构先失败，另一个架构的构建与安装 smoke 也会继续跑完，避免 Intel 结果再次因为 arm64 的先发失败被 GitHub 自动取消。
- macOS 打包现默认按当前 runner 原生架构出包，并在 Intel `macos-15-intel` (`x86_64`) 与 Apple Silicon `macos-14` (`arm64`) runner 上分别做日常 smoke；正式版 tag 会上传双架构 DMG，更新服务会优先选择与当前机器架构匹配的安装包。
- 自动更新检查与更新包下载支持真实阶段和进度：下载时显示百分比、已下载/总大小和速度，下载完成后单独显示 SHA256 校验；安装包先写入 `.part` 临时文件，校验通过后再原子替换为可安装文件。
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
- Windows 静默安装 helper 的启动参数现在支持分级回退：优先尝试 `CREATE_BREAKAWAY_FROM_JOB`，若受限环境拒绝再回退到普通隐藏进程组；`python scripts/update_install_smoke.py` 会记录实际采用的 `creationflags` 与回退日志，降低受限环境下 smoke 和真实静默安装一起卡死在 helper 启动阶段的风险。
- PyInstaller 打包现在使用仓库自定义 hooks，显式排除未使用的 `pydantic.v1` 与 FastAPI 对其的静态兼容导入，避免 Python 3.14 构建日志继续出现 `Core Pydantic V1 functionality isn't compatible` 噪音，并确保产物分析结果不再携带 `pydantic.v1` 命名空间。
- 发布构建环境固定为 `Python 3.14.x + Node 25.x`；`python scripts/build_installer.py` 会在非基线环境下 fail fast，并输出完整构建环境摘要，避免“本地能打包、CI/正式版环境不一致”的漂移问题。
- FastAPI 应用生命周期已切换为 `lifespan`，统一管理数据库初始化、watcher、同步调度、更新调度和日志维护后台服务的启动与关闭顺序。
- SQLite 初始化已升级为显式 schema version 迁移流程：`init_db()` 会顺序执行迁移注册表并将当前版本写入 `sync_meta.schema_version`，旧库升级路径可以通过自动化测试稳定验证。
- 前端质量门补齐 `eslint + vitest` 页面级 smoke 回归，覆盖 App、总览、任务页、活动与问题、冲突处理、设置和维护页的基础挂载与关键壳层文案。
- 桌面版诊断入口已从旧 `LogCenterPage` 收敛为独立的「活动与问题」和「冲突处理」页面；旧日志中心页面、旧暗色 panel 组件、分页/骨架/空态死代码已移除。
- 冲突处理队列状态机独立为 `useConflictResolutionQueue`，相关状态统计与状态文案判断沉淀到可测试 helper，页面不直接维护队列 ref 和重试状态流转细节。
- 活动与问题页继续复用 `useLogCenterTaskDiagnostics`、`useTaskDiagnosticsSelection` 和 `useTaskEventTimeline` 等诊断 hook；这些 hook 只负责查询与选择状态，不再绑定旧日志中心视图组件。
- 诊断 query 的 `include_problems` 判断、URL 参数组装、轮询间隔、概览排序、`runAlert` 和展示派生状态已沉到 `taskDiagnosticsQuery` / `taskDiagnosticsState` 等 helper，并保留独立测试。
- 新增 `python scripts/update_install_smoke.py`，可在 Windows 上用真实 PowerShell bootstrap/worker 链路验证静默安装接管是否能推进到目标 handoff 阶段。
- 更新检查会保留已校验且版本、大小、sha256 匹配的安装包路径，避免下载完成后再次检查把 `download_path` 清空，造成页面误判为尚未下载。
- 设置页更新区新增“打开安装包目录”，静默安装失败时可直接打开下载目录手动排查或重试安装。
- 静默安装接口会拒绝“当前版本或更旧版本”的重复安装请求，避免升级其实已成功、再次点击却只看到无效安装的误判。
- Windows 托盘会忽略“安装包版本小于等于当前运行版本”的过期静默安装请求，避免安装成功后因残留请求再次触发自更新，表现成打不开或反复重启。
- 活动与问题页与同步状态面板，便于排查同步异常。
- 运行详情的事件时间线支持按 `上传 / 下载 / 删除 / 问题 / 跳过 / 实际变更` 分别筛选，便于单独查看不同同步动作。
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
- Markdown 上行解析本地图片和附件链接时会正确处理文件名中的括号，避免 `blocks/convert` 收到残缺图片语法后返回 400 并跳过图片上传。
- Markdown 图片回填飞书图片块时会按源图像素尺寸写入等比显示宽高，避免空图片块默认尺寸导致插图被横向拉伸。
- Markdown 上行遇到失效的 `fig-数字` 图片相对路径时，会按图号回退查找同级 `figures/`、`插图/`、`assets/` 中的真实源图，避免重命名/迁移后的设计说明书缺图。
- 同步器会忽略 `figures/` 与 `插图/` 这类嵌入源图目录，避免源图被当作独立附件重复上传。
- Markdown 上行遇到超限表格时，会优先保留一张原生飞书表格：创建阶段先按飞书建表上限建立初始行，再通过表格行插入补齐剩余行，避免把 V1.5 这类长表拆成多张表；列宽按 Markdown 文档顺序匹配并覆盖飞书转换器的窄默认值，常见多列表格以 732 偏好总宽为目标，贴近飞书原生云文档默认表格宽度，短列保留最小宽度、长文本列按内容权重分配剩余空间，同时保留整表上限防止横向滚动；单元格内容写入后会清理默认空段落，避免内容被空行顶到下方；既有云端文档缺少当前表格渲染修复标记时，即使本地内容 hash 未变化，也会跳过局部 diff 并在原 doc token 内全量重建。
- 飞书 API 请求会对 429、飞书限频码以及 500/502/503/504 临时网关错误执行指数退避重试，降低 `blocks/convert` 瞬时 502 对同步任务的影响。
- 新建任务或距离上次运行超过 48 小时的任务，会先执行一轮“无删除补齐”：双向模式先冻结补齐前已存在的本地文件清单，再由云端优先完成下行，仅对冻结清单执行无删除上行；补齐下行同时禁止刷新云端 Markdown 镜像，同轮刚下载的 Markdown、附件和镜像不会被误判为本地修改后回传。补齐阶段跳过删除墓碑，再进入常规同步，降低首次运行、长时间离线和文件 Token 无意义替换的风险。
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

</details>

## 快速开始

### 方式 1：直接下载安装包（面向使用者）
- 打开发布页：<https://github.com/gooderno1/LarkSync/releases>
- Windows 下载 `LarkSync-Setup-*.exe`
- macOS 下载与你机器架构匹配的 `LarkSync-*.dmg`
- 首次试用请继续参考 [快速开始](docs/QUICK_START.md)

### 方式 2：本地开发
```bash
npm install
cd apps/frontend && npm install
cd ../backend && python -m pip install -r requirements.txt
cd ../..
npm run dev
```

启动后：
- 前端：`http://localhost:3666`
- 后端：`http://localhost:18765`

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

## 文档导航（建议先读）
- 快速开始：[`docs/QUICK_START.md`](docs/QUICK_START.md)
- 使用文档：[`docs/USAGE.md`](docs/USAGE.md)
- OAuth 配置：[`docs/OAUTH_GUIDE.md`](docs/OAUTH_GUIDE.md)
- 安全与隐私：[`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md)
- 反馈与排障：[`docs/FEEDBACK.md`](docs/FEEDBACK.md)
- FAQ：[`docs/FAQ.md`](docs/FAQ.md)
- OpenClaw / AI Agent 本地缓存教程：[`docs/OPENCLAW_LOCAL_CACHE_GUIDE.md`](docs/OPENCLAW_LOCAL_CACHE_GUIDE.md)
- 同步逻辑：[`docs/SYNC_LOGIC.md`](docs/SYNC_LOGIC.md)
- 发布标准：[`docs/RELEASE_STANDARD.md`](docs/RELEASE_STANDARD.md)
- v0.8.14 设置与更新维护页信息架构设计：[`docs/design/v0.8.14-settings-maintenance-information-architecture-design.md`](docs/design/v0.8.14-settings-maintenance-information-architecture-design.md)
- v0.8.13 设置与更新维护页面布局纠偏：[`docs/design/v0.8.13-settings-maintenance-layout-correction.md`](docs/design/v0.8.13-settings-maintenance-layout-correction.md)
- v0.8.10 活动布局、字体与问题处理：[`docs/design/v0.8.10-activity-typography-problem-handling-design.md`](docs/design/v0.8.10-activity-typography-problem-handling-design.md)
- 活动管理 / 问题中心改版：[`docs/design/v0.8.2-activity-problem-center-plan.md`](docs/design/v0.8.2-activity-problem-center-plan.md)
- 自动更新 v2 升级方案：[`docs/design/v0.8.3-auto-update-v2-plan.md`](docs/design/v0.8.3-auto-update-v2-plan.md)
- v0.8.12 更新维护、活动运行时修复设计：[`docs/design/v0.8.12-maintenance-activity-runtime-fixes.md`](docs/design/v0.8.12-maintenance-activity-runtime-fixes.md)
- v0.8.11 同步、问题分层与更新进度设计：[`docs/design/v0.8.11-sync-problem-update-progress-plan.md`](docs/design/v0.8.11-sync-problem-update-progress-plan.md)
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
