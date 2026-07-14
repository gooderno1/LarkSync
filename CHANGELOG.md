# CHANGELOG

[2026-07-14] v0.8.0-dev.24 fix(frontend): 逐页重构活动与问题、冲突处理、设置和更新与维护；活动与冲突改为连续工作台并补零冲突健康态，设置统一为单一保存入口，维护移除重复更新检查并默认收起危险任务，完成 1536/1440/1280 三档真实页面验收

[2026-07-14] v0.8.0-dev.23 fix(frontend): 将同步任务表格三点按钮的行内设置改为独立居中弹窗；保持任务表高度稳定，补齐焦点锁定、页面滚动锁定、Escape 关闭和未保存修改二次确认，并完成 1536/1440/1280 三档真实页面验收

[2026-07-14] v0.8.0-dev.22 fix(frontend): 按用户澄清重设计同步任务表格三点按钮展开后的行内任务设置面板；四张独立配置卡收敛为内容流向、写入方式、删除联动三段主线，增加变更与风险摘要，四次“应用”合并为单次组合 PATCH，并限制任意时刻只展开一个任务

[2026-07-14] v0.8.0-dev.21 fix(frontend): 重设计新建任务与任务详情；新建任务由五列同屏改为带步骤门槛的单页五步向导，增加常驻配置与风险摘要并默认仅下载，详情页以任务名为标题、区分当前与最近运行，将右侧五块卡片合并为连续检查栏并折叠维护操作

[2026-07-14] v0.8.0-dev.20 fix(frontend): 按设计稿逐项深化同步任务页；筛选与新建操作合并为同一工具栏，增强次级文字和表格分隔对比度，重排模式/状态/运行/操作列并消除文字换行，将含义不明确的行尾箭头改为可展开任务设置的三点操作，启停改为语义化开关，最近运行与底部任务统计按真实信息展示

[2026-07-14] v0.8.0-dev.19 fix(frontend): 深化总览页视觉与交互设计；移除无实现价值的侧栏折叠箭头并保持 220px 常驻导航，加深次级文字、表格字重和面板边框，右侧三模块改为与主区 146/278/310px 三层严格对齐，右上账号箭头升级为可展开的账户菜单并提供账号授权与更新维护入口

[2026-07-14] v0.8.0-dev.18 fix(frontend): 逐模块复核总览页设计与真实数据行为；运行中列表不再回退空闲任务，移除日志数据量/耗时/连接延迟的推测值，健康与待处理项改用未解决冲突和真实问题队列，补齐零传输空状态、长摘要文案、单一冲突角标和显式设计样例入口，并完成 1366/1536/1920 截图验收

[2026-07-14] v0.8.0-dev.17 fix(frontend): 按浅色桌面设计稿完成同步任务、任务详情、活动与问题、冲突处理、设置、更新维护和新建任务向导的整体验收；设置页重排为账号、设备、默认策略、忽略规则和高级 OAuth，向导改为同屏五列结构，活动与冲突页移除挤占工作区的统计卡，并在隔离 dev-test 数据库补齐 8 条任务用于视觉验证

[2026-07-14] v0.8.0-dev.16 fix(frontend): 校准总览页桌面壳背景色与布局基线；侧栏改为设计稿冷白色，顶栏/底栏改为不透明中性白，移除重复的伪窗口控制符，并统一顶栏与底栏内容起始位置；完成 1080/1440/1536/1920 截图复验

[2026-07-10] v0.8.0-dev.15 fix(frontend): 按总览页设计稿进行第三轮模块级精修；对齐统计卡图标结构、运行表纵向进度、内联状态、最近同步列宽与操作图标、待处理文档卡、快速操作高度、实时连接分隔和折线；同步修正侧栏图标/间距、顶部账号区与底部状态栏，并完成 1080/1440/1536/1920 截图验收

[2026-07-09] v0.8.0-dev.14 fix(frontend): 继续按总览页设计对照优化桌面壳视觉；顶部连接状态改为点状文本序列，左侧品牌区回收至设计比例，摘要卡首张健康盾牌改为填充式图标并微调长值字号，准备新一轮截图对照

[2026-07-09] v0.8.0-dev.13 fix(frontend): 按 codex-companion 的设计到工程方法为桌面总览页补本地 ui-contract 和模块审计；修正摘要卡图标语义、长值截断、运行表速度列换行、样例待处理状态和实时连接折线，重新生成 1080/1440/1536/1920 总览页截图证据

[2026-07-09] v0.8.0-dev.12 fix(frontend): 修正桌面固定画布放大后的外层白边；适配基准改为设计稿原始 1536x1024，并用反向 viewport 尺寸 + transform 覆盖窗口；总览页按设计稿继续对齐顶栏高度、页面标题、摘要卡高度、左侧栏底部、样例数据态、右侧 316px 模块轨、顶栏 430px 操作区、运行表/最近同步表固定高度和 1536/1920 截图对照

[2026-07-09] v0.8.0-dev.11 fix(frontend): 桌面端改为 1440x960 固定设计画布整体缩放，最小 1080x720 按 0.75 倍完整呈现；移除生产 TSX 中的 viewport 断点，左栏、顶栏、底栏、总览、任务、任务详情、活动与问题、冲突、设置、维护和授权页保持同一设计结构，并补 1080/1280/1440/1920 截图验证

[2026-07-08] v0.8.0-dev.10 fix(frontend): 按桌面设计稿继续收紧总览页和壳层断点；1080/1280/1440 重新截图核对后，补齐标题状态胶囊、右侧栏结构、运行表操作列与测试样例数据态，并压缩顶栏/底栏/侧栏在低高度窗口的占位

[2026-07-08] v0.8.0-dev.9 fix(frontend): 为总览页新增设计能力建立可行性与后续开发文档；实时连接卡改为从同步事件派生稳定占位数据，并修复 dev:test WebSocket 地址使用同源 `/ws/events`

[2026-07-08] v0.8.0-dev.8 fix(desktop): 修复 dev:test 误复用其他数据目录后端的问题，端口被旧测试后端占用时自动切换后端端口；为项目内 data/dev-test 准备可读历史样例数据，并按真实数据态截图继续收紧总览页统计卡、主表格和右侧栏布局密度

[2026-07-08] v0.8.0-dev.7 fix(frontend): 按设计实现对齐矩阵和真实截图审查修正桌面壳窗口配适；左侧栏在窄窗口收为 72px 图标栏、常规窗口按设计稿收为 220px，顶栏/底栏压缩低优先级信息，总览页在 1440px 恢复 v3 设计稿 300px 右侧上下文栏，活动与问题、冲突处理、更新维护的完整多栏工作台后移到 1760px，同步任务表格降低最小宽度并延后策略四列展开

[2026-07-08] v0.8.0-dev.6 feat(frontend): 按浅色科技风视觉稿对齐桌面壳与页面骨架；顶栏改为全局状态序列，左栏收敛为桌面导航状态区，工作区补冷白科技网格背景，同步任务页改为高密度表格并接入搜索、状态、模式和健康筛选

[2026-07-08] v0.8.0-dev.5 chore(dev): 将 `npm run dev:test` 默认数据目录改为项目内 `data/dev-test`，并预填隔离测试 OAuth 配置，避免测试数据落到 C 盘 Temp

[2026-07-07] v0.8.0-dev.4 chore(dev): 新增 `npm run dev:test` 隔离测试入口，支持自定义后端/Vite/单实例锁端口和独立测试数据目录；桌面窗口 fallback 现在会输出具体原因，便于定位缺 pywebview 或 WebView 启动失败

[2026-07-07] v0.8.0-dev.3 feat(auth): 首次授权页接入本机 lark-cli 只读状态探测，展示安装、用户身份和 docs/drive scope 检测结果；后端仅返回脱敏摘要，不导入 CLI token

[2026-07-07] v0.8.0-dev.2 fix(frontend): 将总览页四摘要卡、右侧处理轨、任务详情检查器、路径三列和当前运行四指标继续后移到 1920px；宽屏侧轨增至 320px，1760px 以内保持主列优先，减少框体互相挤占

[2026-07-07] v0.8.0-dev.1 feat(desktop): `/system/update/status` 新增安装请求和 handoff 回执；更新与维护页按真实本地状态展示校验、托盘接管、helper、静默安装和自动重启阶段

[2026-07-07] v0.8.0-dev.1 fix(desktop): 托盘进程内复用已打开的 WebView 桌面窗口，避免反复点击托盘菜单生成多个窗口；退出托盘时同步清理桌面窗口子进程

[2026-07-07] v0.8.0-dev.1 fix(frontend): 首次授权页在未连接时自动轮询授权状态，OAuth redirect 保留当前 hash 路由；启动状态面板接入桌面聚合状态，展示后端、前端资源、窗口宿主、运行模式和数据目录

[2026-07-07] v0.8.0-dev.1 feat(desktop): 新增 pywebview/WebView2 桌面窗口宿主，托盘启动后优先打开桌面窗口并保留浏览器 fallback；托盘菜单新增“打开桌面窗口 / 在浏览器中打开”双入口，设置、问题和重复启动入口也优先回到桌面窗口

[2026-07-07] v0.8.0-dev.1 fix(frontend): 桌面壳启动时读取 `#settings`、`#activity` 等 hash 路由，并兼容旧 `#logcenter`，确保托盘入口能直达对应页面

[2026-07-07] v0.8.0-dev.1 fix(frontend): 将总览页和任务详情页的宽屏分栏继续后移到 1760px；任务详情路径三列和当前运行四指标同步后移，避免桌面壳中 1440/1536/1600 窗口继续挤占主内容

[2026-07-07] v0.8.0-dev.1 feat(desktop): 新增 `/system/desktop/status` 桌面壳聚合状态 API，统一返回运行时、OAuth、任务、冲突和更新摘要；顶栏和底栏改为消费同一状态模型，`/tray/status` 保持旧字段兼容

[2026-07-07] v0.8.0-dev.1 refactor(frontend): 移除不再路由的旧日志中心页面、暗色日志中心子组件和死代码组件；活动与问题、冲突处理继续作为桌面版诊断入口，并将全局 Toast/确认弹窗改为浅色科技风

[2026-07-07] v0.8.0-dev.1 feat(frontend): 将设置页收敛为 OAuth、默认同步策略、设备显示名和本地忽略目录；移除重复的自动更新/同步映射维护入口，统一回到维护页，并把设置面板改为浅色科技风

[2026-07-07] v0.8.0-dev.1 feat(frontend): 将同步任务页、任务卡片、云端目录树和新建任务向导改为浅色科技风；保留现有任务操作/API 行为，并补 smoke 测试防止回退到旧暗色卡片

[2026-07-07] v0.8.0-dev.1 fix(frontend): 将总览页和任务详情页的右轨/检查器断点从 1440px 后移到 1600px；1440px 桌面初始窗口保持纵向主内容，避免摘要卡、表格和右侧框继续互相挤占

[2026-07-07] v0.8.0-dev.1 fix(frontend): 统一桌面壳安全断点；总览摘要卡、活动与问题、冲突处理、更新维护均延后到 1440px 以上进入宽屏多列布局，补维护页 smoke test，并用真实页面验证 1280/1440 无横向溢出

[2026-07-07] v0.8.0-dev.1 fix(frontend): 收口总览页和任务详情页中等窗口布局；右侧处理轨延后到 1440px 以上并排，任务详情运行指标改为自适应网格，顶部栏标题禁止换行，消除 1280/1440 实测横向溢出和卡片挤压

[2026-07-07] v0.8.0-dev.1 feat(frontend): 按浅色科技风 v3 设计优化总览页和任务详情页；总览改为四摘要卡 + 主列大面板 + 300px 右轨，新增独立任务详情页与任务列表入口，减少面板互相挤占并补齐 smoke 测试

[2026-07-06] v0.8.0-dev.1 chore(branding): 基于旧版 LarkSync Logo 原图重新导出资产，不改动无限循环箭头、鸟形和蓝绿渐变设计；新增透明 PNG/ICO、多尺寸 favicon、托盘四态图标、旧资产归档与可重复生成脚本

[2026-07-06] v0.7.29 release: v0.7.29

[2026-07-06] v0.7.29-dev.1 fix(tray): 安装版管理面板不再因本机 3666 Vite 端口活跃而误打开开发页面；生产 URL 固定走后端 8000，3666 仅保留给显式 --dev 模式

[2026-07-06] v0.7.28 release: v0.7.28

[2026-07-06] v0.7.28-dev.7 fix(frontend): 修正仪表盘宽屏高度计算过长；App 现在用与侧边栏一致的高度包住 Header 和 Dashboard，Dashboard 只占 Header 下方剩余空间，任务概览和需要关注不再把整页撑高

[2026-07-06] v0.7.28-dev.6 fix(frontend): 仪表盘宽屏工作台改为固定高度，下方“任务概览”和“需要关注”共享同一行高度并各自内部滚动；新增 DashboardPage smoke test，防止再次退回固定短高度

[2026-07-06] v0.7.28-dev.5 fix(frontend): 修正事件管理页高度边界，顶部选任务下方的左侧运行进程和右侧具体问题改为内部滚动；运行卡片显示“问题类型数 / 事件数”，并补测试确认同一进程可展示多类问题

[2026-07-06] v0.7.28-dev.4 fix(frontend): 事件管理改为任务诊断式“顶部选任务、左侧选运行进程、右侧看具体问题”；移除按问题/按任务切换；待处理说明、待处理来源和日志体积提醒改为中性提示，避免黄色底色叠黄色文字导致不可读

[2026-07-06] v0.7.28-dev.3 fix(frontend): 事件管理重做为任务诊断式左侧队列 + 右侧详情工作台；默认隐藏普通同步事件并支持显示全部；新增事件问题分类，明确解释 `_LarkSync_MD_Mirror` 创建 forbidden、Docx 块写入 forbidden 和删除目标 not found 等“待处理”来源

[2026-07-06] v0.7.28-dev.2 fix(frontend): 事件管理去掉重复横条并改为按问题/按任务分组展示，收敛警告色块；仪表盘限制任务概览高度和条数、消除需要关注区底部留白；任务卡待处理摘要拆分为队列、待删、删失败、失败和冲突来源

[2026-07-06] v0.7.28-dev.1 feat(frontend): 日志中心“冲突管理”升级为事件管理，统一说明待删除、失败、取消和冲突事件；任务诊断默认隐藏全 0 无动作任务并支持切换显示全部；仪表盘拆分待删除与同步队列口径并优化宽屏/中等宽度布局适配

[2026-06-12] v0.7.27 release: v0.7.27
[2026-06-11] v0.7.26 release: v0.7.26
[2026-06-11] v0.7.26-dev.1 fix(docx): 修复 Markdown 上行时本地图片文件名包含括号会被错误截断的问题；图片/附件链接解析改为括号感知扫描，避免 `blocks/convert` 收到残缺 Markdown 后返回 400，并补齐带括号图片路径回归测试

[2026-05-31] v0.7.25 release: v0.7.25

[2026-05-31] v0.7.25-dev.1 fix(docx): 修复 `v0.7.24` tag 质量门中暴露的 Docx 全量替换冗余根块重取问题；全量替换现复用已知根块子节点数，不再额外请求一次 `/blocks` 打乱创建响应序列，并补齐 `test_docx_service.py` 对当前插入链路的全量回归预期

[2026-05-31] v0.7.24 release: v0.7.24

[2026-05-31] v0.7.24-dev.2 fix(docx): 修复 Docx 全量替换在根块接近飞书子节点上限时仍提前生成空文本透明容器、并在创建失败后遗留部分新顶层块的问题；写入链路现改为在删尾腾位后再决定是否包裹一级块，透明容器使用合法零宽字符段落，且失败时会回滚本轮已插入顶层块，避免云端文档越写越大后持续命中 `invalid param`

[2026-05-29] v0.7.24-dev.1 fix(ci): 修正 Windows 开机自启动 Startup 路径的目录拼接方式，避免 macOS runner 上模拟 `win32` 分支时把反斜杠当普通字符，导致 `test_tray_autostart.py` 中的 Windows 自启动回归在 `quality-macos-packaging` 误报失败

[2026-05-29] v0.7.23 release: v0.7.23
[2026-05-29] v0.7.23-dev.1 fix(ci): 升级 `release-build.yml` 中的 `actions/checkout`、`actions/setup-python`、`actions/setup-node`、`actions/upload-artifact` 与 `softprops/action-gh-release` 到当前主版本，消除 Node 20 退役告警并收紧正式版发布链路的后续维护风险

[2026-05-29] v0.7.22 release: v0.7.22
[2026-05-29] v0.7.22-dev.2 fix(tray): 修复 Windows 开机自启动失效问题；开发态快捷方式现优先指向受版本控制的 `apps/tray/launcher.py`，打包态直接指向当前 `LarkSync.exe`，`toggle_autostart()` 会按真实结果返回状态，托盘启动时还会自动修复旧的失效快捷方式

[2026-05-28] v0.7.22-dev.1 docs(promo): 同步推广就绪状态，补齐飞书开放平台 OAuth 真实脱敏截图与截图级配置指南，并按高星项目 README 首屏结构收敛下载入口、快速开始、适用场景、核心能力和安全边界，长工程细节改为折叠展示

[2026-05-28] v0.7.22-dev.1 docs(promo): 撤下非真实托盘菜单示意图和包含该示意图的 Windows 下载启动 GIF，快速开始、推广文章和素材清单统一改为只展示真实截图，托盘与安装启动素材回到待补真实截图状态

[2026-05-28] v0.7.22-dev.1 docs(promo): 继续补齐公开 Beta 推广素材，新增冲突管理页面截图和 OAuth 连接流程 GIF，并更新快速开始、推广文章草稿、素材清单与素材目录说明

[2026-05-28] v0.7.22-dev.1 docs(promo): 新增公开 Beta 推广截图与快速开始 GIF，覆盖 OAuth 配置、连接状态、`download_only` 任务创建、任务卡片、日志中心、本地 Markdown 输出和 GitHub Release 下载入口，并把素材引用补入快速开始、推广文章草稿和素材清单

[2026-05-28] v0.7.22-dev.1 docs(promo): 补齐公开 Beta 试用入口、快速开始、安全与隐私说明、反馈排障指南、FAQ、推广文章草稿、OpenClaw/AI Agent 本地缓存教程、推广素材清单、推广就绪检查清单和 GitHub Issue 表单，并同步修正 README/USAGE/版本号，降低推广前首次安装、授权和 `download_only` 首次同步的说明门槛

[2026-05-26] v0.7.21 release: v0.7.21
[2026-05-26] v0.7.21-dev.1 fix(docx): 修复超长 Docx 全量回写在根块子节点触及飞书上限时持续命中 `too many children in block (1770007)` 并把有效内容误记为“无效块已跳过”的问题；写入链路现会在必要时将一级块压缩为透明容器，并在创建前仅删除最小尾部旧块腾位，降低大文档替换失败概率
[2026-05-26] v0.7.20 release: v0.7.20
[2026-05-26] v0.7.20-dev.2 fix(auth): 将默认飞书权限与用户指引切换到新版 Docx scopes，新增 `docx:document` / `docx:document:readonly` / `docx:document.block:convert`，并在运行时把历史 `docs:doc` 配置自动迁移为新版权限集合，修复首次授权后仍缺文档读写权限的默认配置问题
[2026-05-25] v0.7.20-dev.1 fix(auth): 串行化 OAuth refresh 链路并保留缺省 refresh_token 场景下的旧值，修复同一过期凭证被并发刷新时稳定复现 `refresh token is invalid | refresh token not found (code=20026)` 的竞争窗口，同时避免兼容端点未返回新 refresh_token 时把本地 refresh token 清空
[2026-05-24] v0.7.19 release: v0.7.19
[2026-05-24] v0.7.19-dev.8 chore(ci-mac): 将 Intel mac 验证 runner 从长期排队的 `macos-13` 切换为 `macos-15-intel`，并把 DMG 卷内 `Applications` 安装入口校验纳入 macOS install-launch smoke，进一步贴近“可拖拽安装”的完成证据
[2026-05-24] v0.7.19-dev.7 chore(ci-mac): 为日常 macOS smoke 与正式版 `build-macos` matrix 显式关闭 `fail-fast`，保证 `arm64` / `x86_64` 任一架构失败时另一条验证仍会继续执行并保留结果，避免 Intel 验证再次被自动取消
[2026-05-24] v0.7.19-dev.6 fix(mac-build): 将 `greenlet>=3.0` 升级为后端显式依赖，并保留 PyInstaller hiddenimport 回归；修复 Python 3.14 arm64 环境下 `sqlalchemy` 不再自动安装 `greenlet`，导致 macOS 安装后 bundle 在数据库初始化阶段启动即崩的问题
[2026-05-24] v0.7.19-dev.5 fix(mac-build): 基于新的安装启动 smoke 诊断结果，修复 PyInstaller 产物漏打 `greenlet` 的问题；现在构建脚本与仓库 spec 都会显式纳入该依赖，避免 bundle 在 `sqlalchemy.ext.asyncio` 的数据库初始化阶段因 `No module named 'greenlet'` 提前退出
[2026-05-24] v0.7.19-dev.4 fix(ci-mac): 强化 `macos_installer_smoke.py` 的失败诊断，保留安装后 bundle 的 stdout/stderr 与 `larksync.log` 尾部，并将默认健康检查等待时间提升到 60 秒，便于继续定位 GitHub mac runner 上的安装后启动失败
[2026-05-24] v0.7.19-dev.3 feat(ci-mac): 新增 macOS DMG 安装/启动 smoke，构建后自动挂载镜像、复制 `.app`、启动 bundle 内 `LarkSync --backend` 并执行 `/health` 检查；同时将正式版与日常 smoke 的 mac 打包策略切换为 `x86_64` / `arm64` 双架构产物、让更新服务优先匹配当前机器架构的 DMG，并为 release workflow 增加 `concurrency` 以自动取消同一 PR/分支上的过期 run
[2026-05-24] v0.7.19-dev.2 fix(ci-mac): 修复 `quality-macos-packaging` 漏装 `pytest` / `pytest-asyncio` 导致 darwin runner 一进入定向回归就报 `No module named pytest` 的问题；将 `PYTHONPATH` 过滤与冻结态更新目录回归测试改成跨平台断言；同时放弃当前依赖链下不可落地的默认 `universal2` 方案，改为在 `macos-13(x86_64)` / `macos-14(arm64)` 上分别出包并让更新服务优先选择匹配本机架构的 DMG
[2026-05-24] v0.7.19-dev.1 fix(mac): 补齐 macOS 安装版关键链路，统一 `LarkSync-Setup-*.exe` 与 `LarkSync-*.dmg` 的版本识别；修复 `.app` 安装场景下 LaunchAgent 仍指向仓库脚本、托盘后端日志仍落到应用目录的问题，并补充 DMG 更新请求/自启动/打包态数据目录回归测试
[2026-05-24] v0.7.19-dev.1 fix(release): GitHub Release 工作流在稳定版 tag push 时默认同时构建并上传 macOS `dmg`，手动 `workflow_dispatch` 时仍保留 `build_macos` 开关；mac 构建补齐 `pip --upgrade` 与前端 `npm ci` 预装步骤
[2026-05-24] v0.7.19-dev.1 ci(mac): 为 `pull_request` / `push main` 新增 macOS 打包 smoke，持续验证 `.app` 与 `dmg` 产物链路，减少问题拖到正式版 tag 发布时才暴露
[2026-05-24] v0.7.19-dev.1 ci(mac): macOS smoke 工作流补充定向后端 pytest，在真实 darwin runner 上覆盖 LaunchAgent、更新安装、路径与打包脚本回归，不再只验证能否产出 DMG
[2026-05-24] v0.7.19-dev.1 feat(mac-build): macOS PyInstaller spec 默认改为 `universal2` 目标架构（支持环境变量覆盖），并将日常 mac smoke 扩展到 Intel `macos-13` 与 Apple Silicon `macos-14` runner，持续验证 Intel/M 系列兼容链路

[2026-05-24] v0.7.18 release: v0.7.18

[2026-05-24] v0.7.18-dev.1 feat(sync): 新增全局 `ignore_hidden_cache_paths` 配置，默认忽略所有以 `.` 开头的隐藏文件/目录及 `__pycache__`，并在设置页提供独立开关，避免 `.docx_tools`、`.venv`、`.git` 等隐藏缓存目录继续进入双向同步扫描

[2026-05-23] v0.7.17 release: v0.7.17

[2026-05-23] v0.7.17-dev.33 fix(build): 为 PyInstaller 新增仓库级 `hook-pydantic.py` 与 `hook-fastapi._compat.shared.py`，显式排除未使用的 `pydantic.v1` 命名空间及 FastAPI 对其的静态兼容导入，修复 Python 3.14 构建日志持续出现 `Core Pydantic V1 functionality isn't compatible` 告警的问题，并确认 `build/larksync` 产物分析结果不再包含 `pydantic.v1`

[2026-05-23] v0.7.17-dev.32 refactor(tray): 为 `tray_app` 新增 `windows_install_helper.py`，将 Windows 安装脚本构造、PowerShell helper 启动参数和静默安装 bootstrap/worker 模板下沉到独立 helper，并保持更新链路与 smoke 回归稳定

[2026-05-23] v0.7.17-dev.31 fix(auto-update): Windows 静默安装 bootstrap/helper 启动改为 `creationflags` 分级回退，优先尝试 `CREATE_BREAKAWAY_FROM_JOB`，受限环境拒绝时自动回退到普通隐藏进程组；`update_install_smoke.py` 同步记录实际使用的启动参数与回退日志，避免受限环境下 smoke 和真实静默安装一起卡在 helper 启动阶段

[2026-05-23] v0.7.17-dev.30 refactor(backend): 为 `transcoder` 新增 `transcoder_sheet_helper.py`，将内嵌 sheet 预览转码、表格矩阵裁剪和 add-ons 文本块渲染下沉到独立 helper，并保持既有转码回归稳定

[2026-05-23] v0.7.17-dev.29 refactor(backend): 为 `docx_service` 新增 `docx_markdown_convert_helper.py`，将 Markdown continuation/placeholder 预处理与块文本修补 helper 下沉到独立模块，并保持现有 `docx_service` 接口兼容

[2026-05-23] v0.7.17-dev.28 refactor(backend): 为 `sync_runner` 新增 `SyncMarkdownUploadService`，将 Markdown 上传主编排、块级状态判断、同 token 覆盖与导入重建回退逻辑下沉到独立服务，并修复测试场景下 `block_service` 替换后的动态回调绑定

[2026-05-23] v0.7.17-dev.27 refactor(backend): 为 `sync_runner` 新增 `SyncPathUploadService`，将上传路径分发、通用文件上传与旧云端文件清理逻辑下沉到独立服务，并补充 `_upload_path` 回调透传回归

[2026-05-23] v0.7.17-dev.26 refactor(backend): 为 `transcoder` 新增 `docx_parser.py`，将块类型常量、`DocxParser` 与解析 helper 下沉到独立模块，并保持 `transcoder` 原导出兼容

[2026-05-23] v0.7.17-dev.25 refactor(backend): 为 `sync_runner` 新增 `SyncDownloadOrchestrationService`，将下载树扫描、候选筛选、写回循环与运行时服务组装下沉到独立服务，并补充 `_download_docx` 回调透传回归

[2026-05-23] v0.7.17-dev.24 refactor(backend): 为 `sync_runner` 新增 `SyncUploadOrchestrationService`，将上传全量扫描、按路径上传批次、运行时服务组装与失败归档逻辑下沉到独立服务，并补充 `_run_upload_paths` 回调透传回归

[2026-05-22] v0.7.17-dev.23 refactor(backend): 为 `docx_service` 新增 `DocxContentWriteService`，将内容替换、`convert -> create` 写入编排与 Markdown 块插入逻辑下沉到独立服务，并保留原方法兼容代理以维持文档写入回归稳定

[2026-05-22] v0.7.17-dev.22 refactor(backend): 为 `docx_service` 新增 `DocxBlockCreateService`，将子块创建、失败拆分重试与图片/附件回填逻辑下沉到独立服务，并保留原方法兼容代理以维持文档写回回归稳定

[2026-05-22] v0.7.17-dev.21 refactor(backend): 为 `docx_service` 新增 `DocxPartialUpdateService`，将块级局部更新 diff、重复签名规避与锚点匹配逻辑下沉到独立服务，并保留原方法兼容代理以维持文档局部更新回归稳定

[2026-05-22] v0.7.17-dev.20 refactor(backend): 为 `docx_service` 新增 `DocxTableRuntimeService`，将大表格降级、单元格回填与插行补足等表格运行时逻辑下沉到独立服务，并保留原方法兼容代理以维持表格回归稳定

[2026-05-22] v0.7.17-dev.19 refactor(backend): 为 `docx_service` 新增 `DocxMarkdownAssetService`，将 Markdown 图片/附件 placeholder 构建、HTML 图片解析、资源路径解析与 placeholder 回填逻辑下沉到独立服务，并保留原方法兼容代理以维持文档转换回归稳定

[2026-05-22] v0.7.17-dev.18 refactor(backend): 为 `sync_runner` 新增 `SyncDownloadSupportService`，将下载候选构建、表格/多维表格 `sub_id` 补齐、导出任务轮询、导出文件下载与候选去重逻辑下沉到独立服务，并保留原私有方法兼容代理以维持下载回归稳定

[2026-05-22] v0.7.17-dev.17 refactor(backend): 为 `sync_runner` 新增 `SyncMarkdownCloudDocService`，将 Markdown 云端文档导入/重导入、导入源文件清理、同名旧文档清理与新建文档时间戳兜底等逻辑下沉到独立服务，并保留原私有方法兼容代理以维持上传回归稳定

[2026-05-22] v0.7.17-dev.16 refactor(backend): 为 `sync_runner` 新增 `SyncDeleteSyncService`，将删除墓碑创建/执行、本地回收目录移动、删除映射清理与云端幂等删除判断等逻辑下沉到独立服务，并保留原私有方法兼容代理以维持测试与调用面稳定

[2026-05-22] v0.7.17-dev.15 refactor(backend): 为 `sync_runner` 新增 `SyncCloudFolderService`，将云端父目录解析、MD 镜像目录查找/创建、目录缓存与导入后文档探测等逻辑从主 runner 中下沉，并保留原私有方法兼容代理以维持测试与调用面稳定

[2026-05-22] v0.7.17-dev.14 refactor(backend): 将 `sync_tasks` 的请求/响应模型抽到 `sync_task_models.py`，并把任务诊断与同步日志查询实现下沉到 `sync_task_diagnostics_service.py`，保留原路由和共享对象兼容层，开始按域收口后端同步任务 API

[2026-05-22] v0.7.17-dev.13 refactor(frontend): 将 `TasksPage` 和 `NewTaskModal` 拆成独立任务卡片、空态、向导步骤组件，并新增 `taskManagement` / `newTaskWizard` helper 测试与组件级 smoke test，继续推进前端页面组件化治理

[2026-05-22] v0.7.17-dev.12 refactor(frontend): 将 `SettingsPage` 拆成 `OAuth / 同步策略 / 自动更新 / 忽略目录 / 维护工具` 等独立面板组件，并新增组件级 smoke test，继续推进前端页面组件化收口

[2026-05-22] v0.7.17-dev.11 refactor(frontend): 将日志中心概览排序、`runAlert` 和展示派生状态从 `useLogCenterTaskDiagnostics` 下沉到 `taskDiagnosticsState` helper，并新增独立测试，继续把主诊断 hook 压向纯编排层

[2026-05-22] v0.7.17-dev.10 refactor(frontend): 将日志中心诊断 query 的 `include_problems` 判断、URL 参数组装与轮询间隔判断从 `useLogCenterTaskDiagnostics` 下沉到 `taskDiagnosticsQuery` helper，并新增独立测试，继续压缩主诊断 hook 的分支复杂度

[2026-05-22] v0.7.17-dev.9 refactor(frontend): 将日志中心任务选择与运行选择状态从 `useLogCenterTaskDiagnostics` 下沉到 `useTaskDiagnosticsSelection` hook，并新增 `taskDiagnosticsSelection` helper 测试覆盖默认选中、任务筛选和 active run 解析，继续压缩主诊断 hook 的职责面

[2026-05-22] v0.7.17-dev.8 refactor(frontend): 将日志中心事件时间线状态、分页与查询从 `useLogCenterTaskDiagnostics` 下沉到独立 `useTaskEventTimeline` hook，并新增 `taskEventTimeline` helper 测试覆盖查询参数拼装与轮询判断，继续压缩主诊断 hook 的职责面

[2026-05-22] v0.7.17-dev.7 refactor(frontend): 将日志中心任务诊断详情继续拆成 `TaskDiagnosticsOverviewTab`、`TaskDiagnosticsProblemsTab`、`TaskDiagnosticsEventsTab` 三个独立展示组件，并新增 tab 级 smoke test；`TaskDiagnosticsDetailPanel.tsx` 进一步收口为 header、tab 切换与数据接线层

[2026-05-22] v0.7.17-dev.6 refactor(frontend): 将日志中心任务诊断工作台拆成 `TaskSelectionPanel`、`RunHistoryPanel`、`TaskDiagnosticsDetailPanel` 三个独立视图组件，并新增组件级 smoke test；`LogCenterPage.tsx` 进一步收口为查询编排和面板装配层

[2026-05-22] v0.7.17-dev.5 refactor(frontend): 抽出日志中心冲突处理状态机到 `useConflictResolutionQueue`，并将忙闲重试判断、队列统计和状态文案判断下沉到 `src/lib/conflictResolution.ts`；冲突管理面板改为消费独立 hook/summary，不再依赖页面内部 queue ref 与重试细节

[2026-05-22] v0.7.17-dev.4 refactor(frontend): 将日志中心“任务诊断”查询与派生状态抽到 `useLogCenterTaskDiagnostics`，并把“系统日志”“冲突管理”拆成独立视图组件，主页面进一步收口为组合层，便于继续拆分任务诊断详情与冲突队列状态

[2026-05-22] v0.7.17-dev.3 feat(db): 为 SQLite 初始化引入显式 schema version 迁移注册表，启动时按版本顺序执行迁移并将当前版本写入 `sync_meta.schema_version`；新增老库升级与 schema version 测试，替代只靠 `_ensure_column/_ensure_index` 的隐式演进方式

[2026-05-22] v0.7.17-dev.2 refactor(engineering): 抽出 `sync_runner` 的事件状态流水线到独立 `SyncEventPipeline` / `sync_runner_state` 模块，并将日志中心页面中的日志映射、路径压缩、运行时长与 run_id 格式化等纯逻辑下沉到 `src/lib/logCenter.ts`，为后续继续拆分 `sync_runner` 与 `LogCenterPage` 降低耦合面

[2026-05-22] v0.7.17-dev.1 feat(engineering): 固定安装包发布基线为 `Python 3.14.x / Node 25.x` 并让 `scripts/build_installer.py` 在非基线环境下 fail fast、输出环境摘要；FastAPI 切换为 `lifespan` 管理后台服务；前端补齐 `eslint + vitest` 页面 smoke 质量门；新增 `python scripts/update_install_smoke.py` 与 CI Windows 静默安装 smoke 验证

[2026-05-22] v0.7.16 release: v0.7.16

[2026-05-22] v0.7.16-dev.1 fix(auto-update): 修复 Windows 静默安装生成的 `bootstrap.ps1` / `worker.ps1` 以无 BOM UTF-8 写入时被 Windows PowerShell 5.1 误解码、进而在中文日志文本处触发 ParserError 的问题；脚本现改为 BOM UTF-8，并新增真实 `powershell.exe -File` 回归测试，避免 handoff 永远卡在 `bootstrap_started`

[2026-05-22] v0.7.15 release: v0.7.15

[2026-05-22] v0.7.15-dev.2 fix(log-center): 日志中心事件回填改为后台 checkpoint 增量追平，启动不再阻塞等待旧日志全量入库；`/sync/logs/sync` 不再在请求链路里执行回填或清理，`sync_runs`/`sync_run_events` 补齐复合索引与后台维护任务，完成日志中心性能治理闭环

[2026-05-22] v0.7.15-dev.1 fix(log-center): 为日志中心新增 `sync_run_events` SQLite 事件持久化层，同步事件改为双写数据库与 `sync-events.jsonl`；启动时自动回填旧日志，任务诊断与 `/sync/logs/sync` 优先读取数据库并仅在必要时回退 JSONL；日志中心冲突列表改为按 Tab 懒加载，切任务保留旧详情减少闪空

[2026-05-16] v0.7.14 release: v0.7.14

[2026-05-16] v0.7.14-dev.1 fix(auto-update): Windows 静默安装现在区分 bootstrap 与 worker handoff，托盘仅在 worker 真正接管后才退出；若只停在 `bootstrap_started` 会明确报“worker 未确认接管”，并为 helper 增加 `CREATE_BREAKAWAY_FROM_JOB` 降低被父 job 提前回收的风险

[2026-05-16] v0.7.13 release: v0.7.13

[2026-05-16] v0.7.13-dev.2 fix(sync-upload): Markdown 表格列宽偏好总宽从 960 收紧到 732，贴近飞书原生云文档默认表格宽度，同时保留内容权重分配；表格渲染修复标记升级为 `#md-table-render-v10`

[2026-05-16] v0.7.13-dev.1 fix(sync-upload): Markdown 表格列宽估算改为常见多列表格 960 偏好总宽，保留内容权重分配和整表上限，减少 V1.5 修订说明这类表格在飞书端被撑得过宽；表格渲染修复标记升级为 `#md-table-render-v9`
[2026-05-16] v0.7.12 release: v0.7.12
[2026-05-16] v0.7.12-dev.1 fix(auto-update): Windows 静默安装 handoff 读取兼容 UTF-8 BOM，并将 PowerShell helper 的 handoff JSON 改为无 BOM UTF-8 写入，修复 helper 已启动但托盘因 BOM 读取失败而报“静默安装接管超时”的问题
[2026-05-15] v0.7.11 release: v0.7.11
[2026-05-15] v0.7.11-dev.1 fix(auto-update): GitHub Release API 返回 403/429 限流时，更新检查回退读取公开 `releases/latest` 跳转获取最新 tag，并按平台安装包命名生成下载与 `.sha256` 地址，避免 Release 正常但客户端报“获取 Release 失败: HTTP 403”
[2026-05-15] v0.7.10 release: v0.7.10
[2026-05-15] v0.7.10-dev.1 fix(sync-upload): Markdown 表格列宽估算改为以页面级总宽为目标，2/3/4/5 列表格不再按 `列数 * 180` 被压窄；短列保留最小宽度、长文本列按内容权重分配剩余空间，V1.5 实测 118 张表均写入 1080 总宽；表格渲染修复标记升级为 `#md-table-render-v8`
[2026-05-15] v0.7.9 release: v0.7.9
[2026-05-15] v0.7.9-dev.1 fix(auto-update): Windows 静默安装启动改为落地 bootstrap/worker `.ps1` 后通过 PowerShell `-File` 拉起，避免嵌套 `-EncodedCommand` 过长触发 `WinError 206`；更新检查会保留已校验且版本/大小/sha256 匹配的安装包 `download_path`，避免下载完成后状态回退为未下载
[2026-05-15] v0.7.8 release: v0.7.8
[2026-05-15] v0.7.8-dev.2 fix(sync-upload): Markdown 表格列宽估算增加整表总宽上限，长文本列按内容权重分配空间但不再把 V1.5 这类多列表格撑到横向滚动；表格渲染修复标记升级为 `#md-table-render-v7`，使已有 v6 表格文档下一次同步会在原 doc token 内重建一次
[2026-05-15] v0.7.8-dev.1 fix(sync-delete): 文件夹现在会作为同步对象持久化映射；本地删除已同步文件夹会生成 folder 删除墓碑并删除对应飞书文件夹，云端文件夹缺失只生成一条文件夹墓碑并按删除策略处理本地目录，同时递归清理子文件映射，避免文件夹删除被拆成多条文档删除或完全不生效
[2026-05-15] v0.7.7 release: v0.7.7
[2026-05-15] v0.7.7-dev.1 fix(sync-upload): Markdown 表格上行不再预先把超限表拆成多张表；创建飞书表格时按 API 上限先建初始行，再用表格行插入补齐剩余行，保持 V1.5 长表为单张原生表格；单元格内容改为插入到默认空段落前并随后清理占位段落，避免空行和视觉下沉；列宽补丁改按文档顺序匹配表格并覆盖飞书转换器窄默认值；表格渲染修复标记升级为 `#md-table-render-v6`
[2026-05-15] v0.7.6 release: v0.7.6
[2026-05-15] v0.7.6-dev.1 fix(auto-update): Windows 静默更新 helper 在安装器退出码为空时会复核安装目录中的目标版本，避免“实际安装成功但被判失败”；安装后重启 LarkSync 改为多轮启动确认与重试，并在日志和 handoff 中记录 expected/installed、重启 attempt、过早退出、`restart_succeeded` / `restart_failed`，便于定位自动升级后未拉起的问题
[2026-05-15] v0.7.5 release: v0.7.5
[2026-05-15] v0.7.5-dev.1 fix(sync-upload): Markdown 表格上行在填充飞书新建表格单元格前，会先删除飞书自动生成的默认空段落，再写入真实内容，避免单元格变成“空段落 + 内容”导致视觉上垂直下沉；表格渲染修复标记升级为 `#md-table-render-v5`，使已有 `#md-table-render-v4` 的历史文档下一次同步仍会在原 doc token 内全量重建一次
[2026-05-12] v0.7.4 release: v0.7.4
[2026-05-12] v0.7.4-dev.1 fix(sync-upload): 撤销 v0.7.3 对表格单元格文本写入 `Text.style.align=2` 的水平居中逻辑，保留飞书默认水平左对齐，并将超限表格渲染修复标记升级为 `#md-table-render-v4`，使已被 v0.7.3 重建过的历史文档下一次同步会再同 token 全量重建一次
[2026-05-12] v0.7.3 release: v0.7.3
[2026-05-12] v0.7.3-dev.1 fix(sync-upload): Markdown 表格上行会为表格单元格内文本块写入飞书 `style.align=2` 居中样式，并将超限表格渲染修复标记升级为 `#md-table-render-v3`，使已带 v0.7.2 `#md-table-render-v2` 标记的历史文档在下一次同步时仍会同 token 全量重建一次
[2026-05-11] v0.7.2 release: v0.7.2
[2026-05-11] v0.7.2-dev.1 fix(sync-upload): 既有 Markdown 文档检测到超限表格且缺少 `#md-table-render-v2` 修复标记时，即使本地 hash 未变化也跳过局部块 diff，改为在原 doc token 内全量重建，修复 v0.7.1 只能修复新转换块、无法清理云端历史代码块和窄表格的问题
[2026-05-11] v0.7.1 release: v0.7.1
[2026-05-11] v0.7.1-dev.1 fix(sync-upload): Markdown 上行表格转换会在发送飞书前拆分超 8 行大表并补齐列宽，表格创建失败时不再降级为 fenced code，修复软件设计说明书 V1.5 上传后表格过窄和大表变代码块的问题
[2026-05-11] v0.7.0 release: v0.7.0
[2026-05-11] v0.6.21-dev.1 feat(log-center): 日志中心运行详情的事件时间线新增上传、下载、删除等动作级筛选，删除筛选覆盖删除成功、待删除和删除失败；前端补充事件筛选规则单元测试并接入 Vitest
[2026-05-06] v0.6.20 release: 收口删除链路状态在实时状态与运行摘要中的遗漏；后端 `/sync/tasks/status` 补齐 `deleted / conflict / delete_pending / delete_failed` 等实时计数，日志中心“实际变更”、任务页和仪表盘统一展示 `删除 / 待删除 / 删除失败`，避免删除动作在正式版多个视图里继续被隐掉
[2026-05-06] v0.6.20-dev.1 fix(sync-status): `/sync/tasks/status` 补齐 `deleted / conflict / delete_pending / delete_failed` 等实时计数；日志中心“实际变更”和任务/仪表盘状态摘要同步展示删除链路状态，修复删除动作在多个视图里被漏显示的问题
[2026-05-06] v0.6.19 release: 收口冲突管理与日志中心剩余现场问题；冲突管理前端队列改为 ref 驱动的单 worker 串行泵，修复连续点击多条冲突时多个 resolve 请求并发打到后端、最终只成功一条的问题；任务诊断在概览模式下不再因缺失 `sync_runs` 摘要回退扫描 `sync-events.jsonl`，解决旧任务切换仍然卡 5~15 秒的问题
[2026-05-06] v0.6.19-dev.1 fix(conflict-center): 冲突管理前端队列改为 ref 驱动的单 worker 串行泵，修复连续点击多条冲突时因 state 竞态导致多个 resolve 请求并发打到后端、最终只成功一条的问题；同时移除共享 mutation，改为单次请求后刷新冲突列表；任务诊断在概览模式下不再因缺失 `sync_runs` 摘要回退扫描 `sync-events.jsonl`，解决旧任务切换仍然卡 5~15 秒的问题
[2026-05-06] v0.6.18 release: 收口日志中心与冲突管理交互修复，任务诊断切换默认回到“概览”并避免无意义的大日志拉取；冲突处理补充“等待任务空闲 / 成功 / 失败”状态并对“任务运行中”的 409 自动重试
[2026-05-05] v0.6.17 release: v0.6.17
[2026-05-05] v0.6.17-dev.3 fix(log-center): 任务诊断切换任务时，前端不再为同一次切换重复拉两轮 diagnostics；后端优先使用 `sync_runs` 摘要表构建任务概览和运行摘要，只在真正需要事件/问题明细时才读取 `sync-events.jsonl`，显著降低大日志场景下的切换卡顿
[2026-05-05] v0.6.17-dev.2 fix(conflict-center): 冲突管理支持连续为多条冲突选择“使用本地 / 使用云端”，前端显示“已排队 / 处理中”并按顺序提交给后端；同时移除未实现的“保留双方”动作，避免点击后必然失败
[2026-05-05] v0.6.17-dev.1 fix(sync-download): 云端文件下载写回本地时，若目标文件被 WPS/Office 等进程占用，会先做短暂重试；若仍失败，日志会明确提示“目标文件正被其他程序占用，请关闭后重试”，避免只暴露原始 `[Errno 13] Permission denied`
[2026-05-04] v0.6.16 release: v0.6.16
[2026-05-04] v0.6.16-dev.1 fix(sync-scheduler): 上传与下载调度改为任务级独立循环，单个任务长时间运行或失败不再阻塞其他任务的新一轮 run；同步运行结束后会清空 `current_run_id`，后续新的 `queued` 事件不再错误挂到旧运行时间线
[2026-05-02] v0.6.15 release: v0.6.15
[2026-05-02] v0.6.15-dev.2 fix(sync-upload): 已有云端文档遇到超限 Markdown 表格时，`partial/auto` 会先尝试按整表块替换保持原文档 token；`partial` 不再直接拒绝，`auto` 仅在块替换与同 token 全量覆盖都失败后才回退到导入重建
[2026-05-01] v0.6.15-dev.1 fix(sync-ignore): 任务运行中更新忽略目录等同步执行参数时，后端会取消当前 run 并按最新配置自动重启，避免当前运行继续按旧范围扫描和上传；同时补充任务更新重启判定测试与 runner 重启回归测试
[2026-05-01] v0.6.14 release: v0.6.14
[2026-05-01] v0.6.14-dev.1 fix(auto-update): Windows 静默安装改为 bootstrap -> worker 双阶段接管；托盘先用隐藏 bootstrap 进程确认接管，再由 bootstrap 拉起独立 PowerShell worker 执行安装与重启，修复主程序侧等待 handoff 超时、安装器实际从未接管的问题
[2026-05-01] v0.6.13 release: v0.6.13
[2026-05-01] v0.6.13-dev.1 fix(sync-ignore): 忽略目录扩展为双向隔离；云端下载、云删本地和已排队删除墓碑都会跳过已忽略子目录，避免把已忽略目录重新下载或从本地删掉
[2026-05-01] v0.6.12 release: v0.6.12
[2026-05-01] v0.6.12-dev.1 feat(sync-settings): 设置页支持按任务维护本地忽略目录，后端按任务忽略选定子目录的监听与上行扫描；静默安装接口会拒绝当前版本或更旧版本的重复安装请求并返回明确提示
[2026-05-01] v0.6.11 release: v0.6.11
[2026-05-01] v0.6.11-dev.3 feat(update-ui): 设置页更新区新增“打开安装包目录”按钮，静默安装失败时可直接打开已下载更新所在目录进行手动排查或重试
[2026-05-01] v0.6.11-dev.2 fix(auto-update): Windows 静默升级 helper 改为 detached + breakaway 启动，确保托盘退出后 helper 继续等待安装器完成并负责重启新版本，修复只记录 installer_started 后链路中断的问题
[2026-05-01] v0.6.11-dev.1 fix(auto-update): 更新状态缓存读取时清理已过期或版本不匹配的 download_path，避免设置页拿旧安装包再次触发同版本静默安装并被托盘忽略，表现成静默更新失败
[2026-05-01] v0.6.10 release: v0.6.10
[2026-05-01] v0.6.10-dev.1 fix(sync-diagnostics): 历史持久化运行若因应用退出、更新或进程终止残留为 running，日志中心改显示为已中断；等待上传事件补齐 run_id，飞书文件上传失败信息补充 code/http/request_id，并修复运行耗时按毫秒误算的问题
[2026-05-01] v0.6.9 release: v0.6.9
[2026-05-01] v0.6.9-dev.1 feat(frontend): 仪表盘改为同步健康总览与需要关注摘要，任务卡片默认突出本地/飞书同步关系和健康状态；冲突解决改为等待后端确认后反馈，维护类动作统一使用应用内确认框
[2026-05-01] v0.6.8-dev.1 fix(ci): 修复冲突解决上传测试替身缺少 Markdown 资源基线参数导致的后端测试红灯；后端 pyproject 改用包内可解析 readme 元数据，恢复 editable 安装校验；发布工作流新增 quality job，在正式安装包构建前执行后端 pytest、editable 安装 dry-run 和前端构建
[2026-05-01] v0.6.7 release: v0.6.7
[2026-05-01] v0.6.7-dev.2 fix(auto-update): Windows 托盘处理静默安装请求前新增版本兜底；若安装包版本小于等于当前已运行版本，则直接清理 `install-request.json` / `install-handoff.json` 并忽略请求，修复安装成功后旧请求残留导致的新版本打不开或反复重启
[2026-05-01] v0.6.7-dev.1 fix(auto-update): Windows 静默更新 helper 将 PowerShell `Start-Process` 从错误的 `-LiteralPath` 改为 `-FilePath`，修复从 `v0.6.5` 静默升级到 `v0.6.6` 时 helper 已接管但安装器根本未启动、随后回退当前版本并最终报超时失败的问题
[2026-05-01] v0.6.6 release: v0.6.6
[2026-05-01] v0.6.6-dev.8 fix(log-center): 任务诊断页改为按侧边栏高度拉满，左下运行记录和右下运行详情底边与侧边栏对齐；`概览` 移除重复的“当前处理文件”卡片，改为展示同步目标（本地目录 / 云端目录），避免同一文件信息重复出现
[2026-05-01] v0.6.6-dev.7 feat(log-center): 任务选择框彻底去掉路径并收成可搜索 Combobox；右侧详情头部将最近活动时间并入标题行，继续减少分割线并保持运行摘要归入“概览”标签页
[2026-05-01] v0.6.6-dev.6 feat(log-center): 任务选择区升级为可搜索 Combobox，任务选择框只显示任务名；右侧详情头部将最近活动时间提到任务名同排，并继续减少多余分割线，进一步提升空间利用率
[2026-05-01] v0.6.6-dev.5 feat(log-center): 任务诊断页将“任务上下文”更名为“任务选择”，去除无意义说明文案与常驻任务筛选标签，右下常驻运行状态合并进“概览”标签页，同时保留头部最近活动时间，进一步释放事件详情区空间
[2026-04-30] v0.6.6-dev.4 feat(log-center): 继续压缩任务诊断页信息密度，任务上下文条改成更扁的一行半布局，运行记录卡收成两行结构并短码显示 run_id，运行详情头部去掉重复路径/时间信息，进一步缓解页面拥挤
[2026-04-30] v0.6.6-dev.3 feat(log-center): 任务诊断页进一步改为“上方任务选择条 + 下方运行记录/运行详情双栏”，用下拉选择 + 搜索替代常驻任务列，减轻横向拥挤；继续保留独立滚动、紧凑摘要条与事件 Tab 专属筛选
[2026-04-30] v0.6.6-dev.2 feat(log-center): 日志中心任务诊断页按“左任务 / 右上运行记录 / 右下运行详情”重排，保留全局侧边栏与顶部页头；运行详情改为紧凑摘要条 + Tab，事件筛选仅在事件 Tab 下显示，并同步压缩侧边栏和任务卡信息密度，缓解页面拥挤与切换抖动
[2026-04-30] v0.6.6-dev.1 fix(sync-baseline): `sync_links` 新增 Markdown 本地资源基线字段，下载 doc/docx 成功后记录本地资源签名与对应云端 revision；上传阶段改为按“正文 hash + 本地资源签名 + 资源基线 revision”联合判断是否真的发生了本地变更，避免云端下载后的同轮反向上传覆盖飞书
[2026-04-30] v0.6.5 release: v0.6.5
[2026-06-12] v0.7.27-dev.1 fix(docx-upload): 空代码块上行自动补零宽占位，修复飞书 invalid param 导致的整篇替换失败
[2026-04-30] v0.6.5-dev.3 feat(log-center): 新增 sync_runs 运行摘要表，按运行持久化同步结果并驱动日志中心
[2026-04-30] v0.6.5-dev.2 feat(log-center): 日志中心按运行 ID 展示同步历史，任务概览仅反映最近一次运行
[2026-04-30] v0.6.5-dev.1 fix(auto-update): Windows 静默更新 helper 去掉 DETACHED_PROCESS，改用隐藏窗口进程组启动，修复安装接管回执超时导致的静默更新失败
[2026-04-29] v0.6.4 release: v0.6.4
[2026-04-29] v0.6.3 release: v0.6.3
[2026-04-29] v0.6.3-dev.2 fix(sync-download): 云端下载写本地文件前预先静默 watcher，覆盖 docx/导出文件/普通文件三条下载分支，避免“云端下载 -> watcher 误判本地修改 -> 周期上传反向覆盖云端”的回流问题
[2026-04-29] v0.6.3-dev.1 fix(auto-update): Windows 静默更新改为“helper 接管成功后再退出主程序”；helper 会先写接管回执，再启动安装器并记录启动/退出结果，安装器未拉起或非零退出时会恢复拉起当前版本；坏掉的 install-request 会自动清理，避免程序反复退出或死循环重试
[2026-04-29] v0.6.2 release: v0.6.2
[2026-04-29] v0.6.2-dev.5 fix(conflict-resolution): 冲突管理的“使用本地 / 使用云端”改为真正触发定向同步；本地优先会强制上传当前本地文件覆盖云端，云端优先会强制下载当前云端版本覆盖本地，执行失败时不会提前把冲突标记为已解决
[2026-04-29] v0.6.2-dev.4 feat(auto-update): Windows 自动更新默认改走 NSIS 静默安装，托盘用 detached PowerShell helper 等待安装器退出后自动重启新版本，并记录静默安装 PID、退出码与重启动作
[2026-04-29] v0.6.2-dev.3 fix(auto-update): 正式版自动更新改用用户数据目录保存安装包/状态/安装请求，避免从安装目录自更新；更新状态读取会覆盖陈旧 current_version，修复安装成功后仍提示可更新的问题
[2026-04-29] v0.6.2-dev.2 fix(conflict-center): 冲突记录写入改为对同一路径、同一 token、同一版本差异幂等；冲突列表折叠历史残留的重复未解决记录，避免冲突管理显示两条相同冲突
[2026-04-29] v0.6.2-dev.1 fix(sync-delete): 删除墓碑执行云端删除前检查同一 cloud token 是否仍有其他有效本地路径；本地回收目录移动会静默 watcher 事件，避免云端删除引发本地回收后又反向误删云端
[2026-04-28] v0.6.1 release: v0.6.1
[2026-04-28] v0.6.1-dev.4 feat(log-center): 日志中心接入后端任务诊断接口，新增同步事件 `run_id`、任务概览与单任务诊断 API，前端按任务展示真实运行状态、当前处理文件、问题摘要和事件时间线
[2026-04-28] v0.6.1-dev.3 feat(log-center): 日志中心重构为任务诊断视图，支持按任务查看当前状态、最近运行、处理进度、问题摘要和事件时间线；系统日志与冲突管理保留为辅助排查入口
[2026-04-28] v0.6.1-dev.2 fix(frontend): 仪表盘任务展示拆分为“当前运行”和“最近同步”，Header 改用真实任务状态提示；任务页最近同步时间使用 `last_run_at` 兜底，并将进度改为已处理/总数，修复全跳过任务显示别扭的问题
[2026-04-28] v0.6.1-dev.1 fix(sync-upload): 双向同步 Markdown 上行覆盖前新增云端修改时间预检；若云端相对本地同步基线已更新则阻止覆盖并记录冲突，避免本地旧版本覆盖飞书云文档协作版本
[2026-04-28] v0.6.0 release: v0.6.0
[2026-04-28] v0.6.0-dev.1 feat(sync-safety): 新建任务或距离上次运行超过 48 小时的任务会先执行一轮无删除补齐，跳过删除墓碑创建/执行并记录 `last_run_at`，降低首次运行和长时间离线后的误删除风险
[2026-04-28] v0.5.64-dev.1 fix(feishu-client): 飞书统一请求客户端新增 500/502/503/504 临时服务端错误指数退避重试，修复 `docx/v1/documents/blocks/convert` 偶发 502 会直接中断 Markdown 上行的问题
[2026-04-23] v0.5.63 release: v0.5.63
[2026-04-23] v0.5.63-dev.1 fix(sync-upload): Markdown 图片素材回填飞书图片块时同步写入按源图计算的等比 `width/height`（最大宽度 820px），修复空图片块默认 `1460x220` 导致插图比例被拉伸的问题；现场修正目标文档 `JYtPdpNuCoQAyzxJWgRcy8bQnrg` 的 37 个图片块显示尺寸
[2026-04-23] v0.5.62 release: v0.5.62
[2026-04-23] v0.5.62-dev.1 fix(sync-upload): Markdown 图片素材上传到飞书 `drive/v1/medias/upload_all` 时为 multipart file 显式写入 MIME（如 `image/png`），并将本地图片修复标记升级到 `#local-images-v2` 以强制重传旧 `v1` 图片 token，修复飞书 Docx 前端显示“无法导入该图片”的问题
[2026-04-23] v0.5.61 release: v0.5.61
[2026-04-23] v0.5.61-dev.1 fix(sync-upload): Markdown 上行遇到“超限表格 + 本地图片”时不再走飞书原生 Markdown 导入，改走块级覆盖以确保本地图片上传为飞书图片块；首次导入创建后若检测到本地图片会立即执行块级覆盖；历史同 hash 缺图文档会强制执行一次图片修复覆盖并写入 `#local-images-v1` 修复标记
[2026-04-23] v0.5.60 release: v0.5.60
[2026-04-23] v0.5.60-dev.1 fix(sync-upload): Markdown 上行遇到失效的 `fig-数字` 图片相对路径时，按图号回退查找同级 `figures/`、`插图/`、`assets/` 中的真实源图；补齐《软件设计说明书-V1.4》迁移后缺失的 `V1.4-GPT-image-2` 图片目录，确保 37 张图片均可进入飞书图片上传链路
[2026-04-19] v0.5.59 release: v0.5.59
[2026-04-19] v0.5.59-dev.4 fix(sync-upload): Markdown 上行检测到飞书块级建表行数超限时，自动改走飞书原生 Markdown 导入重建并替换旧文档，修复需求/设计说明书这类大表格文档继续降级为代码块的问题，同时将导入轮询默认时长延长到 60 秒以覆盖大文档导入
[2026-04-19] v0.5.59-dev.3 fix(sync-upload): Markdown 上行不再为飞书表格创建请求注入 `column_width`，HTML 内嵌 `data:image/...` 图片改为优先复用本地 `figures/插图` 资源并进入图片上传链路，同时忽略 `figures/插图` 源图目录的独立附件上传
[2026-04-14] v0.5.59-dev.2 fix(docx-upload): Markdown 上行遇到飞书大表格 `1770001 invalid param` 时自动降级为代码块重试，避免整篇文档上传中止
[2026-04-14] v0.5.59-dev.1 fix(docx-upload): 创建表格块时保留并补齐 `table.cells`，修复 Markdown 含表格时飞书返回 `1770001 invalid param`
[2026-04-09] v0.5.58 release: v0.5.58
[2026-04-09] v0.5.58-dev.1 fix(update-install): Windows 在线升级安装改为优先使用 ShellExecute (`os.startfile`) 直接拉起安装包，失败时再回退 PowerShell，修复“程序已退出但安装器未成功启动”
[2026-04-09] v0.5.57 release: v0.5.57
[2026-04-09] v0.5.57-dev.2 fix(frontend): 设置页、新建任务与任务管理页按同步模式收起不适用配置，避免 `download_only` 任务继续显示 MD 上传相关选项
[2026-04-09] v0.5.57-dev.1 fix(sync-download): `download_only` 模式下禁用云端 MD 镜像创建/回写，修复仍尝试创建 `_LarkSync_MD_Mirror` 并返回 forbidden 的问题
[2026-04-09] v0.5.56 release: v0.5.56
[2026-04-08] v0.5.56-dev.1 fix(update-install): Windows 托盘改为使用 `powershell.exe -EncodedCommand` + `Start-Process -LiteralPath` 拉起安装包，并补充安装启动日志，修复“更新包已下载但确认安装后程序退出、安装器未成功启动”
[2026-04-08] v0.5.55 release: v0.5.55
[2026-04-08] v0.5.55-dev.8 feat(cli,agent): `workflow-execute` 自动归档到 `data/workflows`，新增 `workflow-run-list/show/prune` 并支持仅凭 `run_id` 恢复执行
[2026-04-08] v0.5.55-dev.7 feat(cli,agent): `workflow-execute` 新增 `run_id`/`resume-from-file`/`skip-completed`，支持基于已有执行结果恢复并跳过已成功步骤
[2026-04-08] v0.5.55-dev.6 feat(cli,agent): `workflow-execute` 新增步骤区间、失败后继续与结果 JSON 落盘控制，便于 Agent 局部重跑与审计
[2026-04-08] v0.5.55-dev.5 feat(cli,agent): 新增 `workflow-execute` 工作流执行器，可顺序执行模板步骤并把上一步结果自动注入下一步动态参数
[2026-04-08] v0.5.55-dev.4 feat(cli,agent): 新增 `workflow-plan` 模板实例化命令，可将标准工作流渲染为带参数、带动态依赖提示的可执行命令计划
[2026-04-08] v0.5.55-dev.3 feat(cli,agent): 新增 `workflow-template-list` / `workflow-template` 标准工作流模板命令，内置 daily-cache、refresh-cache、conflict-audit 三类 Agent 模板
[2026-04-07] v0.5.55-dev.2 feat(cli,agent): 新增 `bootstrap-cache` 高层初始化命令与 CLI Agent 契约文档，统一首次接入/OAuth 分支与 OpenClaw 推荐工作流
[2026-04-07] v0.5.55-dev.1 feat(cli,openclaw): 新增正式 CLI 统一封装授权/配置/任务/日志/更新/冲突等核心能力，并让 OpenClaw helper 复用同一命令面
[2026-04-07] v0.5.54 release: v0.5.54
[2026-04-07] v0.5.54-dev.1 fix(update-install): 托盘仅在安装请求成熟后再退出并拉起安装包，修复“已下载更新后点击安装提示 Failed to fetch”
[2026-04-07] v0.5.53 release: v0.5.53
[2026-04-07] v0.5.53-dev.1 fix(sync-upload): 上传链路忽略 Office/编辑器临时文件与系统噪音文件，修复本地对云端误传 `~$`/`.tmp`/`Thumbs.db` 等临时产物
[2026-03-11] v0.5.52 release: v0.5.52
[2026-03-11] v0.5.52-dev.1 feat(update): 自动下载更新包后支持“确认安装”安全流程，由托盘在收到安装请求后退出应用并启动安装程序
[2026-03-11] v0.5.51 release: v0.5.51
[2026-03-11] v0.5.51-dev.1 fix(release,update): Release 自动附带安装包 sha256 到正文并上传 `.sha256` 资产，兼容 v0.5.49 等旧客户端的自动更新校验
[2026-03-11] v0.5.50 release: v0.5.50
[2026-03-11] v0.5.50-dev.3 fix(sync-upload): 非 Markdown 文件二次上传后自动清理旧云端文件与同名历史副本，修复本地反复生成/修改 PDF 时飞书目录持续累积重复文件
[2026-03-08] v0.5.50-dev.2 fix(release-notes,changelog): 发布说明生成器支持“无 release: 标记”回退归档（按目标版本首条记录锚定），避免发布页出现“未找到可归档的增量条目”；同步规范最新条目置顶，提升可读性
[2026-03-07] v0.5.50-dev.1 fix(update): 自动更新校验链路补齐三层来源（Release 资产 digest > .sha256 文件 > Release 正文），修复旧客户端报“缺少 sha256 校验信息”导致下载被阻断
[2026-03-07] v0.5.49 fix(sync-upload): 本地持续编辑场景改为“静默窗口后再上传”（2s），上传队列升级为路径+最后变更时间，避免同一文档被周期任务重复上云
[2026-03-06] v0.5.48 release: v0.5.48
[2026-03-06] v0.5.48-dev.1 fix(build,ci): 修复 Windows Release 构建入口脚本缺失导致的 PyInstaller 失败（新增受版本控制入口 `apps/tray/launcher.py`，spec/build 脚本改为优先使用该入口并保留 `LarkSync.pyw` 兼容兜底）
[2026-03-06] v0.5.47 release: v0.5.47
[2026-03-06] v0.5.47-dev.2 fix(sync,docx): 修复获取文档块列表使用 `page_size=500` 导致飞书返回 400 的问题，调整为安全分页值并补充回归测试
[2026-03-06] v0.5.47-dev.1 fix(ui,auth): 提升“权限不足”提示在主页面与新建任务弹窗中的文字对比度，修复浅色主题下看不清的问题
[2026-03-06] v0.5.46 fix(auth,onboarding): 修复首次 OAuth 配置填写错误后卡在“连接飞书”页的问题，支持返回上一步直接修改并重试
[2026-02-28] v0.5.45 fix(openclaw-skill-security): 收紧 `larksync_wsl_helper.py`，移除 WSL 自动安装依赖与自动拉起后端；改为纯 Python 地址诊断 + 安全转发；同步更新 OpenClaw Skill 文档与 ClawHub 发布示例至 `0.1.6`
[2026-02-24] v0.5.44 release(openclaw-skill): 发布 `larksync-feishu-local-cache@0.1.5`（`fix(wsl-runtime): sanitize pythonpath for autonomous local backend startup`）
[2026-02-24] v0.5.44 fix(openclaw,wsl-runtime): 修复 WSL 自动拉起后端时受跨版本 `PYTHONPATH` 污染导致 `pydantic_core` 导入失败；`larksync_wsl_helper.py` 新增运行时 `PYTHONPATH` 净化并应用到依赖安装与后端子进程启动；补充对应测试
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
[2026-04-29] v0.6.4-dev.1 fix(sync-conflict): 创建云端文档后立即补齐同步基线，修复首次上传误判“云端已更新”冲突
[2026-04-30] v0.6.5 release: v0.6.5
