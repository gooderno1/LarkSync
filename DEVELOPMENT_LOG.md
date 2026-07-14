# DEVELOPMENT LOG

## v0.8.0-dev.22 (2026-07-14)

- 开发原因：
  - 用户澄清“任务详情”是任务表格最右侧三点按钮展开后的行内视图，而非独立任务详情页。
  - 旧行内视图把同步、更新、MD 上传和删除策略拆成四张同权重卡片，缺少配置顺序。
  - 每张卡片都要求单独点击“应用”，一次策略调整可能产生四次保存，用户无法判断是否全部完成。
  - 仅下载任务的 MD 上传卡没有可配置内容仍占整列；删除任务长期暴露在底部并抢占注意力。
- 实现方式：
  - 先新增本地规格 `docs/local_specs/task_row_settings_panel_redesign_v0.8.0-dev.22.md`，明确范围、信息架构、交互、尺寸和验收标准。
  - 新增独立 `TaskSettingsPanel`，将表单重排为“内容流向 → 写入方式 → 删除联动”三段连续主线。
  - 右侧 `272px` 摘要栏展示内容流向、更新模式、MD 模式、删除策略、变更项数量和风险等级。
  - 同步模式与删除策略改为带影响说明的三选卡；仅下载时将 MD 上传降级为“不适用”说明。
  - 初始“放弃更改 / 保存更改”均禁用；修改后按配置组统计待保存数量，保存失败保留草稿并允许重试。
  - 新增 `updateTaskSettings` mutation，通过单次任务 PATCH 提交全部已变字段；严格删除强制宽限为 0。
  - 删除任务移入默认折叠的“维护操作”，继续使用既有应用内二次确认。
  - 展开状态从任务 ID 映射改为单一 `expandedTaskId`，任意时刻只保留一个行内设置面板。
  - 补齐根目录、前端和后端版本一致性，统一推进到 `v0.8.0-dev.22`。
- 当前结果：
  - 展开面板不再出现四个“应用”，所有策略只保留一个“保存更改”。
  - `1536x1024` 下完整面板高度为 `586px`，可在任务工作区内完整展示。
  - `1536x1024`、`1440x900`、`1280x800` 下页面 `scrollWidth` 均等于 viewport 宽度。
  - 点击另一任务三点按钮后，展开面板数量始终为 1。
  - 三档视口下浏览器控制台与页面异常监听均无错误。
- 验证方式：
  - `python scripts/sync_feishu_docs.py`：通过；4 个飞书文档包已检查。
  - `npm --prefix apps/frontend test -- --run src/lib/taskSettings.test.ts src/components/tasks/TaskSettingsPanel.test.tsx src/pages/TasksPage.test.tsx`：通过，3 个测试文件、7 个测试。
  - `npm --prefix apps/frontend run typecheck`：通过。
  - `npm --prefix apps/frontend test`：通过，28 个测试文件、78 个测试。
  - `npm --prefix apps/frontend run lint`：通过，无警告。
  - `python -m pytest tests/test_version.py -q`（`apps/backend`）：通过，确认开发态版本读取为 `v0.8.0-dev.22`。
  - `python scripts/build_installer.py`：通过；前端生产构建、托盘图标生成和 PyInstaller 桌面目录打包成功，生成 `dist/LarkSync/LarkSync.exe`（17.5 MB）；本轮未指定 `--nsis`。
  - Playwright + Edge 完成三档真实页面展开、修改态、唯一面板、保存禁用、溢出和浏览器错误检查：通过。
  - 截图证据位于 `docs/local_specs/visual_audit/2026-07-14-task-row-settings-redesign/`；该目录属于本地规格资料，不进入 Git。
- 遗留问题：
  - 本轮沿用现有任务 PATCH 契约，没有新增后端字段或猜测第三方 API 数据。
  - 独立任务详情页继续保留；三点展开区统一称为“任务设置”，避免后续再次混淆。

## v0.8.0-dev.21 (2026-07-14)

- 开发原因：
  - 新建任务把五个步骤同时放进五列，字段、说明与操作互相挤压，当前决策缺少视觉焦点。
  - 向导允许未完成必填目录时直接跳到后续步骤，并默认选择可写入云端的双向同步，不符合首次使用的低风险路径。
  - 任务详情重复展示“任务详情”和任务名称；完成的运行仍标为“当前运行”，语义不准确。
  - 详情右侧把问题、操作、策略、忽略目录和危险操作拆为五张卡片；零值和高风险按钮长期占据视觉焦点。
- 实现方式：
  - 先新增本地规格 `docs/local_specs/new_task_and_task_detail_redesign_v0.8.0-dev.21.md`，定义信息架构、状态语义、交互门槛、尺寸和验收标准。
  - 新建任务弹窗收敛为 `1120px` 五步单页向导；正文使用当前步骤主区与 `280px` 常驻摘要，移除五列同时渲染。
  - 本地目录和云端目录成为前置门槛：未选本地目录最多访问第 1 步，未选云端目录最多访问第 2 步，两项完成后开放后续策略步骤。
  - 默认同步模式改为 `download_only`；风险按同步写入能力和删除策略计算，严格删除固定标记为高风险。
  - 删除策略由下拉框改为关闭联动、安全删除、严格删除三张说明卡；任务启用改用 `role=switch` 和 `aria-checked`。
  - 任务详情以任务名称作为唯一一级标题；同步关系改为紧凑端点卡，运行标题按 `running / 已有历史 / 从未运行` 分别显示“当前运行 / 最近一次运行 / 运行状态”。
  - 四项传输统计改为同一行分隔指标；右侧合并为单个 `300px` 连续检查栏，仅展示非零问题，零问题显示健康状态，重置映射与删除任务默认折叠在维护操作中。
  - “编辑策略”改为真实行为文案“返回列表管理策略”，避免把返回列表误写成详情页内编辑。
  - 版本推进到 `v0.8.0-dev.21`。
- 当前结果：
  - 新建任务在 `1536x1024` 与 `1280x1024` 下均只显示当前步骤，底部任一步骤只有一个主操作。
  - 任务详情在 `1536x1024`、`1280x900`、`1024x900` 下无页面级横向溢出，右侧检查栏保持一个连续容器。
  - 已完成运行显示“最近一次运行”；任务无问题时不再渲染四张 0 值问题卡。
  - 浏览器控制台和页面异常监听均无错误。
- 验证方式：
  - `python scripts/sync_feishu_docs.py`：通过；4 个飞书文档包已检查。
  - `npm --prefix apps/frontend test -- --run src/lib/newTaskWizard.test.ts src/components/tasks/NewTaskWizardPanels.test.tsx src/pages/TaskDetailPage.test.tsx`：通过，3 个测试文件、11 个测试。
  - `npm --prefix apps/frontend run typecheck`：通过。
  - `npm --prefix apps/frontend test`：通过，26 个测试文件、74 个测试。
  - `npm --prefix apps/frontend run lint`：通过，无警告。
  - `python -m pytest tests/test_version.py -q`（`apps/backend`）：通过，确认开发态版本读取为 `v0.8.0-dev.21`。
  - `python scripts/build_installer.py`：通过；前端生产构建、托盘图标生成和 PyInstaller 桌面目录打包成功，生成 `dist/LarkSync/LarkSync.exe`（17.5 MB）；本轮未指定 `--nsis`。
  - Playwright + Edge 对上述五个视口组合执行真实页面截图、页面溢出和浏览器错误检查：通过。
  - 截图证据位于 `docs/local_specs/visual_audit/2026-07-14-new-task-detail-redesign/`；该目录属于本地规格资料，不进入 Git。
- 遗留问题：
  - 当前“返回列表管理策略”保持既有列表内展开设置能力；如后续新增详情页内编辑，需要先定义独立保存、撤销和并发更新交互。
  - 本轮不改任务创建 API 字段，风险摘要仅解释现有 `sync_mode` 与 `delete_policy`，没有引入推测性后端规则。

## v0.8.0-dev.20 (2026-07-14)

- 开发原因：
  - 同步模式和“详情”操作在任务表格中发生纵向换行，降低扫描效率。
  - 行尾箭头同时承担展开策略的行为，但没有文案或状态反馈，操作含义不明确。
  - 任务启停控件缺少标准开关语义；停用任务同时显示两次“已停用”。
  - “最近运行”在无运行记录时显示更新策略“自动”，信息归属错误。
  - 新建任务位于标题行，而设计稿要求与搜索筛选处于同一操作层级。
- 实现方式：
  - 将搜索框、状态/模式/健康筛选与测试任务开关、刷新、新建任务合并为同一工具栏。
  - 表格列宽调整为任务 `14%`、本地 `13%`、云端 `13%`、模式 `9%`、状态 `10%`、最近运行 `11%`、四类计数各 `4%`、操作 `14%`。
  - 同步模式标签增加单行约束；详情、立即同步和任务设置使用 `30px` 图标按钮，保留明确的 `aria-label` 与悬停说明。
  - 行尾箭头替换为三点任务设置按钮；展开时使用蓝色边框与浅蓝底反馈，并继续显示四类策略和危险操作。
  - 启停控件使用 `role=switch`、`aria-checked` 和滑块视觉；状态与健康标签相同时只展示一次。
  - 无运行时间时显示“尚未运行”，不再把更新模式放入最近运行列。
  - 任务数量从表格顶部移至底部；筛选后显示“显示 N / 共 M 个任务”，不加入无真实分页行为的页码控件。
  - 同步任务页增加 `tasks-clarity` 作用域，次级文字、表格边框和正文重量沿用总览页的清晰度标准。
  - 版本推进到 `v0.8.0-dev.20`。
- 当前结果：
  - `1536x1024`、`1440x900`、`1280x800` 三个尺寸均完整显示 8 行隔离测试任务。
  - 三个尺寸下全部同步模式标签均为单行；页面级 `scrollWidth` 未超过 viewport。
  - 操作列完整展示详情、立即同步、启停和任务设置四个入口，展开后的四类策略与删除任务区域正常可见。
  - 浏览器控制台未出现错误；停用任务不再重复显示健康文案。
- 验证方式：
  - `python scripts/sync_feishu_docs.py`：通过；4 个飞书文档包已检查。
  - `npm --prefix apps/frontend run test`：通过，26 个测试文件、70 个测试。
  - `npm --prefix apps/frontend run typecheck`：通过。
  - `npm --prefix apps/frontend run lint`：通过，无警告。
  - `python -m pytest tests/test_version.py -q`（`apps/backend`）：通过，确认开发态版本读取为 `v0.8.0-dev.20`。
  - `python scripts/build_installer.py`：通过；前端生产构建、托盘图标生成和 PyInstaller 桌面目录打包成功，生成 `dist/LarkSync/LarkSync.exe`（17.5 MB）；本轮未指定 `--nsis`。
  - Playwright + Edge 对 `1536x1024`、`1440x900`、`1280x800` 执行真实页面截图、模式行高、页面溢出和浏览器错误检查：通过。
  - 截图证据位于 `docs/local_specs/visual_audit/2026-07-14-sync-tasks-page-pass/`；该目录属于本地规格资料，不进入 Git。
- 遗留问题：
  - 本轮不增加分页，因为当前前端一次加载完整任务列表且没有后端分页契约；任务量增长后需要先定义分页或虚拟滚动的数据接口。
  - 本轮只收口同步任务列表页；任务详情页将在下一轮按同一流程单独复核。

## v0.8.0-dev.19 (2026-07-14)

- 开发原因：
  - 侧栏左下角折叠箭头没有实际折叠状态与业务价值，用户无法判断点击结果。
  - 固定画布缩放后，浅色次级文字、细边框和普通表格字重产生模糊感。
  - 右侧三个模块与主区摘要、运行、最近同步三层起始坐标不同，削弱横向秩序。
  - 右上账号名后的下拉箭头仅是装饰，没有解释或可执行功能。
- 实现方式：
  - 删除侧栏折叠按钮，导航保持 `220px` 常驻，不引入第二套折叠布局和状态持久化。
  - 总览页增加 `dashboard-clarity` 清晰度作用域：次级文字提升到 `#465b73 / #3f536b`，主要面板边框提升到 `#c6d7e9`，表格正文使用 `font-weight: 500`，并恢复浏览器的自然字体平滑。
  - 右侧轨道改为 `grid-rows-[146px_278px_310px]`、`gap-5`、`pt-9`，与主区摘要卡、运行面板和最近同步面板逐层共用高度和起始坐标。
  - “需要处理”压缩为可点击的单行问题摘要；“快速操作”使用带动作说明的四个 `94px` 按钮；实时折线区域压缩到 `64px`，保证内容在对齐后的行高内完整显示。
  - 账号区域改为真实菜单按钮，支持点击展开、再次点击关闭、点击外部关闭和 `Escape` 关闭；菜单明确提供“账号与授权”和“更新与维护”入口。
  - 退出登录继续保留在设置页，不放入顶栏高频区域，避免误触造成授权中断。
  - 版本推进到 `v0.8.0-dev.19`。
- 当前结果：
  - `1536x1024` 下主区三层坐标为 `y=147 / 313 / 611`，右侧三层坐标同为 `y=147 / 313 / 611`；高度均为 `146 / 278 / 310px`。
  - 清晰度复核得到次级文字 `rgb(70, 91, 115)`、主要边框 `rgb(198, 215, 233)`，比上一版更清楚但未增加大面积重色。
  - 账户菜单尺寸为 `244x203px`，账号名称完整显示，菜单展开后没有造成页面滚动或横向溢出。
  - `1366x768`、`1536x1024`、`1920x1080` 的 `scrollWidth / scrollHeight` 均等于 viewport。
- 验证方式：
  - `python scripts/sync_feishu_docs.py`：通过；4 个文档包已检查。
  - `npm --prefix apps/frontend run test`：通过，26 个测试文件、69 个测试。
  - `npm --prefix apps/frontend run typecheck`：通过。
  - `npm --prefix apps/frontend run lint`：通过，无警告。
  - `python scripts/build_installer.py`：通过；前端生产构建、托盘图标生成和 PyInstaller 桌面目录打包成功，生成 `dist/LarkSync/LarkSync.exe`（17.5 MB）；本轮未指定 `--nsis`。
  - 截图与坐标证据位于 `docs/local_specs/visual_audit/2026-07-14-dashboard-page-pass/`，包括清晰度、三层对齐和账户菜单展开状态；本地规格目录不进入 Git。
- 遗留问题：
  - 本轮对比度增强限定在总览页和桌面壳可见区域；其他业务页在逐页优化时再按相同口径复核，避免一次性全局改色造成不可控回归。
  - 账户切换与顶栏直接退出未纳入本轮菜单；后续若加入多账号能力，需要先明确 token 隔离、任务归属和切换确认规则。

## v0.8.0-dev.18 (2026-07-14)

- 开发原因：
  - 总览页虽然已接近设计稿，但真实数据态仍会把空闲任务显示为“正在运行”。
  - 最近同步的数据量和耗时、实时连接延迟由前端推算，无法代表后端真实采集结果。
  - 历史冲突日志可能继续影响当前健康状态；侧栏同时在“活动与问题”和“冲突处理”显示同一冲突角标。
  - 长时间值、摘要说明和顶部任务按钮在有限宽度下存在截断或换行。
- 实现方式：
  - “正在运行”只使用 `status.state === running` 的任务；有任务但全部空闲时显示真实空状态和“管理任务”入口。
  - 最近同步日志缺少结构化 `volume` / `duration` 字段时统一显示 `—`；WebSocket 未提供延迟指标时显示“未采集”。
  - 实时折线只统计 `downloaded` 与 `uploaded` 事件；两类事件均为 `0` 时显示“暂无传输事件”，不绘制重叠零值折线。
  - 总体健康和冲突数量只读取未解决冲突列表；右侧“需要处理”按未解决冲突、失败问题、删除队列顺序选取预览。
  - 设计样例不再按任务数量自动启用，仅允许开发环境通过 `?ui-demo=dashboard` 显式开启。
  - 摘要卡值改为单行完整显示，说明最多展示两行；最近同步长值使用 `21px` 字号。
  - 侧栏只在“冲突处理”保留未解决冲突角标；顶部和快速操作统一使用“任务启停”，按钮固定单行。
  - Git 忽略规则补充仓库根 `%TEMP%/` 和后端 `.tmp-tests-root/`，避免测试与打包临时文件进入版本归档。
  - 版本推进到 `v0.8.0-dev.18`。
- 当前结果：
  - 真实数据页能区分无任务、任务均空闲和任务运行中三种状态。
  - 健康状态不再受已解决历史冲突日志污染，也不再展示前端推测的吞吐、耗时或延迟。
  - `1536x1024` 设计样例页保持四摘要卡、主列双面板和 `316px` 右轨结构；真实数据页的“15 小时前”和三类待处理摘要均完整可读。
  - `1366x768`、`1536x1024`、`1920x1080` 截图未发现横向溢出、模块错位或顶部按钮换行。
- 验证方式：
  - `python scripts/sync_feishu_docs.py`：通过；4 个飞书文档包已检查，manifest 已刷新。
  - `npm --prefix apps/frontend run test`：通过，26 个测试文件、69 个测试。
  - `npm --prefix apps/frontend run typecheck`：通过。
  - `npm --prefix apps/frontend run lint`：通过，无警告。
  - `npm --prefix apps/frontend run build`：通过，Vite 生产产物成功生成。
  - `python scripts/build_installer.py`：通过；前端构建、托盘图标生成和 PyInstaller 桌面目录打包成功，生成 `dist/LarkSync/LarkSync.exe`（17.5 MB）；本轮未指定 `--nsis`，未生成用户级安装器。
  - 设计与真实数据截图位于 `docs/local_specs/visual_audit/2026-07-14-dashboard-page-pass/`；该目录属于本地规格资料，不进入 Git。
- 遗留问题：
  - 后端当前没有提供结构化传输字节数、单事件耗时和 WebSocket RTT；总览页保持 `—` / “未采集”，后续接入真实字段前不做推算。
  - 本轮只收口总览页；后续页面继续按同一套“契约、失败测试、实现、真实数据截图、多尺寸验收”流程逐页完善。

## v0.8.0-dev.17 (2026-07-14)

- 开发原因：
  - 总览页已完成模块级对照，其余桌面页面仍存在模块顺序、列宽、纵向密度和设计稿不一致的问题。
  - 活动与冲突页顶部统计卡挤占主要工作区；设置页仍以 OAuth 表单开场；新建任务仍是逐页小弹窗。
- 实现方式：
  - 任务列表收紧为 `1120px` 固定表格基线并将行高改为 `py-3`；隔离测试库增加 7 条禁用 `is_test` 任务，总计 8 条任务。
  - 任务详情主区与检查器改为 `1fr + 300px`；本地/同步/云端路径区中轴固定为 `112px`。
  - 设置页重排为飞书账号、当前设备、默认同步策略、忽略规则和高级 OAuth；同步频率保留在可展开的“计划设置”。
  - 新建任务改为同屏五列：本地目录、云端目录、同步模式、删除与忽略、风险摘要；共享链接和高级同步选项保持可展开。
  - 活动与问题页移除四张顶部统计卡，主工作区改为 `280px + 1fr + 400px`；冲突页改为 `280px + 1fr + 320px`。
  - 更新维护页保持 `1fr + 360px`，将更新主模块和安装 handoff 明确命名为“更新流程”“安装与交接”。
  - 版本推进到 `v0.8.0-dev.17`。
- 当前结果：
  - `1366x768` 与 `1920x1080` 下页面滚动尺寸均等于 viewport，设置页无白边和横向溢出。
  - 任务列表可在一个 `1536x1024` 画布内展示 8 条任务，与设计稿的数据密度一致。
  - 设置页首屏可以完整看到五个设计模块；新建任务五个阶段同屏可比较，并保留真实创建流程。
- 验证方式：
  - 页面截图位于 `docs/local_specs/visual_audit/2026-07-14-all-pages-pass/`。
  - `final-settings-1366x768.png` 与 `final-settings-1920x1080.png` 验证最小和大窗口同比缩放。
  - `final-tasks-clean2-1536x1024.png` 验证 8 行任务数据密度。
  - `npm --prefix apps/frontend run test`：通过，25 个测试文件、64 个测试。
  - `npm --prefix apps/frontend run typecheck`：通过。
  - `npm --prefix apps/frontend run lint`：通过，无警告。
  - `npm --prefix apps/frontend run build`：通过，Vite 产物成功生成。
  - `python -m pytest -q`（`apps/backend`）：通过，后端测试进度达到 `100%`，退出码 `0`。
- 遗留问题：
  - 冲突页“保留双方”仍受后端缺少 `keep_both` 策略限制，页面明确禁用并说明原因。
  - 活动页的事件详情依赖真实失败/冲突运行数据；无问题任务会保持设计化空状态。

## v0.8.0-dev.16 (2026-07-14)

- 开发原因：
  - 总览页应用壳仍存在侧栏偏白、内容区下半部偏蓝、右上角重复窗口控制符和上下状态栏基线不齐的问题。
  - 本轮只调整桌面壳背景与对齐，不改变总览业务模块尺寸和数据行为。
- 实现方式：
  - 侧栏使用不透明 `#f9fbfd`；顶栏、底栏和外层画布使用 `#fdfdfd`。
  - 主内容背景改为 `#fbfcfe` 到 `#fcfdfe` 的低对比度纵向渐变，移除透视线叠层。
  - 删除前端硬编码的最小化、最大化和关闭字符，避免与 Windows 原生标题栏重复。
  - 顶栏上内边距从 `16px` 收为 `8px`；底栏左内边距改为 `36px`，使两者首项均从设计坐标 `x=256` 开始。
  - 版本推进到 `v0.8.0-dev.16`。
- 当前结果：
  - `1536x1024` 下侧栏、顶栏、主区和底栏色值分别为 `rgb(249,251,253)`、`rgb(253,253,253)`、`rgb(251,252,254)` 和 `rgb(253,253,253)`。
  - 主内容仍为 `x=220 y=88 w=1316 h=858`，右侧轨道和总览模块坐标未被本轮调整扰动。
  - `1080x720`、`1440x900`、`1536x1024`、`1920x1080` 的页面滚动尺寸均等于 viewport，额外窗口控制字符数量为 `0`。
- 验证方式：
  - `npm --prefix apps/frontend run test -- App.test.tsx DesktopShellStatus.test.tsx`：通过，2 个测试文件、7 个测试。
  - `npm --prefix apps/frontend run typecheck`：通过。
  - `npm --prefix apps/frontend run lint`：通过。
  - 最终并排图位于 `docs/local_specs/visual_audit/2026-07-14-dashboard-shell-pass/compare-dashboard-design-vs-actual-final.png`。
- 遗留问题：
  - 设计稿包含示意窗口控制符；桌面程序已有 Windows 原生标题栏，本轮明确不在 Web 内容中重复绘制。
  - 总览页以外页面仍需按同一截图对照流程逐页收敛。

## v0.8.0-dev.15 (2026-07-10)

- 开发原因：
  - 总览页整页结构已接近设计稿，但模块放大对照仍能看到状态样式、进度布局、图标语义、右轨内部层级和桌面壳信息结构差异。
  - 本轮继续以 `docs/local_specs/design_artifacts/v0.8.0/light/03-dashboard-light-v3.png` 为唯一视觉基准。

- 实现方式：
  - 摘要卡统一为 `8px` 圆角和低强度阴影；健康盾牌、运行波形、最近时钟和待处理图标按设计稿改为不同的图标框架。
  - 正在运行表把进度改为“百分比在上、进度条在下”；运行状态改为色点 + 文本；文件夹和资料库图标移除底框。
  - 最近同步表按设计稿重分配列宽；成功状态改为圆形勾选 + 文本；文件夹操作移除圆形按钮外框；底部入口补齐右侧箭头。
  - 需要处理模块改为告警标题、文档名称、目录和时间四层结构；开发样例时间固定为 `10:24`，避免 Unix 早期时间戳造成错误展示。
  - 快速操作按钮固定为 `54px` 高、`12px` 行列间距，并替换为同步、暂停、分支冲突和文件搜索图标。
  - 实时连接增加流入/流出方向图标与行分隔；调整开发样例出站折线，使蓝绿曲线层级接近设计稿。
  - 左侧栏 logo 固定为 `132x21px`，导航起点固定为 `y=108`，六项导航使用 `44px` 高和 `12px` 间距，并替换为设计语义图标。
  - 顶栏操作区采用显式间距；账号头像与分隔线位置向设计稿收敛。
  - 底栏改为“后端进程 / 进程名 / 运行状态 / 端口 / WebSocket / 数据库 / 版本 / 最近同步”顺序；端口由 Vite 构建环境注入，隔离测试显示真实 `18000`。
  - 版本推进到 `v0.8.0-dev.15`。

- 当前结果：
  - `1536x1024` 主 Grid 为 `x=248 y=111 w=1260 h=810`；摘要区为 `x=248 y=147 w=924 h=146`；右轨为 `x=1192 y=111 w=316 h=810`。
  - 左栏六项导航的 `y` 坐标依次为 `108 / 164 / 220 / 276 / 332 / 388`，与设计节奏一致。
  - `1080x720`、`1440x960`、`1536x1024`、`1920x1080` 均满足 `scrollWidth == clientWidth`，无页面级横向滚动和外层白边。
  - 最终并排图位于 `docs/local_specs/visual_audit/2026-07-10-dashboard-detail-pass/compare-dashboard-design-vs-actual-final.png`。

- 验证方式：
  - `python scripts/sync_feishu_docs.py`：通过，4 个文档包均已检查。
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx DesktopShellStatus.test.tsx`：通过，2 个测试文件、4 个测试。
  - `npm --prefix apps/frontend run typecheck`：通过。
  - `npm --prefix apps/frontend run lint`：通过。
  - Chrome headless 使用禁用 GPU 合成模式重新抓取 `1536x1024`，控制台错误数为 `0`。

- 遗留问题：
  - 真实账号名、开发端口、开发版本和 imagegen 位图字体细节会与设计稿样例不同；这些差异保留真实环境值，不做伪造。
  - 总览页之外的页面仍需按同一模块级截图对照流程逐页收敛。

## v0.8.0-dev.14 (2026-07-09)

- 目标：
  - 针对总览页第一轮截图对照后仍可见的壳层与摘要卡偏差继续收敛。
  - 本轮只处理视觉一致性，不改同步业务逻辑和接口数据结构。
  - 继续以 `03-dashboard-light-v3.png` 为设计基准。

- 实现：
  - 顶部状态区从 `StatusPill` 胶囊改为色点 + 文本 + 分隔线。
  - 左侧栏品牌图从 `36px` 高度回收到 `28px`，接近设计稿比例。
  - `StatCard` 增加 `iconFrame="plain"`，支持首张健康卡使用无底色大图标。
  - `IconShieldCheck` 改为填充式盾牌 + 白色勾选，贴近设计稿健康卡视觉。
  - 统计卡非首张图标从 `28px` 调整为 `32px`，保持图标与圆形底的层级。
  - 长值字号从 `23px` 调整为 `24px`，在保留 `2 分钟前` 完整显示的前提下接近设计稿。
  - 版本推进到 `v0.8.0-dev.14`。

- 结果：
  - `1536x1024`、`1440x960`、`1080x720`、`1920x1080` 均无页面级横向滚动。
  - `1536x1024` 总览 Grid 保持 `x=248 y=111 w=1260 h=810`。
  - `1536x1024` 摘要卡 Grid 保持 `x=248 y=147 w=924 h=146`。
  - 顶部状态区、左侧品牌区和健康卡盾牌已按第二轮对照图收敛。
  - 新增并排对照图：
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-codex-method/compare-dashboard-design-vs-actual-after-v2.png`

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - `npm --prefix apps/frontend run lint`
  - `cd apps/backend && python -m pytest tests/test_version.py`
  - `git diff --check`
  - Chrome headless 重新生成总览页 1080/1440/1536/1920 截图。

- 遗留问题：
  - 真实账号名、底栏真实错误、系统字体渲染和 imagegen 位图细节仍会与设计稿存在少量差异。
  - 总览页之外的页面仍需逐页执行同样的设计对照流程。

## v0.8.0-dev.13 (2026-07-09)

- 目标：
  - 按 codex-companion 的“设计稿 -> 页面契约 -> 模块审计 -> 实现 -> 截图验证”方法继续完善总览页。
  - 先把总览页本地 `ui-contract` 和模块审计落地，再做页面细节修正。
  - 聚焦当前截图中仍明显偏离 `03-dashboard-light-v3.png` 的模块内部差异。

- 实现：
  - 新增本地契约文档：
    - `docs/local_specs/desktop_dashboard_ui_contract_v0.8.0-dev.13.md`
    - `docs/local_specs/design_review/dashboard-block-audit-v0.8.0-dev.13.md`
  - 生成当前基线截图：
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-codex-method/actual-dashboard-1536x1024-before.png`
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-codex-method/actual-dashboard-1440x960-before.png`
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-codex-method/actual-dashboard-1080x720-before.png`
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-codex-method/actual-dashboard-1920x1080-before.png`
  - 总览页摘要卡图标改为更贴近设计稿语义：
    - 总体状态：shield check。
    - 任务运行中：pulse circle。
    - 最近同步：clock。
    - 待处理项：alert circle。
  - `StatCard` 为长值使用更小字号，避免 `2 分钟前` 被截断。
  - `StatCard` 提示文案改为 `11px` 并保留 `title`，避免“冲突 1 个 / 问题 0 个”视觉截断。
  - showcase 运行行增加 icon variant：
    - 项目文档、设计资源使用黄色文件夹。
    - 公开资料库使用蓝色 globe。
  - 运行表速度列增加单行约束，避免 `12.4 MB/s` 分成两行。
  - showcase 最近同步的“变更文件”列改为设计稿中的计数式摘要：`128 / 86 / 512 / 73 / 201`。
  - showcase 右侧“需要处理”固定展示冲突样例，避免 dev-test 历史待删除事件抢占视觉基线。
  - showcase 实时连接使用稳定指标：
    - 连接延迟：`24 ms`。
    - 数据流入：`18.6 MB/s`。
    - 数据流出：`12.3 MB/s`。
    - 蓝绿双折线使用稳定序列，避免历史事件造成单点尖峰。
  - 版本推进到 `v0.8.0-dev.13`。

- 结果：
  - `1536x1024`、`1440x960`、`1080x720`、`1920x1080` 均无页面级横向滚动。
  - `1536x1024` 总览 Grid 仍保持 `x=248 y=111 w=1260`。
  - `1536x1024` 右轨仍保持 `x=1192 y=111 w=316`。
  - `2 分钟前`、`冲突 1 个 / 问题 0 个`、`冲突待处理`、`24 ms` 和 `12.4 MB/s` 均在最终截图中可见。
  - 新增并排对照图：
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-codex-method/compare-dashboard-design-vs-actual-after.png`

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - `npm --prefix apps/frontend run lint`
  - Chrome headless 生成 1080/1440/1536/1920 四张总览页截图。

- 遗留问题：
  - 设计稿是 imagegen 位图，真实字体、账号名、底栏真实错误信息和图标线条仍会存在少量天然差异。
  - 本轮只完善总览页；任务、任务详情、活动与问题、冲突、设置、维护和授权页仍需按同一方法逐页执行。

## v0.8.0-dev.12 (2026-07-09)

- 目标：
  - 修正上一轮固定 frame 居中导致的大窗口外层白边。
  - 按设计稿原始尺寸重新建立总览页一比一对照基准。
  - 继续把总览页按模块向 `03-dashboard-light-v3.png` 收敛。

- 实现：
  - 设计基准从 `1440x960` 改为设计稿原图 `1536x1024`。
  - 最小缩放改为 `1080 / 1536`，对应最小窗口 `1080x720`。
  - `useDesktopViewportScale` 不再返回居中 frame。
  - 缩放后的 shell 使用 `width: calc(100vw / scale)` 与 `height: calc(100vh / scale)`。
  - 外层 viewport 固定为 `100vw x 100vh`。
  - App 外层移除居中布局和大阴影容器。
  - 这样 1440、1536、1920 宽度都不会露出外层背景边。
  - 顶栏高度从 `56px` 调整为 `88px`。
  - 顶栏补充窗口控制视觉区。
  - 主工作区边距调整为 `px-7 py-[23px]`。
  - 总览页标题去掉多余边框卡片和右侧状态胶囊。
  - 摘要卡高度、图标尺寸、字号和内边距按设计稿放大。
  - 总览页改为左主列 + `316px` 右侧模块轨。
  - 右侧模块轨从标题行同高处开始，不再从摘要卡行开始。
  - 右侧“需要处理 / 快速操作 / 实时连接”分别固定为 `214px / 188px / 336px`。
  - 左侧“正在运行 / 最近同步”分别固定为 `278px / 310px`。
  - 运行表重新分配列宽，操作列放宽到 `7%`，避免按钮被挤窄。
  - 最近同步表行高压缩到约 `38px`，5 条样例和底部入口均保持可见。
  - 顶栏可见状态收敛为“后端运行中 / WebSocket 已连接”。
  - 顶栏右侧操作区固定为 `430px`，按钮和账号区不再被挤出画布。
  - dev 测试样例任务稳定启用 showcase 数据，不再因历史事件数量超过 16 条而退回单行真实数据。
  - 左侧栏移除设计稿中没有的三行连接状态和“在浏览器中打开”按钮。
  - 左侧栏底部改为单个折叠控制视觉位。
  - 新截图目录：
    - `docs/local_specs/visual_audit/2026-07-09-responsive-scale-fix/dashboard-1440x960.png`
    - `docs/local_specs/visual_audit/2026-07-09-responsive-scale-fix/dashboard-1920x1080.png`
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-detail-pass/actual-dashboard-1536x1024-after-b.png`
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-detail-pass/compare-dashboard-design-vs-actual-after-b.png`
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-pixel-pass/actual-iab-1536x1024-final-tight.png`
    - `docs/local_specs/visual_audit/2026-07-09-dashboard-pixel-pass/compare-dashboard-design-vs-actual-final-tight.png`
  - 版本推进到 `v0.8.0-dev.12`。

- 结果：
  - 1920x1080 截图不再出现左右外层白边。
  - 1536x1024 截图已可与设计稿原图直接并排比较。
  - 总览页顶栏、标题、摘要卡、运行表、最近同步、右侧栏和左侧栏底部比 `v0.8.0-dev.11` 更接近设计稿。
  - 应用内浏览器固定 `1536x1024` 复核后，shell 关键坐标为：
    - 左侧栏：`x=0 y=0 w=220 h=1024`。
    - 顶栏：`x=220 y=0 w=1316 h=88`。
    - 主区：`x=220 y=88 w=1316 h=858`，`scrollHeight=858`。
    - 底栏：`x=220 y=946 w=1316 h=78`。
  - 总览页模块关键坐标为：
    - 顶栏操作区：`x=1074 y=32 w=430 h=40`。
    - 摘要卡行：`y=148 h=146`。
    - 正在运行：`x=248 y=314 w=924 h=278`。
    - 最近同步：`x=248 y=612 w=924 h=310`。
    - 需要处理：`x=1192 y=112 w=316 h=214`。
    - 快速操作：`x=1192 y=342 w=316 h=188`。
    - 实时连接：`x=1192 y=546 w=316 h=336`。
  - 连接状态仍保留在顶栏和底栏，不再重复堆在左侧栏底部。

- 验证：
  - `npm --prefix apps/frontend run test -- App.test.tsx DesktopShellStatus.test.tsx DashboardPage.test.tsx`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - Chrome headless 截图验证 1440x960、1536x1024、1920x1080。
  - 应用内浏览器固定 `1536x1024` 截图验证 `actual-iab-1536x1024-final-tight.png`。

- 遗留问题：
  - 当前轮只继续收口了 shell 和总览页。
  - 设计稿中的窗口控制为静态视觉位，当前还不是原生窗口控制按钮。
  - 总览页仍存在少量由真实字体渲染和 imagegen 位图文本造成的 1-3px 视觉差。
  - 任务页、任务详情页、活动与问题页、冲突页、设置页、维护页和授权页还需要按同样方法逐页截图对照。

## v0.8.0-dev.11 (2026-07-09)

- 目标：
  - 修正桌面页面随窗口尺寸变化时结构断点过多、最小窗口和设计稿不一致的问题。
  - 参考 codex-companion 的固定画布缩放方法，让桌面端先保持同一套浅色科技风页面结构。
  - 最小窗口按设计图完整显示，窗口变大时整体同步放大，而不是各页面分别切换版式。

- 实现：
  - 对照 codex-companion 的 `BrowserWindow minWidth/minHeight` 与 `.app-shell` transform scale 方案。
  - 新增 `useDesktopViewportScale`。
  - 设计画布固定为 `1440x960`。
  - 最小缩放固定为 `0.75`，对应 `1080x720`。
  - 缩放比例使用 `min(window.innerWidth / 1440, window.innerHeight / 960)`。
  - `App.tsx` 将已连接桌面壳和首次授权页都包进同一固定画布。
  - 左侧栏固定为 `220px`，不再在 1080px 下切换为图标栏。
  - 顶栏和底栏固定展示完整状态，不再按窗口高度隐藏运行数、账号、数据库、版本或最近同步。
  - 总览页固定为主列 + `300px` 右侧栏。
  - 任务详情页固定为主列 + `320px` 检查器。
  - 活动与问题、冲突处理、设置、更新维护、任务页、任务卡片、新建任务向导和首次授权页移除 viewport 断点结构。
  - 修复 `.desktop-perspective-line` 覆盖 `overflow-y-auto` 的问题，避免主工作区不能正常滚动。
  - 生产 TSX 文件中已清除 `sm:`、`md:`、`lg:`、`xl:`、`min-[...]`、`max-height` 和 `@media` 断点类。
  - 新截图目录：
    - `docs/local_specs/visual_audit/2026-07-09-responsive-scale/dashboard-1080x720.png`
    - `docs/local_specs/visual_audit/2026-07-09-responsive-scale/dashboard-1280x820.png`
    - `docs/local_specs/visual_audit/2026-07-09-responsive-scale/dashboard-1440x960.png`
    - `docs/local_specs/visual_audit/2026-07-09-responsive-scale/dashboard-1920x1080.png`
    - `docs/local_specs/visual_audit/2026-07-09-responsive-scale/tasks-1080x720.png`
    - `docs/local_specs/visual_audit/2026-07-09-responsive-scale/tasks-1440x960.png`
  - 版本推进到 `v0.8.0-dev.11`。

- 结果：
  - 1080x720 下会显示完整 1440x960 设计结构的 0.75 倍版本。
  - 1440x960 下按 1.0 倍显示设计画布。
  - 1920x1080 下按高度约束放大到 1.125 倍，结构不发生切换。
  - 左栏、顶栏、底栏、总览、任务、任务详情、活动与问题、冲突处理、设置、维护和授权页现在使用同一桌面结构。
  - `dev:test` 仍使用项目内 `data/dev-test` 数据目录，不影响已安装版程序和默认网页版本数据。

- 验证：
  - `rg -n "min-\[|sm:|md:|lg:|xl:|2xl:|max-height|@media" apps/frontend/src --glob "*.tsx" --glob "!**/*.test.tsx"`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`
  - `python -m pytest apps/backend/tests/test_version.py`
  - Chrome headless 截图验证 1080x720、1280x820、1440x960、1920x1080。

- 遗留问题：
  - 当前轮解决的是窗口配适和结构一致性。
  - 后续仍需要按“设计稿 + 真实截图 + 模块拆分”的方法，继续逐页做像素级视觉对齐。
  - 任务页截图中的测试数据仍需要继续补齐，便于审查真实表格态和任务详情态。

## v0.8.0-dev.10 (2026-07-08)

- 目标：
  - 修正“窗口配适还没做完”的问题，继续压缩桌面壳在低高度和中等宽度窗口下的占位。
  - 将总览页除明确不保留的真实吞吐/精确 ETA 之外，其余设计结构尽量收敛到页面稿。
  - 用真实截图而不是只看代码，重新核对 1080 / 1280 / 1440 三个断点。

- 实现：
  - `App.tsx` 将主工作区改为 `overflow-y-auto + overflow-x-hidden`。
  - 主工作区在常规窗口和低高度窗口分别收紧内边距。
  - `DesktopTopBar.tsx` 收紧为 56px 顶栏。
  - 顶栏在低高度窗口下压缩按钮尺寸，并隐藏低优先级运行数、待处理数和账号名。
  - `Sidebar.tsx` 在低高度窗口下继续收紧 Logo 区、导航区和底部状态区的垂直占位。
  - `DesktopStatusBar.tsx` 在低高度窗口下隐藏任务统计、前端类型、数据库、版本和最近同步文本，只保留关键状态和刷新按钮。
  - `StatCard.tsx` 将摘要卡高度、图标尺寸和数值字号继续收紧。
  - `DashboardPage.tsx` 将标题区改回“标题 + 右侧状态胶囊”。
  - 总览页移除设计稿中没有的标题副文案。
  - 总览页移除右侧“任务待处理摘要”多余卡片，只保留“需要处理 / 快速操作 / 实时连接”三段结构。
  - 右侧“实时连接”改为三行指标：连接延迟、数据流入、数据流出。
  - 运行表补回速度列、操作列和行内动作按钮。
  - 最近同步表补回数据量、耗时和末列查看入口。
  - 在 `import.meta.env.DEV` 且当前测试数据属于样例任务时，启用总览页展示态样例数据。
  - 展示态样例数据覆盖摘要卡、运行表、最近同步表和右侧实时连接速率。
  - 这样在 `dev:test` 下，即使真实任务和历史不足，也能对照设计稿审查布局与密度。
  - 使用 Chrome headless 对 `http://localhost:13666/#dashboard` 重新截图。
  - 新截图目录：
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/fix-pass-3/dashboard-1080x720.png`
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/fix-pass-3/dashboard-1280x900.png`
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/fix-pass-3/dashboard-1440x960.png`
  - 版本推进到 `v0.8.0-dev.10`。

- 结果：
  - 1440px 已恢复设计稿的主列 + 300px 右栏结构，并且总览页展示态与 `03-dashboard-light-v3.png` 更接近。
  - 1280px 下不再提前展开右侧栏，四摘要卡保持两列，主表和最近同步维持主内容优先。
  - 1080px 下左栏继续收为图标栏，顶栏和底栏占位收紧，首屏不再被壳层进一步压缩。
  - 总览页目前明确不保留的只有“真实 MB/s 吞吐”和“精确 ETA”。
  - 其余结构都已改成设计稿形态，测试环境中用稳定样例数据填满。

- 验证：
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx DesktopShellStatus.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`
  - `Invoke-WebRequest http://localhost:13666/`
  - Chrome headless 截图验证 1080x720、1280x900、1440x960。

- 遗留问题：
  - 当前这轮只继续收口了桌面壳和总览页。
  - 任务详情、活动与问题、冲突处理、设置、维护页仍需要按同样的“设计稿 + 真实截图”方法逐页继续对齐。

## v0.8.0-dev.9 (2026-07-08)

- 目标：
  - 回应总览页设计稿中出现但旧版未具备的数据能力，先判断能否实现，再决定页面是否保留。
  - 对暂时缺少真实接口的能力使用稳定占位数据，避免空页面影响真实数据态视觉审查。
  - 继续完善总览页，让右侧实时连接卡和历史测试数据能够更接近设计稿表达。

- 实现：
  - 新增本地规划文档：`docs/local_specs/desktop_overview_future_feature_plan_v0.8.0-dev.9.md`。
  - 文档将总览页能力分为“已有能力”“可做但先用派生占位数据”“暂不保留”三类。
  - 保留总体健康、运行任务数、最近同步、待处理项、正在运行表格、最近同步列表、需要处理右栏、快速操作等已有或可直接承接能力。
  - 保留连接延迟、数据流入/流出趋势、实时连接折线，但当前先从 WebSocket 状态和同步事件派生稳定占位值。
  - 暂不展示真实 MB/s 吞吐速率。
  - 暂不展示精确 ETA。
  - 原因是当前事件模型没有稳定的字节数、耗时和方向字段，空闲任务也无法推断剩余时间。
  - `DashboardPage` 新增 `buildRealtimeMetrics`。
  - `buildRealtimeMetrics` 将 `downloaded` 计入流入，将 `uploaded`、`mirrored`、`created`、`linked` 计入流出。
  - 失败、冲突和待删除事件只作为双线趋势的关注波动，不计入真实方向总数。
  - 实时连接卡展示连接延迟、数据流向和运行任务数，不再显示无来源的 `-- ms`。
  - `useWebSocketLog` 从开发环境硬编码 `hostname:8000/ws/logs` 改为同源 `/ws/events`。
  - Vite 代理继续负责将 `/ws/events` 转发到当前 `dev:test` 后端端口，避免测试后端自动换端口后页面仍连旧地址。
  - 生成总览页截图：
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/future-features-pass-2/dashboard-1280x900.png`
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/future-features-pass-2/dashboard-1440x960.png`
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/future-features-pass-2/dashboard-1920x1080.png`
  - 版本推进到 `v0.8.0-dev.9`。

- 结果：
  - 总览页的新设计能力都已标注实现边界，后续不会把占位数据误当真实后端能力。
  - 1440px 真实数据态下，右侧实时连接卡显示 `良好`，连接延迟显示稳定毫秒值，数据流向显示当前测试历史事件的流入/流出统计。
  - 1280px 下右栏继续下移，主表格保持横向滚动边界，不挤占主体。
  - 1920px 下主列和 300px 右栏比例稳定。
  - 当前页面继续承接网页版已有功能；批量暂停、真实心跳延迟、时间桶聚合和吞吐统计放入后续开发。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx DesktopShellStatus.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`
  - Chrome / Edge headless 截图验证 1280x900、1440x960、1920x1080。

- 遗留问题：
  - 连接延迟仍是由 WebSocket 状态、最近日志量和运行任务数派生的占位值。
  - 数据流向仍是从同步事件状态推断的事件数，不代表真实字节流量。
  - 批量暂停按钮当前跳转同步任务页，后续需要新增批量暂停/恢复 API 和确认弹窗。

## v0.8.0-dev.8 (2026-07-08)

- 目标：
  - 修正 `dev:test` 看起来启动成功但页面仍无数据的问题。
  - 将历史测试数据放入项目内 `data/dev-test`，用于真实数据态 UI 审查。
  - 继续按设计稿收紧总览页整体布局，重点处理统计卡、主表格、右侧上下文栏的密度差异。

- 实现：
  - `scripts/start_dev_test.mjs` 启动前会检查默认后端端口。
  - 当 `18000` 已被其他数据目录的 LarkSync 后端占用时，`dev:test` 会自动尝试 `18001` 等后续端口。
  - `apps/tray/backend_manager.py` 在显式设置 `LARKSYNC_DATA_DIR` 时，会读取已有后端 `/system/desktop/status`。
  - 只有已有后端的数据目录与当前运行目录一致时才允许复用，避免项目内测试前端连到 Temp 测试库或安装版数据。
  - 将历史库中的 1 个真实任务复制到 `data/dev-test/larksync.db`。
  - 将测试任务归属改为当前测试 OAuth 身份和当前设备。
  - 将测试任务本地目录改到项目内 `data/dev-test/sample-workspace/Test4LarkSync`。
  - 创建 Markdown / 附件占位样例文件，避免 watcher 因旧本地目录不存在而启动失败。
  - 将测试配置的自动上传 / 下载间隔调为每日固定时间，避免 UI 审查期间被高频调度日志污染。
  - 清理旧 `F:/File/Data/Test4LarkSync` 路径噪声，重建 11 条可读同步事件和 1 条未解决冲突样例。
  - 总览页移除标题行右侧重复的实时连接状态胶囊；连接状态仍由顶栏和右侧实时连接卡展示。
  - `StatCard` 高度、图标尺寸、内边距和文本行距收紧，接近 v3 设计稿摘要卡密度。
  - 总览页主面板内边距、模块间距和表格行高收紧，降低真实数据态下的纵向松散感。
  - 生成真实数据态视觉审查截图：
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/history-data/pass-3/dashboard-1440x960.png`
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/history-data/pass-3/dashboard-1280x900.png`
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/history-data/pass-3/dashboard-1920x1080.png`
    - `docs/local_specs/visual_audit/2026-07-08-dashboard/history-data/pass-3/compare-dashboard-design-vs-history-pass-3.png`
  - 版本推进到 `v0.8.0-dev.8`。

- 结果：
  - `npm run dev:test` 默认仍使用前端 `13666`，但后端端口会在默认 `18000` 被不匹配数据目录占用时自动切到 `18001`。
  - 前端代理已确认读取项目内 `data/dev-test`：1 个任务、11 条同步日志、1 条未解决冲突。
  - 1440px 总览页恢复主列 + 300px 右侧栏布局，并在真实数据态下接近设计稿的统计卡高度和表格密度。
  - 1280px 下右侧上下文栏按当前设计下移到主内容后方，主内容不横向挤压。
  - 1920px 下主列和右侧栏比例正常，底栏和侧栏没有遮挡主体内容。

- 验证：
  - `python -m pytest apps/backend/tests/test_backend_manager.py`
  - `node --check scripts/start_dev_test.mjs`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx DesktopShellStatus.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`
  - Chrome / Edge headless 截图验证 1280x900、1440x960、1920x1080。

- 遗留问题：
  - 历史库当前只有 1 个真实同步任务；设计稿的“正在运行”模块是 3 行任务态，因此该模块高度不会完全一致。
  - 如后续需要严格压测 3 行任务表格，应在 `data/dev-test` 中额外生成 2 个样例任务和对应本地目录，但不能把这些样例误当真实历史数据。

## v0.8.0-dev.7 (2026-07-08)

- 目标：
  - 修正桌面页面没有按窗口大小配适的问题。
  - 将浅色科技风设计稿和实际页面的断点行为重新对齐。
  - 先保障壳层、同步任务、活动与问题、冲突处理、更新维护不在中等窗口互相挤压。

- 实现：
  - 新增 `docs/local_specs/desktop_design_implementation_alignment_v0.8.0.md`。
  - 文档按设计稿、实现入口、关键布局、当前偏差和修正动作建立页面矩阵。
  - 新增 `docs/local_specs/visual_audit/2026-07-08-dashboard/README.md`。
  - 用隔离 `dev:test` 对总览页截取 1080x720、1280x820、1440x960、1920x1080 实际页面。
  - 生成 `compare-dashboard-design-vs-actual-1440.png`，并排对照 `03-dashboard-light-v3.png` 与 1440 实际截图。
  - 生成 `compare-dashboard-responsive-strip.png`，对照四个实际窗口尺寸。
  - 左侧栏在 1080px 到 1179px 窗口自动收为 72px 图标栏。
  - 左侧栏在 1180px 以上恢复 220px 完整导航，对齐 `light-prompts.md` 中的 220px 设计约束。
  - 顶栏在窄窗口将“立即同步”和“暂停”压缩为图标按钮。
  - 底栏在窄窗口隐藏版本和最近同步等低优先级文本。
  - 主工作区内边距从固定 24px 改为 12px / 20px / 24px 分段。
  - 总览页摘要卡在 1440px 以上恢复四列。
  - 总览页主列 + 300px 右侧上下文栏在 1440px 以上展开，对齐 v3 设计稿基准。
  - 总览页将四摘要卡移入左主列，使右侧上下文栏从摘要卡顶部开始，而不是在摘要卡下方才出现。
  - 总览页摘要卡改为圆形状态图标 + 指标文本的横向结构，接近设计稿卡片视觉重心。
  - 总览页右侧“实时连接”从柱状图改为蓝/绿双折线图。
  - 总览页“正在运行”模块移除设计稿中不存在的右上刷新按钮和说明行。
  - 总览页“最近同步”的历史入口移动到底部，接近设计稿链接位置。
  - 活动与问题页完整三栏工作台从 1440px 后移到 1760px。
  - 冲突处理页完整三栏工作台和版本双列从 1440px/1500px 后移到 1760px。
  - 更新与维护页双栏工作台从 1440px 后移到 1760px。
  - 同步任务表格最小宽度从 1180px 降为 980px。
  - 同步任务表格的云端目录列在 1320px 以上展示。
  - 同步任务展开策略四列从 1440px 后移到 1760px。
  - 后端版本同步到 `v0.8.0-dev.7`，避免底栏版本和文档版本不一致。

- 结果：
  - 1080px 最小桌面窗口不再从左侧栏和主区边距开始挤占页面。
  - 1440px 窗口中，总览页恢复设计稿的 300px 右侧上下文栏；活动、冲突和维护页仍保持主内容优先，不提前展开完整三栏工作台。
  - 1760px 以上再进入活动、冲突和维护页的完整多栏设计结构。
  - 1920px 以上继续承接任务详情的检查器布局。
  - 本轮没有变更后端同步、OAuth、冲突解决和更新安装接口。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test -- App.test.tsx DesktopShellStatus.test.tsx TasksPage.test.tsx ActivityIssuesPage.test.tsx ConflictResolutionPage.test.tsx MaintenancePage.test.tsx`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - Chrome headless 截图：`actual-dashboard-1080x720.png`
  - Chrome headless 截图：`actual-dashboard-1280x820.png`
  - Chrome headless 截图：`actual-dashboard-1440x960.png`
  - Chrome headless 截图：`actual-dashboard-1920x1080-rerun.png`
  - Chrome headless 截图：`actual-dashboard-1440x960-module-pass-2.png`
  - 模块对照图：`modules-pass-2/dashboard-module-contact-sheet.png`

- 遗留问题：
  - 仍需要通过 `npm run dev:test` 做 1080x720、1280x820、1440x960、1920x1080 的人工视觉验收。
  - 新建任务向导、设置页和首次授权页的细节仍需继续按页面矩阵逐项核验。
  - OAuth 测试仍要求飞书开发者后台配置 `http://localhost:13666/auth/callback` 作为 Redirect URI。

## v0.8.0-dev.6 (2026-07-08)

- 目标：
  - 将桌面版主界面继续对齐浅色科技风视觉稿。
  - 优先修正桌面壳、总览标题区和同步任务页与设计稿不一致的问题。
  - 保持本轮只改页面与交互骨架，不改同步核心和数据目录策略。

- 实现：
  - App 主工作区增加冷白浅蓝网格和透视线背景。
  - 顶栏改为全局状态序列，展示后端、WebSocket、飞书授权、运行任务数和待处理数。
  - 左侧栏收敛为 Logo、主导航、问题角标、飞书授权、后端、WebSocket 和浏览器 fallback。
  - 总览、活动与问题、冲突处理、设置、更新与维护补齐页面级标题和主操作。
  - 同步任务页从旧大卡片列表改为高密度表格。
  - 同步任务页新增搜索、状态筛选、同步模式筛选和健康筛选。
  - 同步任务表格保留启用/停用、立即同步、详情入口、策略展开和删除任务能力。
  - 表格展开行继续承载同步模式、更新模式、MD 上传模式和删除策略编辑。

- 结果：
  - 桌面版页面更接近 `docs/local_specs/design_artifacts/v0.8.0/light/` 下的浅色科技风视觉稿。
  - 同步任务页在 1080 px 以上保持表格主体验，路径和 token 使用截断展示。
  - 页面改版没有变更后端同步、OAuth、冲突解决或更新安装接口。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- TasksPage.test.tsx TaskPanels.test.tsx DashboardPage.test.tsx DesktopShellStatus.test.tsx ActivityIssuesPage.test.tsx ConflictResolutionPage.test.tsx SettingsPage.test.tsx`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`

- 遗留问题：
  - 本轮完成代码层对齐和自动化验证，仍建议通过 `npm run dev:test` 做一次桌面窗口人工视觉验收。
  - OAuth 测试仍要求飞书开发者后台配置 `http://localhost:13666/auth/callback` 作为 Redirect URI。

## v0.8.0-dev.5 (2026-07-08)

- 目标：
  - 将隔离开发测试数据固定放回项目目录。
  - 避免 `npm run dev:test` 默认向系统临时目录写入数据。
  - 继续保证安装版运行时不被开发测试入口影响。

- 实现：
  - `scripts/start_dev_test.mjs` 的默认 `LARKSYNC_DATA_DIR` 改为仓库内 `data/dev-test`。
  - 保留 `LARKSYNC_DATA_DIR` 环境变量覆盖能力。
  - 项目内 `data/dev-test/config.json` 预填测试 OAuth 配置。
  - 测试 OAuth Redirect URI 使用 `http://localhost:13666/auth/callback`。
  - 测试 token 存储继续使用 `file`。

- 结果：
  - 默认 `npm run dev:test` 使用项目内 `data/dev-test` 数据目录。
  - 测试配置不读取安装版用户数据目录。
  - 测试配置不读取或写入安装版 Windows 凭据管理器里的 `larksync` token。

- 验证：
  - `node --check scripts/start_dev_test.mjs`
  - `python -m pytest tests/test_desktop_window.py tests/test_tray_config.py`
  - `python -m py_compile apps/tray/desktop_window.py apps/tray/tray_app.py apps/tray/config.py`
  - `npm --prefix apps/frontend run typecheck`

- 遗留问题：
  - 如果旧的 `dev:test` 后端进程仍在运行，它仍会继续使用启动时的旧环境变量。
  - 需要重启 `npm run dev:test` 后才会切换到项目内 `data/dev-test`。

## v0.8.0-dev.4 (2026-07-07)

- 目标：
  - 允许安装版 LarkSync 正在运行时查看桌面化开发效果。
  - 避免默认开发入口抢占安装版后端端口、托盘单实例锁或凭证存储。
  - 保持当前阶段测试目标聚焦“桌面版承接网页版本已有功能”。

- 实现：
  - 根包新增 `npm run dev:test`。
  - `dev:test` 默认使用后端端口 `18000`。
  - `dev:test` 默认使用前端端口 `13666`。
  - `dev:test` 默认使用单实例锁端口 `48911`。
  - `dev:test` 使用独立测试数据目录，后续在 `v0.8.0-dev.5` 改为项目内 `data/dev-test`。
  - `dev:test` 默认设置 `LARKSYNC_TOKEN_STORE=file`，不读取或写入安装版 Windows 凭据管理器里的 `larksync` token。
  - 托盘配置支持通过 `LARKSYNC_BACKEND_PORT` 和 `LARKSYNC_VITE_DEV_PORT` 改端口。
  - 托盘单实例锁支持通过 `LARKSYNC_LOCK_PORT` 改锁端口。
  - Vite 代理支持通过环境变量指向隔离后端。
  - Vite 开发日志写入当前 `LARKSYNC_DATA_DIR/logs`。
  - 桌面窗口 fallback 输出补充具体原因。
  - 缺少 `pywebview` 时会明确提示“未检测到 pywebview/webview 模块”。

- 结果：
  - 安装版继续占用 `8000` 和默认托盘锁时，可以用 `npm run dev:test` 启动隔离开发预览。
  - `http://localhost:13666` 用于隔离测试前端。
  - `http://127.0.0.1:18000` 用于隔离测试后端。
  - 默认 `npm run dev` 保持原开发入口语义。
  - 本机 `C:\Python314\python.exe` 缺少 `pywebview` 是“桌面窗口不可用”的直接原因。
  - 已执行 `python -m pip install "pywebview>=5.0"`，当前环境可以 import `webview`。

- 验证：
  - `python -c "import importlib.util, webview; print(importlib.util.find_spec('webview'))"`
  - `python -m pytest tests/test_tray_config.py`
  - `python -m pytest tests/test_desktop_window.py tests/test_tray_config.py`
  - `python -m py_compile apps/tray/config.py apps/tray/tray_app.py`
  - `python -m py_compile apps/tray/desktop_window.py apps/tray/tray_app.py apps/tray/config.py`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run build`

- 遗留问题：
  - `dev:test` 使用独立测试数据目录，因此不会直接展示安装版真实任务数据。
  - 如需用真实任务验证承接效果，应先复制数据到测试目录或暂停安装版后再做专门回归。

## v0.8.0-dev.3 (2026-07-07)

- 目标：
  - 为首次授权页补齐 `lark-cli` 辅助诊断入口。
  - 降低后续设备码/二维码授权方案验证成本。
  - 保持 LarkSync 原生 OAuth 和本地加密凭证仍为主流程。

- 实现：
  - 新增 `LarkCliAuthStatus` 后端只读探测服务。
  - 后端固定执行 `lark-cli auth status --json --verify`。
  - 后端设置 `LARKSUITE_CLI_NO_UPDATE_NOTIFIER=1` 和 `LARKSUITE_CLI_NO_SKILLS_NOTIFIER=1`。
  - Windows 下隐藏 CLI 检测进程窗口。
  - `/auth/cli/status` 返回 CLI 安装状态、身份类型、用户可用性、scope 数量、docs scope 检测和 drive scope 检测。
  - `/auth/cli/status` 不返回 raw scope、access token、refresh token 或 open_id，只返回 `open_id_present` 布尔值。
  - 首次授权页右侧面板新增“CLI 辅助授权”。
  - 前端展示 CLI 检测状态、复制状态检查命令、设备码命令和二维码命令。
  - 前端文案明确当前主流程仍使用 LarkSync 原生 OAuth。

- 结果：
  - 未安装 `lark-cli` 时，页面提示可继续使用原生 OAuth。
  - 已安装且用户身份可用时，页面展示 `CLI 可用`、用户名称和 docs/drive 权限检测结果。
  - 该能力只做状态诊断，不读取或导入 CLI token。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `python -m pytest tests/test_lark_cli_auth_service.py tests/test_auth_api.py`
  - `python -m py_compile src/services/lark_cli_auth_service.py src/api/auth.py src/services/__init__.py`
  - `npm --prefix apps/frontend run test -- OnboardingWizard.test.tsx`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`

- 遗留问题：
  - 本轮只实现 CLI 状态探测。
  - 设备码登录和二维码登录仍需后续专项方案确认后再接入主流程。

## v0.8.0-dev.1 (2026-07-06)

- 目标：
  - 在桌面化重构前先整理 Logo 资产。
  - 保留旧版“无限循环箭头 + 鸟形 + 蓝绿渐变”的识别点。
  - 解决旧资产白边大、透明导出不稳定、小尺寸托盘图标不稳定的问题。

- 实现：
  - 新增 `scripts/generate_logo_assets.py`，以旧版原图为唯一视觉来源，统一导出品牌 PNG、Windows ICO、前端 favicon 和托盘四态图标。
  - 背景移除算法只处理与画布边缘连通的近白背景，保留旧 Logo 内部白色鸟眼和原始形状。
  - 覆盖兼容旧文件名的品牌 PNG 和 `LarkSync.ico`，避免现有 README、安装包和构建脚本引用失效。
  - 将重做前的品牌、前端和托盘图标复制到 `assets/branding/archive/2026-07-06-original/`。
  - 更新 `scripts/process_logo.py`，当源图已经是透明背景时保留白色细节，不再误删图标内部白色眼睛。
  - 更新 `apps/tray/icon_generator.py`，继续从同一品牌图标派生 `idle`、`syncing`、`paused`、`error` 四态，保留原有整图增强/灰度/红色着色方式。

- 结果：
  - 新版资产保持旧版 Logo 视觉设计，不再引入新几何图形。
  - `apps/frontend/public/logo-horizontal.png` 输出为透明 PNG。
  - `apps/tray/icons/` 四态图标均为 64 x 64 透明 PNG。
  - `assets/branding/LarkSync.ico` 继续作为 Windows 安装包图标入口。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `python scripts/generate_logo_assets.py`
  - `python -m py_compile scripts/generate_logo_assets.py scripts/process_logo.py apps/tray/icon_generator.py`
  - `python scripts/process_logo.py`
  - `python apps/tray/icon_generator.py`
  - 使用 Pillow 检查品牌 PNG、favicon、ICO 和托盘四态图标尺寸与 alpha 通道。

- 遗留问题：
  - 当前资产严格基于旧版原图；如需要更高清的同款 Logo，需要提供旧设计的原始矢量文件或更高质量源图。

### 2026-07-07 桌面总览与任务详情布局

- 原因：
  - 用户评审指出总览页和任务详情页仍有多个框互相挤占的问题。
  - 旧前端总览页仍是深色双列卡片结构，与 v0.8.0 桌面浅色科技风壳层不一致。
  - 代码中没有独立任务详情页，任务级信息仍混在任务卡展开区域里。

- 实现：
  - 用 imagegen 重新生成 `03-dashboard-light-v3.png` 和 `06-task-detail-light-v3.png`。
  - 将 v3 设计稿归档到 `docs/local_specs/design_artifacts/v0.8.0/light/`。
  - 更新本地设计索引和 prompt 归档，明确总览页主列 + 300px 右轨、任务详情页主列 + 300px 检查器。
  - 重写 `DashboardPage` 为浅色科技风布局。
  - 总览页上方固定四张摘要卡。
  - 总览页主列只承载“正在运行”和“最近同步”两个大面板。
  - 总览页右侧只承载“需要处理”“快速操作”“实时连接”。
  - 新增 `TaskDetailPage`。
  - 任务详情页主列承载任务标题、路径关系、当前运行和运行历史。
  - 任务详情页右侧检查器承载问题摘要、任务操作、策略摘要、忽略目录和危险操作。
  - 任务列表卡新增“查看详情”入口，App 在“同步任务”页签内切换列表和详情。
  - `StatusPill` 和 `StatCard` 改为浅色 token，避免旧暗色组件混入桌面壳。

- 结果：
  - 1440px 宽度下，总览页主列宽度约 806px，右轨宽度 300px。
  - 总览页实机检查未出现横向溢出。
  - 任务详情页已具备独立页面入口和可测试布局骨架。
  - 任务详情页危险操作使用既有 `reset-links` 和删除任务确认，不新增未知后端字段。

- 验证：
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`（22 files / 55 tests passed）
  - 浏览器打开 `http://127.0.0.1:3666`，按 1440 x 960 视口截图验证总览页。
  - 浏览器布局检测结果：`scrollWidth=1440`，`clientWidth=1440`，无横向溢出。
  - 总览页检测到主列面板宽度约 806px，右侧检查轨宽度 300px。

- 遗留问题：
  - 首轮实现时本地数据库任务数为 0，未创建临时任务污染数据，因此当时没有用真实任务数据截图验证任务详情页。
  - 任务详情页布局已通过 `TaskDetailPage.test.tsx` smoke test 验证。
  - WebSocket 在本地浏览器验证时返回 403，页面能显示重连态；后续需要在桌面壳鉴权上下文稳定后继续验证实时日志连接。

### 2026-07-07 总览与任务详情布局二次收口

- 原因：
  - 用户评审指出总览页和任务详情页仍有框体互相挤占的问题。
  - 现有两栏断点按浏览器视口触发，没有扣除左侧 248px 导航和主内容区 48px 内边距。
  - 任务详情页原 `minmax(760px,1fr) + 300px` 检查器在 1280px 桌面窗口下会超出真实工作区。
  - 顶部栏在 1280px 宽度会同时显示页面摘要、状态胶囊、操作按钮和账号区，导致“同步任务”标题换行。

- 实现：
  - 总览页主列 + 300px 右轨从 `1180px` 触发改为 `1440px` 触发。
  - 任务详情页主列 + 300px 检查器从 `1180px` 触发改为 `1440px` 触发。
  - 任务详情页移除主列 `760px` 强制最小宽度，避免右侧检查器挤压主内容。
  - 任务详情页“当前运行”上传、下载、跳过和错误指标改为自适应网格，不再横向硬塞在进度环右侧。
  - 顶部栏标题增加 `whitespace-nowrap`，页面摘要和状态胶囊延后到 `1500px` 以上显示，账号区延后到 `1360px` 以上显示。
  - 总览页“正在运行”表格最小宽度收敛为 `740px`，1440px 并排状态下不再出现内部横向滚动条。

- 结果：
  - 1280 x 820 视口下，总览页无页面级横向溢出。
  - 1280 x 820 视口下，任务详情页无页面级横向溢出。
  - 1280 x 820 视口下，顶部栏高度保持 56px，“同步任务”标题保持单行。
  - 1440 x 960 视口下，总览页右轨正常并排。
  - 1440 x 960 视口下，总览页“正在运行”表格内部滚动区 `clientWidth=764`，`scrollWidth=764`，无内部横向溢出。
  - 1440 x 960 视口下，任务详情页右侧检查器正常并排。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`（24 files / 57 tests passed）
  - `npm --prefix apps/frontend run build`
  - 浏览器打开 `http://127.0.0.1:3666`，用真实任务数据验证 1280 x 820 和 1440 x 960 视口。
  - 总览页 1280 x 820：`documentElement.clientWidth=1280`，`documentElement.scrollWidth=1280`，`main.clientWidth=1022`，`main.scrollWidth=1022`。
  - 任务详情页 1280 x 820：`documentElement.clientWidth=1280`，`documentElement.scrollWidth=1280`，`main.clientWidth=1022`，`main.scrollWidth=1022`，顶部栏 `h1Height=27`。
  - 总览页 1440 x 960：`documentElement.clientWidth=1440`，`documentElement.scrollWidth=1440`，`main.clientWidth=1182`，`main.scrollWidth=1182`。

- 遗留问题：
  - 1440px 并排时总览主列信息密度较高，但不再出现卡片互相挤占或横向溢出。
  - 后续若继续强化宽屏体验，可考虑为 1600px 以上增加更宽主列或隐藏低优先级表格列。

### 2026-07-07 桌面壳安全断点统一

- 原因：
  - 活动与问题页、冲突处理页仍在 `1280px` 触发 `300px + 主列 + 320px` 三栏布局。
  - 1280px 桌面窗口扣除 248px 左侧导航和主内容区左右内边距后，真实工作区约为 1022px。
  - 在 1022px 工作区内强行三栏会让中间排障列只有约 360px，容易出现信息拥挤。
  - 更新与维护页仍用 Tailwind `xl` 在 1280px 触发双列，也没有按桌面壳真实工作区计算。

- 实现：
  - 活动与问题页三栏断点从 `1280px` 改为 `1440px`。
  - 冲突处理页三栏断点从 `1280px` 改为 `1440px`。
  - 活动与问题页、冲突处理页顶部四摘要卡从 `1180px` 改为 `1440px` 触发四列。
  - 总览页顶部四摘要卡从 `1180px` 改为 `1440px` 触发四列。
  - 更新与维护页主列 + 维护侧栏从 `xl` 改为 `1440px` 触发。
  - 统一给活动与问题页、冲突处理页的面板增加 `min-w-0`、标题截断和 action 固定宽度处理。
  - 新增 `MaintenancePage.test.tsx`，锁定更新维护页的 1440px 宽屏断点。

- 结果：
  - 1280 x 820 视口下，总览页、活动与问题页、冲突处理页、更新与维护页均无页面级横向溢出。
  - 1440 x 960 视口下，总览页、活动与问题页、冲突处理页、更新与维护页均无页面级横向溢出。
  - 活动与问题页在 1280px 下纵向展示任务选择、运行历史、问题摘要、事件详情和建议动作。
  - 活动与问题页在 1440px 下恢复左侧任务/运行、中间问题/时间线、右侧事件详情的三栏排障工作台。
  - 冲突处理页在 1280px 下纵向展示冲突队列、版本对比、处理状态和版本选择。
  - 冲突处理页在 1440px 下恢复冲突队列、版本对比、处理侧栏的三栏工作台。
  - 更新与维护页在 1280px 下纵向展示更新状态和日志/映射维护。
  - 更新与维护页在 1440px 下恢复更新主列 + 维护侧栏。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`（25 files / 58 tests passed）
  - `npm --prefix apps/frontend run build`
  - 浏览器打开 `http://127.0.0.1:3666`，用真实任务数据验证 1280 x 820 和 1440 x 960 视口。
  - 1280 x 820：总览、活动与问题、冲突处理、更新与维护均满足 `documentElement.clientWidth=1280` 且 `documentElement.scrollWidth=1280`。
  - 1280 x 820：四个页面均满足 `main.clientWidth=1022` 且 `main.scrollWidth=1022`。
  - 1440 x 960：总览、活动与问题、更新与维护均满足 `documentElement.clientWidth=1440` 且 `documentElement.scrollWidth=1440`。
  - 1440 x 960：冲突处理页满足 `documentElement.clientWidth=1440` 且 `documentElement.scrollWidth=1440`；该页主内容测得 `main.clientWidth=1192` 且 `main.scrollWidth=1192`。

- 遗留问题：
  - 旧日志中心组件仍保留给测试和兼容入口，但桌面导航中的活动与问题、冲突处理已切到独立浅色工作台。
  - 后续继续实现 OAuth 二维码授权、启动连接状态页和新建任务向导时，应沿用 1440px 桌面壳安全断点。

### 2026-07-07 总览与任务详情布局三次收口

- 原因：
  - 用户继续反馈总览页和任务详情页仍有框体互相挤占。
  - 1440px 断点只按浏览器视口计算，没有扣除 248px 左侧导航和主内容区左右 48px 内边距。
  - 在 1440px 桌面窗口中，真实主工作区约 1144px；若同时放 300px 右轨、28px gutter 和主列表，主列视觉仍偏紧。

- 实现：
  - 总览页顶部四摘要卡从 `1440px` 改为 `1600px` 以上进入四列。
  - 总览页主列 + 300px 右侧处理轨从 `1440px` 改为 `1600px` 以上触发。
  - 任务详情页主列 + 300px 检查器从 `1440px` 改为 `1600px` 以上触发。
  - 更新 `DashboardPage.test.tsx` 和 `TaskDetailPage.test.tsx`，明确禁止回退到 1440px 右轨断点。
  - 更新 README 和 CHANGELOG，将总览/任务详情与其它页面的断点口径区分开。

- 结果：
  - 1280px 和 1440px 初始桌面窗口下，总览页保持纵向主内容，不再出现右侧处理轨抢占主列。
  - 1280px 和 1440px 初始桌面窗口下，任务详情页保持纵向主内容，不再出现右侧检查器挤压路径关系、当前运行和运行历史。
  - 1600px 以上恢复 v3 设计中的主列 + 约 300px 右轨/检查器。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx TaskDetailPage.test.tsx`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`（26 files / 60 tests passed）
  - `npm --prefix apps/frontend run build`
  - Chrome headless 1440 x 960：总览页 `documentElement.scrollWidth=1440`，`main.width=1192`，右侧处理区位于主列下方，容器宽度 `1144px`。
  - Chrome headless 1600 x 960：总览页 `documentElement.scrollWidth=1600`，主列宽度 `976px`，右侧处理轨宽度 `300px`。
  - Chrome headless 1440 x 960：任务详情页已打开真实任务详情，`documentElement.scrollWidth=1440`，问题摘要/任务操作/策略摘要/危险操作位于主列下方，容器宽度 `1144px`。
  - Chrome headless 1600 x 960：任务详情页主列宽度 `976px`，右侧检查器宽度 `300px`。

- 遗留问题：
  - 本轮先做布局断点修复，未改动数据口径、任务排序、运行历史和后端接口。
  - 后续如要进一步贴近设计稿，可再按真实截图微调 1600px 以上的主列表格列宽。

### 2026-07-07 总览与任务详情布局四次收口

- 原因：
  - 用户继续反馈总览页和任务详情页存在框体互相挤占。
  - 1600px 浏览器视口在桌面壳内需要扣除 248px 左侧导航和主内容区 48px 内边距。
  - 扣除后真实工作区约 1304px，同时放 300px 右轨、28px gutter 和主列表时，主列仍容易显得拥挤。
  - 任务详情页内部“本地目录 / 同步模式 / 云端目录”三列原先在 1440px 触发，会在主列变窄时继续挤压路径文本。

- 实现：
  - 总览页顶部四摘要卡从 `1600px` 改为 `1760px` 以上进入四列。
  - 总览页主列 + 300px 右侧处理轨从 `1600px` 改为 `1760px` 以上触发。
  - 任务详情页主列 + 300px 检查器从 `1600px` 改为 `1760px` 以上触发。
  - 任务详情页当前运行的四个传输指标从 `1500px` 改为 `1760px` 以上进入四列。
  - 任务详情页路径关系区从 `1440px` 改为 `1760px` 以上进入三列。
  - 更新 `DashboardPage.test.tsx` 和 `TaskDetailPage.test.tsx`，明确禁止回退到 1600px、1500px 和 1440px 的拥挤断点。

- 结果：
  - 1440px、1536px 和 1600px 常见桌面窗口下，总览页保持纵向主内容，右侧处理轨不再抢占主列宽度。
  - 1440px、1536px 和 1600px 常见桌面窗口下，任务详情页保持纵向主内容，检查器、路径三列和四指标不会同步挤压主列。
  - 1760px 以上才恢复 v3 设计中的主列 + 约 300px 右轨/检查器。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx TaskDetailPage.test.tsx`

- 遗留问题：
  - 本轮只调整布局断点和测试断言，未改动接口、数据口径、任务排序和运行历史逻辑。
  - 如后续在 1760px 以上仍觉得表格密度高，应优先压缩低优先级列或改为容器查询，而不是继续按浏览器整宽提前分栏。

### 2026-07-07 总览与任务详情布局五次收口

- 原因：
  - 用户继续反馈任务详情页和总览页仍有框体互相挤占。
  - 1760px 断点仍按浏览器整宽触发，未按桌面壳左侧 248px 导航、主内容区 48px 内边距和系统缩放后的可用工作区计算。
  - 任务详情页路径关系区和当前运行指标在右侧检查器出现时同时进入宽屏多列，长路径、云端标识和四个指标卡仍容易被压缩。

- 实现：
  - 总览页顶部四摘要卡从 `1760px` 改为 `1920px` 以上进入四列。
  - 总览页主列 + 右侧处理轨从 `1760px` 改为 `1920px` 以上触发。
  - 总览页右侧处理轨从 `300px` 扩为 `320px`，减少右轨内部按钮和状态卡拥挤。
  - 任务详情页主列 + 检查器从 `1760px` 改为 `1920px` 以上触发。
  - 任务详情页检查器从 `300px` 扩为 `320px`。
  - 任务详情页路径关系区从 `1760px` 改为 `1920px` 以上进入 `本地 / 同步模式 / 云端` 三列。
  - 任务详情页当前运行的四个传输指标从 `1760px` 改为 `1920px` 以上进入四列。
  - 任务详情页云端目录右对齐从 `lg` 改为 `1920px` 同步触发，避免纵向布局下视觉左右分裂。
  - `DashboardPage.test.tsx` 和 `TaskDetailPage.test.tsx` 明确禁止回退到 `1760px` 右轨和路径三列断点。

- 结果：
  - 1280px、1440px、1600px 和 1760px 常见桌面窗口下，总览页保持主列优先，不再提前出现右侧处理轨抢宽度。
  - 1280px、1440px、1600px 和 1760px 常见桌面窗口下，任务详情页保持主列优先，检查器、路径三列和当前运行四指标不会同时挤压主列。
  - 1920px 以上恢复 v3 设计中的宽屏右轨/检查器，并给右侧栏保留 320px 宽度。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx TaskDetailPage.test.tsx`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`（25 files / 61 tests passed）
  - `npm --prefix apps/frontend run build`
  - 浏览器打开 `http://127.0.0.1:3666/#dashboard`，在 1280 x 720 实际窗口下验证总览页。
  - 总览页 1280 x 720：`documentElement.clientWidth=1280`，`documentElement.scrollWidth=1280`，`main.clientWidth=1022`，`main.scrollWidth=1022`，右侧处理区位于主列下方。
  - 浏览器打开真实任务详情，1280 x 720：`documentElement.clientWidth=1280`，`documentElement.scrollWidth=1280`，`main.clientWidth=1022`，`main.scrollWidth=1022`，路径关系区为单列。

- 遗留问题：
  - 本轮先处理页面框体挤占，不改任务数据、同步状态和后端接口。
  - 浏览器控制接口当前不能直接设置 1760px / 1920px 视口；这两个断点由页面 smoke test 约束。
  - 后续如继续收紧，应优先考虑容器查询或表格列降级，而不是只按浏览器整宽断点推进。

### 2026-07-07 Windows 桌面窗口宿主

- 原因：
  - 桌面化规划要求安装版默认进入桌面窗口，而不是继续默认打开外部浏览器管理面板。
  - 现有 `tray_app.py` 在后端启动成功后直接调用 `webbrowser.open()`。
  - 托盘菜单只有“打开管理面板”，缺少“打开桌面窗口”和“在浏览器中打开”双入口。
  - `pystray` 和 `pywebview` 都有阻塞事件循环，不能把 WebView 窗口直接塞进托盘主事件循环。

- 实现：
  - 新增 `apps/tray/desktop_window.py`。
  - 桌面窗口使用独立子进程运行 pywebview，托盘主进程继续负责后端生命周期、状态轮询、通知和菜单。
  - 子进程通过 `tray_app.py --desktop-window --url ...` 启动，非打包态走当前 Python + `apps/tray/tray_app.py`，打包态走当前可执行文件。
  - Windows 下 pywebview 启动优先指定 `edgechromium`，并设置初始尺寸 `1280 x 820`、最小尺寸 `1080 x 720`。
  - 如果 `webview` 模块不存在、用户设置 `LARKSYNC_FORCE_BROWSER=1` 或子进程启动失败，则自动回退到浏览器。
  - 如果桌面窗口子进程刚启动就退出，则托盘立即回退浏览器，避免用户看到无窗口状态。
  - 托盘菜单主入口改为“打开桌面窗口”，并新增“在浏览器中打开”备用入口。
  - 托盘“设置”和“查看日志/问题”入口改为优先打开桌面窗口路由。
  - 查看问题入口从旧 `#logcenter` 更新为 `#activity`。
  - 重复启动检测到已有实例时，也优先打开桌面窗口；如果桌面宿主不可用，则由同一 helper 回退浏览器。
  - `DesktopWindowLaunchResult` 增加窗口子进程句柄。
  - `LarkSyncTray` 记录托盘拉起的桌面窗口子进程。
  - 托盘进程内再次打开桌面窗口时，如果原窗口仍在运行，直接复用原进程，不再生成第二个 WebView 窗口。
  - 如果原窗口已经退出，托盘会清空旧进程引用并重新打开窗口。
  - 退出托盘时同步清理仍在运行的桌面窗口子进程。
  - 前端 `App` 启动时读取 `#settings`、`#activity`、`#maintenance` 等 hash 路由。
  - 前端继续兼容旧 `#logcenter`，自动映射到“活动与问题”。
  - 新增运行依赖 `pywebview>=5.0`，并把 `webview` 相关模块加入 PyInstaller hiddenimports。

- 结果：
  - 托盘启动成功后会优先打开桌面窗口。
  - 用户关闭桌面窗口时，只会关闭窗口子进程，托盘和后端同步服务继续运行。
  - WebView2/pywebview 不可用时仍能通过浏览器 fallback 使用。
  - 托盘菜单已形成桌面窗口与浏览器 fallback 的双入口。
  - 设置、活动与问题、重复启动入口不再默认跳出到外部浏览器。
  - `/#settings` 和 `/#activity` 可以直达桌面壳对应页面，避免打开窗口后仍停留在总览页。
  - 托盘进程内的重复打开动作不会再创建多个桌面窗口。
  - 托盘退出会清理桌面窗口子进程，避免残留 WebView 进程。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run test -- App.test.tsx DashboardPage.test.tsx TaskDetailPage.test.tsx`（3 files / 7 tests passed）
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`
  - `python -m pytest tests/test_desktop_window.py tests/test_tray_config.py tests/test_tray_lock.py tests/test_tray_update_install.py tests/test_build_installer.py`（工作目录：`apps/backend`，结果：61 passed）
  - `python -m py_compile apps/tray/desktop_window.py apps/tray/tray_app.py apps/tray/config.py apps/tray/notifier.py scripts/build_installer.py`
  - `python -m pip install -e apps/backend --dry-run`（可解析 `pywebview-6.2.1`、`pythonnet`、`bottle`、`proxy_tools` 等依赖，未实际安装）
  - `python -c "import importlib.util; print(importlib.util.find_spec('webview') is not None)"`：当前开发环境输出 `False`，未做真实 GUI 打开验证。

- 遗留问题：
  - 本轮未做真实 WebView2 安装版 smoke；后续进入安装体验批次时需要执行 `python scripts/build_installer.py --nsis` 并手动验证窗口创建、关闭窗口后托盘仍运行、托盘重新打开窗口。
  - 当前已实现托盘进程内单窗口复用；如果要让“重复启动应用”也聚焦既有窗口，还需要跨进程 IPC。

### 2026-07-07 同步任务页与新建任务向导浅色化

- 原因：
  - 桌面壳、总览页和任务详情页已进入浅色科技风，但同步任务页仍保留 `zinc-900/zinc-950` 旧暗色卡片。
  - 任务列表、任务卡片、云端目录树和新建任务向导是创建同步关系的主链路，视觉割裂会影响桌面版一致性。
  - 设计稿要求同步任务页采用表格化/密集任务行和浅色冷白面板，新建任务向导应作为分步配置流程，而不是旧暗色弹窗。

- 实现：
  - `TasksPageHeader` 改为浅色工具条，移除页面内部主题切换按钮，保留刷新、新建任务和测试任务显隐。
  - `TasksEmptyState` 改为浅色虚线空态。
  - `TaskCard` 改为白色任务行卡片，路径关系区使用冷白技术面板，状态胶囊、模式标签、进度条和操作按钮统一浅色 token。
  - `TaskCard` 展开管理区改为浅色策略编辑区，保留同步模式、更新模式、MD 上传模式和删除策略的原有保存行为。
  - `NewTaskModal` 改为浅色桌面弹窗，宽度提升到 `max-w-4xl`，保留三步向导、系统目录选择、云端目录树、手动链接/Token 和创建 payload。
  - `NewTaskLocalStep`、`NewTaskCloudStep`、`NewTaskStrategyStep` 和 `NewTaskWizardStepIndicator` 全部替换旧暗色边框、文本和背景。
  - `TreeNode` 改为浅色目录树节点，避免新建任务第二步仍混入暗色控件。
  - 更新 `TasksPage.test.tsx`、`TaskPanels.test.tsx` 和 `NewTaskWizardPanels.test.tsx`，断言任务页/任务卡/向导不再包含旧暗色类名。

- 结果：
  - 同步任务页与桌面壳、总览页和任务详情页的浅色科技风一致。
  - 新建任务向导仍使用既有 `/system/select-folder`、`/drive/tree` 和 `/sync/tasks` 接口。
  - 本轮未改变同步模式、删除策略、MD 上传模式和任务操作的业务逻辑。
  - Chrome headless 1440 x 960 打开同步任务页并打开新建任务弹窗，页面级 `documentElement.scrollWidth=1440`，无横向溢出。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run test -- NewTaskWizardPanels.test.tsx TasksPage.test.tsx App.test.tsx`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test -- TasksPage.test.tsx TaskPanels.test.tsx NewTaskWizardPanels.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - Chrome headless 1440 x 960：已连接状态下进入同步任务页，打开新建任务弹窗，`documentElement.clientWidth=1440` 且 `documentElement.scrollWidth=1440`。

- 遗留问题：
  - 本轮保留现有任务卡展开式高级管理；后续如继续贴近设计稿，可把任务列表进一步改成真正的密集表格行。
  - 设置页仍有旧暗色输入样式，后续应继续按浅色科技风收口。

### 2026-07-07 设置页浅色化与职责收敛

- 原因：
  - 设置页仍保留 `zinc-900/zinc-950` 旧暗色卡片，与桌面浅色科技风不一致。
  - 设置页重复承载自动更新、日志保留和同步映射重置；这些维护能力已在更新维护页实现。
  - 旧同步策略卡在中等工作区过早进入三列/双列，容易造成模式卡和上下行配置拥挤。

- 实现：
  - `SettingsPage` 移除 `useUpdate`、自动更新处理、同步映射重置处理和内部主题切换入口。
  - 设置页保留 OAuth、默认同步策略、设备显示名和本地忽略目录。
  - 自动更新、日志保留和同步映射重置继续由 `MaintenancePage` 承载。
  - `SettingsOAuthPanel`、`SettingsSyncStrategyPanel`、`SettingsMorePanel`、`SettingsGeneralPanel` 和 `SettingsIgnoredDirectoriesPanel` 改为浅色科技风。
  - 默认同步模式三列延后到 `1180px` 以上触发。
  - 上下行频率双列延后到 `1440px` 以上触发。
  - 删除设置页专用的旧 `SettingsUpdatePanel` 和 `SettingsMaintenancePanel`，避免死代码继续保留旧暗色样式。
  - 更新 `SettingsPage.test.tsx` 和 `SettingsPanels.test.tsx`，断言设置页不再渲染自动更新、重置同步映射和旧暗色卡片类名。

- 结果：
  - 设置页与桌面壳、总览页、任务详情页和同步任务页的浅色科技风一致。
  - 设置页只负责日常配置，不再重复维护页入口。
  - 本轮未改变 OAuth 保存、默认同步策略保存、设备显示名保存和任务级忽略目录保存的接口行为。

- 验证：
  - `npm --prefix apps/frontend run test -- SettingsPage.test.tsx SettingsPanels.test.tsx MaintenancePage.test.tsx`（3 files / 4 tests passed）
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test`（26 files / 60 tests passed）
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`
  - Chrome headless 1440 x 960：设置页 `documentElement.scrollWidth=1440`，`main.scrollWidth=1192`，OAuth、同步策略和更多设置三张主卡宽度均为 `1144px`。
  - Chrome headless 展开高级 OAuth、更多设置和本地忽略目录后，1280 x 960 / 1440 x 960 / 1600 x 960 均未出现页面级横向溢出或设置页内部元素溢出。

- 遗留问题：
  - 本轮只处理设置页，没有继续调整维护页的交互密度。
  - 后续全量页面收口时，可继续用真实桌面壳截图微调设置页 1600px 以上的空白比例。

### 2026-07-07 旧日志中心移除与全局反馈层浅色化

- 原因：
  - 桌面版主路由已经拆为「活动与问题」和「冲突处理」两个独立页面。
  - 旧 `LogCenterPage` 不再被 `App` 路由使用，但仍保留旧暗色 `zinc` 页面和子组件。
  - 全局 Toast 和确认弹窗仍是暗色样式，会在删除任务、重置映射和静默安装等关键操作中破坏浅色科技风一致性。

- 实现：
  - 删除旧 `LogCenterPage.tsx` 和 `LogCenterPage.test.tsx`。
  - 删除旧 `components/log-center/` 下的暗色任务诊断、系统日志、事件管理和对应组件测试。
  - 删除未被引用的旧 `Header`、`EmptyState`、`Skeleton` 和 `Pagination` 组件。
  - `App.test.tsx` 移除对旧日志中心页面的 mock。
  - `ToastProvider` 改为浅色边框、浅色状态底和轻阴影。
  - `ConfirmDialogProvider` 改为浅色遮罩、白色面板、浅色取消按钮和小面积状态色确认按钮。
  - `App` 加载态和未授权引导外层移除旧暗色文本 token。
  - `MaintenancePage` 的主维护卡片统一改为 8px 级圆角。
  - `OnboardingWizard` 的扫码和授权主卡片统一改为 8px 级圆角。
  - `TaskDetailPage` 的本地目录/箭头/云端目录三列布局从 `lg` 延后到 `1440px` 以上触发。

- 结果：
  - 当前实际前端源码中的旧暗色页面组件已移除。
  - 源码扫描只剩测试中的旧暗色类名防回退断言。
  - 活动与问题页继续复用 `useLogCenterTaskDiagnostics` 等查询 hook，不删除后端诊断能力。
  - 冲突处理继续通过独立页面和 `useConflictResolutionQueue` 承载。

- 验证：
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test`（22 files / 53 tests passed）
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`
  - `rg -n "zinc-|bg-zinc|text-zinc|border-zinc|rose-|amber-|emerald-|rounded-2xl|xl:grid|lg:grid" apps/frontend/src -g '*.tsx'`：仅剩测试文件中的防回退断言。
  - `rg -n "LogCenterPage|components/log-center|Header|EmptyState|Skeleton|Pagination" apps/frontend/src -g '*.ts' -g '*.tsx'`：未发现旧页面和死代码引用。
  - Chrome headless 1440 x 960 逐页点击总览、同步任务、活动与问题、冲突处理、设置、更新与维护：各页 `documentElement.scrollWidth=1440`，`main.scrollWidth=1192`，运行时 DOM 未检测到旧 `zinc` 暗色类、`rounded-2xl` 主面板或“日志中心”旧文案。

- 遗留问题：
  - 本轮未移除历史日志和开发记录中的旧日志中心描述。
  - 后续如果需要系统日志可视化，应在更新维护页或新的轻量诊断抽屉中重新设计，而不是恢复旧 `LogCenterPage`。

### 2026-07-07 桌面壳聚合状态 API

- 原因：
  - 桌面规格要求顶部状态栏和底部状态条统一展示后端、账号、任务、冲突、数据库和更新状态。
  - 旧实现中顶栏分别读取 auth、tasks、conflicts，底栏读取 `/tray/status`。
  - 状态来源分散会让桌面壳在后续接 Windows 宿主、托盘菜单和安装版 fallback 时难以保持一致。

- 实现：
  - 新增 `/system/desktop/status`。
  - 新接口返回 `runtime`、`auth`、`tasks`、`conflicts`、`update` 五组嵌套状态。
  - `runtime` 包含后端运行、前端静态文件是否存在、数据目录、数据库 URL 和是否打包态。
  - `auth` 包含 OAuth 是否已配置、是否已连接、账号名、open_id、设备 ID 和 token 过期时间。
  - `tasks` 包含任务总数、启用数、停用数、运行数、失败数、最近错误和最近同步时间。
  - `conflicts` 包含未解决冲突数。
  - `update` 包含当前版本、最新版本、是否有更新、上次检查、更新错误和已下载路径。
  - `/tray/status` 改为复用同一聚合状态后再映射回旧字段，保持托盘旧调用兼容。
  - `DesktopTopBar` 改为消费 `useDesktopStatus` 的账号、运行任务和待处理冲突摘要。
  - `DesktopStatusBar` 改为消费 `useDesktopStatus` 的后端、前端模式、任务、数据库、冲突、版本和最近同步摘要。
  - 新增 `useDesktopStatus` hook 和 `DesktopShellStatus.test.tsx`。

- 结果：
  - 桌面壳顶部和底部状态来自同一个后端模型。
  - 托盘 `/tray/status` 字段不变，不影响现有托盘菜单和测试。
  - 状态聚合只读取现有服务，不新增飞书 API 字段假设。
  - token store 读取失败时，桌面聚合接口会降级为未连接，不影响后端/任务/更新状态展示。

- 验证：
  - `python -m pytest tests/test_tray_status.py tests/test_system_update_api.py`（工作目录：`apps/backend`，14 passed）
  - `python -m py_compile src/api/system.py src/main.py`（工作目录：`apps/backend`）
  - `python -m pytest tests/test_tray_status.py`（工作目录：`apps/backend`，9 passed）
  - `npm --prefix apps/frontend run test -- DesktopShellStatus.test.tsx App.test.tsx`（2 files / 4 tests passed）
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run test`（23 files / 54 tests passed）
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`

- 遗留问题：
  - 当前接口只做桌面壳状态聚合，还没有加入 WebSocket 在线状态。
  - 后续接 Windows 桌面窗口宿主后，可继续把窗口宿主状态和托盘可见状态纳入 `runtime`。

### 2026-07-07 启动状态与授权闭环

- 原因：
  - 桌面设计稿要求启动页解释托盘、后端、桌面窗口、前端资源和飞书授权状态。
  - 当前首次授权页只展示 OAuth 应用、授权连接、Drive 权限和设备 ID。
  - 用户扫码完成 OAuth 后，前端没有自动轮询 `/auth/status`，容易停留在二维码页。
  - 授权 redirect 只回到 origin，无法保留 `#settings`、`#activity` 等桌面 hash 路由。

- 实现：
  - `OnboardingWizard` 接入 `useDesktopStatus`。
  - 启动状态面板新增窗口宿主、后端服务、前端资源、运行模式和数据目录。
  - 前端资源按 `frontend_static_available + packaged` 区分为生产静态、开发服务和静态缺失。
  - 窗口宿主通过 `window.pywebview` 判断桌面窗口，否则显示浏览器或开发预览。
  - 授权页刷新状态时同时刷新 `auth-status`、授权 URL 和桌面聚合状态。
  - `getLoginUrl()` 和授权二维码 redirect 改为使用当前完整页面 URL，保留 hash 路由。
  - `useAuth` 在未连接时每 2.5 秒轮询 `/auth/status`，连接后停止轮询。
  - 新增 `api.test.ts` 和 `useAuth.test.ts`，锁定 hash redirect 与授权轮询策略。

- 结果：
  - 首次启动页更接近浅色科技风启动/连接状态设计稿。
  - 扫码授权成功后，页面可以自动感知连接状态并进入桌面壳。
  - 用户从托盘设置、活动与问题等入口触发授权时，授权完成后不会丢失原 hash 路由。
  - 启动页能区分开发服务、生产静态和安装版静态缺失，便于安装版排障。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run test -- api.test.ts useAuth.test.ts OnboardingWizard.test.tsx App.test.tsx`
  - `npm --prefix apps/frontend run test -- OnboardingWizard.test.tsx useAuth.test.ts api.test.ts App.test.tsx DesktopShellStatus.test.tsx`（5 files / 12 tests passed）
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`

- 遗留问题：
  - 当前窗口宿主判断只区分 pywebview 与浏览器/开发预览。
  - 后续若桌面窗口进程加入 IPC，可把真实窗口进程、托盘可见性和浏览器 fallback 原因纳入 `/system/desktop/status`。

### 2026-07-07 更新维护页安装 handoff 可视化

- 原因：
  - 浅色设计稿要求更新与维护页集中展示下载安装、校验、托盘接管、静默安装、自动重启和失败恢复。
  - 旧维护页只有固定的五步“安装 handoff”静态展示。
  - 静态五步无法说明真实 `install-request.json` 和 `install-handoff.json` 当前处于哪个阶段。
  - 设计要求保守展示安装状态，不能把未确认状态写成成功。

- 实现：
  - `update_install_service.py` 新增 `UpdateInstallHandoff` 模型。
  - 新增 `install_handoff_path()` 和 `load_install_handoff()`，兼容 UTF-8 BOM 读取 helper 回执。
  - `load_install_request()` 增加 Pydantic 校验失败兜底，坏文件不让状态接口报错。
  - `/system/update/status`、`/system/update/check`、`/system/update/download` 返回 `install_request` 和 `install_handoff`。
  - `useUpdate` 增加安装请求和 handoff 类型。
  - `MaintenancePage` 将固定五步改为根据真实状态推导：
    - 校验通过：只在已有下载路径时标记就绪。
    - 托盘接管：只在存在安装请求时标记已排队。
    - helper 启动：只在 handoff 阶段进入 bootstrap/helper/installer/install/restart 时标记。
    - 静默安装：只在 installer/install/restart 阶段标记安装中或已完成。
    - 自动重启：只在 `restart_succeeded` 标记已确认，`restart_failed` 标记未确认。
  - 页面新增安装请求 ID、安装包路径、handoff 时间和 helper 消息展示。

- 结果：
  - 更新与维护页不再伪造安装进度。
  - 用户能看到当前安装请求是否已排队、helper 是否接管、安装器是否启动、自动重启是否确认。
  - 后端状态接口只读取已有本地 JSON，不改变安装执行链路。
  - 坏的安装请求或 handoff 文件会降级为无状态，不阻塞更新页加载。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `python -m pytest tests/test_system_update_api.py tests/test_tray_update_install.py`（工作目录：`apps/backend`，27 passed）
  - `python -m py_compile apps/backend/src/api/system.py apps/backend/src/services/update_install_service.py`
  - `npm --prefix apps/frontend run test -- MaintenancePage.test.tsx`（1 file / 2 tests passed）
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run lint`

- 遗留问题：
  - 本轮未执行真实 NSIS 安装。
  - 真实安装体验仍需 `python scripts/build_installer.py --nsis` 和用户级安装/启动 smoke 验证。

## v0.7.29 (2026-07-06)

- 目标：
  - 将 `v0.7.29-dev.1` 的安装版入口修复收口为正式补丁版。
  - 发布新的安装包，替换 `v0.7.28` 中安装版可能误打开 `3666` 开发页面的问题。

- 结果：
  - 当前版本正式提升为 `v0.7.29`。
  - 安装版托盘管理面板、设置和日志中心固定打开 `8000` 上的生产静态前端。
  - `3666` 仍仅用于 `--dev` / `npm run dev` 的开发热重载入口。
  - README、CHANGELOG、根包/前端/后端版本和锁文件同步对齐到 `v0.7.29` / `0.7.29`。

- 验证：
  - `python scripts/sync_feishu_docs.py`
  - `python -m pytest tests/test_tray_config.py tests/test_tray_lock.py`（工作目录：`apps/backend`，结果：7 passed）
  - `python -m pytest`（工作目录：`apps/backend`，结果：513 passed）
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - `python -m pip install -e apps/backend --dry-run`

## v0.7.29-dev.1 (2026-07-06)

- 目标：
  - 修复安装版启动后仍打开 `http://localhost:3666` 的问题。
  - 明确区分开发入口与安装版入口：`3666` 只属于显式 `--dev` 的 Vite 热重载服务，安装版应打开 `8000` 上由 FastAPI 提供的生产静态页面。

- 原因：
  - `apps/tray/config.py` 的 `_detect_frontend_url()` 会优先探测本机 `3666` 端口。
  - 如果用户机器上仍有 Vite 开发服务运行，新安装的托盘版会把该端口误判为当前前端入口。
  - 该行为会让安装版打开测试页面，而不是安装包内置的生产前端。

- 实现：
  - `apps/tray/config.py` 的生产 URL 检测改为始终返回 `BACKEND_URL`。
  - `apps/tray/tray_app.py` 现有 `--dev` 分支继续显式使用 `VITE_DEV_URL`，开发体验不变。
  - 新增托盘配置回归测试：即使 `_is_port_active(3666)` 返回 true，`get_dashboard_url()`、`get_settings_url()` 和 `get_logs_url()` 也必须返回 `8000` 地址。

- 结果：
  - 安装版打开管理面板、设置、日志中心时都会走 `http://127.0.0.1:8000`。
  - `npm run dev` / `python apps/tray/tray_app.py --dev` 仍会使用 `http://localhost:3666`。

- 验证：
  - `python -m pytest tests/test_tray_config.py`（工作目录：`apps/backend`，结果：5 passed）

## v0.7.28 (2026-07-06)

- 目标：
  - 将 `v0.7.28-dev.1` 到 `v0.7.28-dev.7` 的日志中心、事件管理、仪表盘和任务待处理说明改动收口为正式稳定版。
  - 发布一个用户可直接安装升级的稳定版，解决“待处理不知道处理什么”、事件管理结构混乱、任务诊断噪音过多、仪表盘高度不对齐和配色可读性问题。

- 结果：
  - 当前版本正式提升为 `v0.7.28`。
  - 本次稳定版纳入日志中心“冲突管理”升级为“事件管理”的完整改造：顶部选任务、左侧选同步运行进程、右侧查看具体问题、原因、建议动作和原始事件。
  - 事件管理默认只展示需关注事件；普通上传、下载、跳过和完成日志默认隐藏，可通过“显示全部事件”做完整审计。
  - 事件分类会把 `_LarkSync_MD_Mirror` 创建 forbidden、Docx 块写入 forbidden、删除目标 not found、删除失败、待删除、冲突和取消解释成明确问题，避免只显示笼统待处理数字。
  - 任务诊断默认隐藏全 0 无动作任务；任务管理页和仪表盘会拆分显示队列、待删、删失败、失败和冲突等待处理来源。
  - 仪表盘宽屏布局已收口为与左侧边栏同高：Header 和 Dashboard 共享同一个外壳高度，“任务概览”和“需要关注”在剩余高度内各自滚动。
  - README、CHANGELOG、根包/前端/后端版本、锁文件、`release-notes-preview.md` 与本开发日志同步对齐到 `v0.7.28` / `0.7.28`。
  - 正式版 Release 继续沿用 tag 驱动的 GitHub Actions 发布链路：推送 `v0.7.28` tag 后会在远端执行 Windows/macOS 质量门、安装包构建、release notes 生成与 Release 资产上传。

- 测试：
  - `python scripts/sync_feishu_docs.py`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - `python -m pytest`（工作目录：`apps/backend`，结果：512 passed）
  - `python scripts/build_installer.py`
  - `python scripts/release_notes.py --version v0.7.28 --output release-notes-preview.md`

- 问题：
  - 真实 GitHub Release 安装包仍以 tag 推送后的远端 workflow 结果为准。
  - 本机未安装 `makensis`；本地 `python scripts/build_installer.py` 已生成 `dist/LarkSync/LarkSync.exe`，未生成 Windows NSIS 安装器。

## v0.7.28-dev.7 (2026-07-06)

- 目标：
  - 修正 `v0.7.28-dev.6` 后仪表盘整体高度又偏长的问题。
  - 让仪表盘整体高度与左侧边栏一致，而不是让 `DashboardPage` 在 Header 下面再占一整屏高度。

- 结果：
  - `App` 在仪表盘页签下新增一层 `lg:h-[calc(100vh-2.5rem)]` 的容器，统一包住 `Header` 和 `DashboardPage`，高度与左侧边栏一致。
  - `DashboardPage` 移除自身的 `min-[1760px]:h-[calc(100vh-2.5rem)]`，改为在仪表盘容器内 `flex-1` 占用 Header 下方剩余高度。
  - `DashboardPage` 宽屏下增加 `overflow-hidden`，下方“任务概览”和“需要关注”继续各自内部滚动，避免页面整体被撑长。
  - `App.test.tsx` 新增断言：仪表盘 Header 和 Dashboard 被同一个侧边栏等高容器约束；`DashboardPage.test.tsx` 断言页面自身不再带整屏高度。
  - README、CHANGELOG、根包版本、前端版本和锁文件已同步到 `v0.7.28-dev.7` / `0.7.28-dev.7`。

- 测试：
  - `npm --prefix apps/frontend run test -- App.test.tsx DashboardPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - 浏览器检查 `http://127.0.0.1:3666`（`2048x900`）：侧边栏和仪表盘外壳实际高度均为 `860px`，Header 为 `126px`，Dashboard 剩余高度为 `710px`；“任务概览”和“需要关注”面板实际高度均为 `572px`，页面 `bodyScrollHeight` 等于视口高度 `900`。
  - `python scripts/build_installer.py`

- 问题：
  - 本轮为前端高度约束修正，未改变仪表盘数据口径、任务排序、关注事件筛选或后端接口。
  - 本轮未执行后端 pytest。
  - `python scripts/build_installer.py` 已生成 `dist/LarkSync/LarkSync.exe`；未传 `--nsis`，脚本按设计跳过 Windows 安装器生成，未做用户级安装启动体验。

## v0.7.28-dev.6 (2026-07-06)

- 目标：
  - 修正仪表盘“任务概览”和“需要关注”面板高度过短的问题，使它们在宽屏下与左侧主工作区保持同一行高度。
  - 避免再次回到固定 `560px / 390px` 的短面板布局。

- 结果：
  - `DashboardPage` 在 `1760px+` 宽屏下改为 `flex min-h-0 + h-[calc(100vh-2.5rem)]` 工作台布局；统计卡保持顶部固定，下方双栏区域吃掉剩余高度。
  - 双栏区域在宽屏下改为 `items-stretch`，`任务概览` 和 `需要关注` 都使用 `flex min-h-0 flex-col + h-full`，共享同一行高度。
  - `任务概览` 面板移除 `max-h-[560px]`；`需要关注` 列表移除 `max-h-[390px]`，改为 `flex-1 overflow-y-auto` 内部滚动。
  - 中等宽度仍保持自然纵向布局，不强行把单列仪表盘压成固定高度。
  - 新增 `DashboardPage.test.tsx` smoke test，断言宽屏工作台类名存在，且旧的 `max-h-[560px]` / `max-h-[390px]` 不再出现。
  - README、CHANGELOG、根包版本、前端版本和锁文件已同步到 `v0.7.28-dev.6` / `0.7.28-dev.6`。

- 测试：
  - `npm --prefix apps/frontend run test -- DashboardPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - 浏览器检查 `http://127.0.0.1:3666`（`2048x900`）：宽屏下“任务概览”和“需要关注”面板实际高度都为 `722px`，两个内部滚动区分别为 `616px` 和 `588px`，旧的 `560px / 390px` 固定短高度已消失。
  - `python scripts/build_installer.py`

- 问题：
  - 本轮为前端仪表盘布局修正，未改变任务排序、关注事件筛选口径或日志查询接口。
  - 本轮未执行后端 pytest。
  - `python scripts/build_installer.py` 已生成 `dist/LarkSync/LarkSync.exe`；未传 `--nsis`，脚本按设计跳过 Windows 安装器生成，未做用户级安装启动体验。

## v0.7.28-dev.5 (2026-07-06)

- 目标：
  - 修正事件管理页左右区域被内容直接撑开的问题，使左侧运行进程和右侧具体问题都在各自区域内滚动。
  - 明确同一同步进程是否支持多类问题，并在界面上显示问题类型数量。

- 结果：
  - 日志中心在 `events` 页签下使用与任务诊断一致的 `flex min-h-0 + lg:h-[calc(100vh-2.5rem)]` 工作台高度。
  - `EventManagementPanel` 主工作区改为 `flex min-h-0 flex-1`，下方左右网格继承剩余高度；左侧进程列表和右侧问题详情继续使用 `overflow-y-auto`，不再把整页向下撑开。
  - 运行进程卡片从只显示事件条数改为显示 `问题类型数 / 事件数`；问题类型超过 3 类时显示额外数量胶囊。
  - 同一 `runId` 下的事件仍会先按运行进程聚合，再按具体问题类型拆分；右侧可以同时展示多类问题详情。
  - README、CHANGELOG、根包版本、前端版本和锁文件已同步到 `v0.7.28-dev.5` / `0.7.28-dev.5`。

- 测试：
  - `npm --prefix apps/frontend run test -- EventManagementPanel.test.tsx eventManagement.test.ts`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - 浏览器检查 `http://127.0.0.1:3666`：进入日志中心事件管理后，左侧运行进程和右侧具体问题的 `.log-scroll-area` 计算 `overflow-y` 均为 `auto`，页面 `bodyScrollHeight` 等于视口高度 `900`。
  - `python scripts/build_installer.py`

- 问题：
  - 本轮为前端布局和展示文案调整，未改变后端日志查询、同步事件写入或问题分类规则。
  - 本轮未执行后端 pytest。
  - `python scripts/build_installer.py` 已生成 `dist/LarkSync/LarkSync.exe`；未传 `--nsis`，脚本按设计跳过 Windows 安装器生成，未做用户级安装启动体验。

## v0.7.28-dev.4 (2026-07-06)

- 目标：
  - 将事件管理继续改成和任务诊断一致的操作路径：顶部选任务，左侧选同步运行进程，右侧展示具体问题。
  - 移除“按问题 / 按任务”切换，避免事件管理与任务诊断的信息架构不一致。
  - 修正待处理说明和日志体积提醒的配色，避免黄色底色叠黄色文字导致浅色主题下不可读。

- 结果：
  - `EventManagementPanel` 改为三段布局：顶部任务选择条、左侧“运行进程”列表、右侧“具体问题”详情。
  - 顶部任务选择器展示当前任务的问题摘要和最近事件时间；选择任务后会重置左侧进程选择。
  - 左侧运行进程按 `runId` 聚合事件，展示每次运行的最近时间、事件数量和问题组成；无 `runId` 的历史事件会归到“无运行 ID”。
  - 右侧具体问题按问题类型聚合当前运行中的事件，继续展示原因、建议动作和原始事件。
  - 日志体积提醒从 `border-amber + text-amber` 改为中性边框、中性背景和中性文字，浅色主题下不再出现黄色底色 + 黄色文字。
  - 任务卡片“待处理说明”和仪表盘“待处理来源”改为中性说明文字；仪表盘未连接防御提示改为红色错误提示，不再使用黄底黄字。
  - README、CHANGELOG、根包版本、前端版本和锁文件已同步到 `v0.7.28-dev.4` / `0.7.28-dev.4`。

- 测试：
  - `npm --prefix apps/frontend run test -- eventManagement.test.ts EventManagementPanel.test.tsx LogCenterPage.test.tsx`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`
  - `python scripts/build_installer.py`

- 问题：
  - 本轮仍为前端展示调整，未改变后端日志查询、同步运行记录或冲突处理逻辑。
  - 本轮未执行后端 pytest。
  - `python scripts/build_installer.py` 已生成 `dist/LarkSync/LarkSync.exe`；未传 `--nsis`，脚本按设计跳过 Windows 安装器生成，未做用户级安装启动体验。

## v0.7.28-dev.3 (2026-07-06)

- 目标：
  - 按任务诊断页的布局方式重做事件管理，避免继续使用问题卡片平铺。
  - 让“待处理”能落到具体原因，尤其是飞书权限禁止、增强 MD 镜像目录创建失败、Docx 块写入失败和删除目标不存在。
  - 修正事件管理选中态和底色层级，使其与任务诊断页保持一致。
  - 默认隐藏普通上传、下载、跳过和完成事件，减少无操作日志噪音。

- 结果：
  - 新增 `apps/frontend/src/lib/eventManagement.ts`，将同步事件分类为可解释的问题：`mirror_folder_forbidden`、`docx_block_write_forbidden`、`delete_target_missing`、冲突、待删除、取消和普通同步记录。
  - 事件管理面板改为左侧队列 + 右侧详情：左侧可切换“按问题 / 按任务”，右侧展示问题摘要、原因、建议动作、影响任务和原始事件。
  - 默认查询仍只拉取 `failed / delete_failed / conflict / delete_pending / cancelled` 等需关注状态；点击“显示全部事件”后才读取最近 100 条完整同步事件。
  - 选中态统一改为 `border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]`，移除浅色白底按钮；主工作台继续使用 `bg-zinc-900/60`，内部面板使用 `bg-zinc-950/35~40`。
  - 浅色主题补齐 `bg-zinc-950/35`、`bg-zinc-950/45` 和 `bg-zinc-950/60` 覆盖规则；事件管理内部面板在浅色主题下实际计算背景为 `rgb(244,244,245)`，不再把透明深色直接盖在白底上。
  - 当前用户新建任务中的 `_LarkSync_MD_Mirror forbidden` 会显示为“权限禁止：云端镜像目录创建失败”；`创建块失败 / 1770032 / forBidden` 会显示为“权限禁止：云文档内容写入失败”；删除 `not found` 会显示为“删除状态已失效：云端目标不存在”。
  - README、CHANGELOG、根包版本、前端版本和锁文件已同步到 `v0.7.28-dev.3` / `0.7.28-dev.3`。

- 测试：
  - `npm --prefix apps/frontend run test -- eventManagement.test.ts`
  - `npm --prefix apps/frontend run test -- eventManagement.test.ts EventManagementPanel.test.tsx LogCenterPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - 浏览器检查 `http://127.0.0.1:3666`：事件管理页出现“问题队列 / 原因 / 建议动作 / 删除状态已失效：云端目标不存在”，浅色主题下事件左右面板计算背景为 `rgb(244,244,245)`。

- 问题：
  - 本轮仍为前端展示与问题解释调整，未改变后端同步、权限校验、删除幂等或冲突解决逻辑。
  - 本轮未执行后端 pytest 和安装包构建。

## v0.7.28-dev.2 (2026-07-06)

- 目标：
  - 删除事件管理页重复的独立标题横条，减少日志中心内部的无效垂直空间。
  - 将事件管理从平铺事件列表改为可按“问题类型”和“任务”查看，让用户能先判断是哪类问题，再定位来自哪个任务。
  - 收敛事件管理配色，避免整页出现过多成功色或警告色块。
  - 修正仪表盘任务概览过长、右侧“需要关注”底部留白和整体页面过长的问题。
  - 明确任务管理页“待处理”的具体组成，避免只显示一个不可解释的数字。

- 结果：
  - 事件管理只保留一个主工作区，不再渲染单独的“事件管理”横条。
  - 事件管理新增 `按问题 / 按任务` 切换：按问题分组展示 `同步失败 / 删除失败 / 冲突 / 待删除 / 已取消`；按任务分组展示每个任务下的事件组成和最近事件。
  - 事件管理配色改为中性卡片背景，失败、冲突、待删除等状态只通过状态胶囊和小面积文字提示表达。
  - 冲突处理面板只在存在冲突、冲突处理队列或加载错误时展示；没有冲突时不再额外占用一整块空态区域。
  - 仪表盘任务概览默认减少最近任务展示数量，并设置最大高度和内部滚动，避免任务列表把页面拉长。
  - 仪表盘主内容网格改为 `items-start`，右侧“需要关注”不再被左侧任务概览拉伸出底部留白。
  - 仪表盘任务卡路径改为摘要路径展示，并在存在待删、删失败、失败或冲突时显示“待处理来源”。
  - 任务管理页任务卡的“待处理”改为 `队列 / 待删 / 删失败 / 失败 / 冲突` 组成摘要，并补充每类含义：队列是等待上传/创建/重导入，待删是安全删除宽限队列，冲突需要到事件管理选择版本。
  - README、CHANGELOG、根包版本、前端版本和锁文件已同步到 `v0.7.28-dev.2` / `0.7.28-dev.2`。

- 测试：
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`

- 问题：
  - 本轮仍为纯前端展示调整，未改变后端同步、删除宽限和冲突解决逻辑。
  - 本轮未执行后端 pytest 和安装包构建。

## v0.7.28-dev.1 (2026-07-06)

- 目标：
  - 修正仪表盘与日志中心对“待处理”的表达，让用户能区分安全删除宽限队列、同步队列、失败事件和真正需要人工处理的冲突。
  - 降低任务诊断中全 0 无动作任务的噪音，默认优先显示有实际动作或问题的任务。
  - 修正仪表盘在中等宽度窗口下的卡片拥挤、长路径溢出和事件状态颜色不准确问题。

- 结果：
  - 日志中心第三页签从“冲突管理”改为“事件管理”，数据源为 `/sync/logs/sync?statuses=delete_pending&statuses=delete_failed&statuses=failed&statuses=conflict&statuses=cancelled`，默认展示最近 100 条关注事件。
  - 事件管理摘要区按 `待删除 / 失败 / 冲突 / 取消` 分组计数；`delete_pending` 的解释固定为“安全删除宽限队列，到期后自动执行”，不再暗示用户必须手动处理。
  - 冲突处理仍保留在事件管理下方；只有未解决冲突需要用户选择“使用本地”或“使用云端”，已解决冲突继续作为记录展示。
  - 任务诊断默认只显示满足任一条件的任务：正在运行、`problem_count > 0`、上传数/下载数/删除数/待删除数/删除失败数/失败数/冲突数大于 0、最近结果为失败/取消、存在 `last_error`、当前文件状态属于实际动作状态。
  - 任务诊断会隐藏全 0 无动作任务，并在任务选择区显示隐藏数量；用户可点击“显示全部任务”恢复查看全部任务。
  - 仪表盘将 `delete_pending` 与 `queued / creating / created / reimporting` 分开统计；“待处理事件”卡显示待删除数量和同步队列数量，“同步健康”卡会分别显示“待删除”或“有队列”。
  - 仪表盘关注事件的状态颜色改为：失败/删除失败/取消为危险色，冲突/待删除为警告色，同步队列为信息色，成功类为成功色。
  - 仪表盘主内容两列布局改为 `min-[1760px]` 后启用；任务路径、云端 token、事件路径和消息支持换行，减少长路径撑开卡片。
  - README、CHANGELOG、根包版本、前端版本和锁文件已同步到 `v0.7.28-dev.1` / `0.7.28-dev.1`。

- 测试：
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`

- 问题：
  - 本轮为纯前端体验与文案调整，未执行后端 pytest 和安装包构建。
  - `delete_pending` 的后续执行时间仍由后端删除宽限策略决定；本轮只修正前端展示与解释，不改变删除策略。

## v0.7.27 (2026-06-12)

- 目标：
  - 将 `v0.7.27-dev.1` 的 Docx Markdown 上行修复收口为正式稳定版，发布包含“fenced code 资源示例误上传”和“空代码块触发飞书 invalid param”修复的新安装包版本。

- 结果：
  - 当前版本正式提升为 `v0.7.27`。
  - 本次稳定版纳入 `v0.7.27-dev.1` 的 Markdown 上行修复：代码块中的 `![...]()` / `[...](...)` 示例不再被当成真实本地资源替换上传，避免代码示例在 convert/create 链路中被剥离后把 `block_type=14` 代码块清空。
  - `DocxService` 额外补齐了空 code block 的零宽占位兜底，即使历史链路或其他边角场景仍构造出 `code.elements=[]`，发往飞书前也会被修补成合法 payload，不再因 `1770001 invalid param` 让整篇文档替换中止。
  - README、CHANGELOG、根包/前端/后端版本、锁文件、`release-notes-preview.md` 与本开发日志同步对齐到 `v0.7.27` / `0.7.27`。
  - 正式版 Release 继续沿用 tag 驱动的 GitHub Actions 发布链路：推送 `v0.7.27` tag 后会在远端执行 Windows/macOS 质量门、安装包构建、release notes 生成与 Release 资产上传。

- 测试：
  - `python -m pytest tests/test_docx_service.py tests/test_docx_content_write_service.py`（工作目录：`apps/backend/`）
  - 后续正式发布前补跑完整后端 pytest、前端 lint/test/build 与 Windows NSIS 构建验收

- 问题：
  - 真实 GitHub Release 安装包仍以 tag 推送后的远端 workflow 结果为准；本地打包验收通过后仍需等待远端 Release Build 完成资产上传。

## v0.7.26 (2026-06-11)

- 目标：
  - 将 `v0.7.26-dev.1` 的 Markdown 图片上行修复收口为正式稳定版，发布包含用户反馈 400 问题修复的新安装包版本。

- 结果：
  - 当前版本正式提升为 `v0.7.26`。
  - 本次稳定版纳入 `v0.7.26-dev.1` 的 Docx/Markdown 上行修复：本地图片和附件链接解析改为括号感知扫描，避免文件名包含括号时把图片路径截断，进而让残缺 Markdown 进入飞书 `blocks/convert` 并触发 400。
  - README、CHANGELOG、根包/前端/后端版本、锁文件、`release-notes-preview.md` 与本开发日志同步对齐到 `v0.7.26` / `0.7.26`。
  - 正式版 Release 继续沿用 tag 驱动的 GitHub Actions 发布链路：推送 `v0.7.26` tag 后会在远端执行 Windows/macOS 质量门、安装包构建、release notes 生成与 Release 资产上传。

- 测试：
  - 沿用 `v0.7.26-dev.1` 的完整后端 pytest、前端 lint/build、Windows PyInstaller/NSIS 打包与静默安装 helper smoke 验证。

- 问题：
  - 真实 GitHub Release 安装包仍以 tag 推送后的远端 workflow 结果为准。

## v0.7.26-dev.1 (2026-06-11)

- 目标：
  - 修复用户反馈的本地 Markdown 图片未同步上云，并在 `docx/v1/documents/blocks/convert` 返回 400 的问题。

- 结果：
  - 复现确认旧的 Markdown 图片正则只截取到第一个右括号，遇到 `assets/diagram (1).png` 这类文件名时会把路径截成 `assets/diagram (1`，再把残留 `.png)` 继续送入飞书 `blocks/convert`，导致图片无法被替换成占位符并可能触发 400。
  - `DocxMarkdownAssetService` 已将本地图片和附件链接扫描改为括号感知解析，支持转义、嵌套标签、尖括号目标、标题和文件名中的成对括号；占位替换改为逐个替换，减少重复链接场景下的误替换风险。
  - Markdown 列表缩进图片的规范化正则同步放宽到最后一个右括号，避免带括号图片路径在列表上下文中漏掉列表子项转换。
  - `apps/backend/tests/test_docx_service.py` 新增带括号本地图片路径回归测试，确保 convert 前图片语法已被替换为 `LARKSYNC_IMAGE` 占位符。

- 测试：
  - `python -m pytest -q`（工作目录：`apps/backend/`）
  - `python -m pytest tests/test_docx_service.py -q`（工作目录：`apps/backend/`）
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -q`（工作目录：`apps/backend/`）
  - `npm run lint --prefix apps/frontend`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py`
  - `python scripts/build_installer.py --nsis`
  - `python scripts/update_install_smoke.py`

- 问题：
  - 本轮未拿到用户现场的飞书 400 响应体；修复基于本地可复现的 Markdown 解析截断问题，未改动飞书 API 字段。
  - NSIS 安装脚本需要管理员权限并会写入 `Program Files` 与注册表，本轮未直接执行真实安装；已用仓库的非破坏性 Windows 静默安装 smoke 验证 bootstrap/worker/handoff 链路。

## v0.7.25 (2026-05-31)

- 目标：
  - 在 `v0.7.24` tag 工作流因后端全量回归失败而未能出包后，收口修复并发布新的正式稳定版，保证远端 Release Build 能继续推进到安装包构建与资产上传阶段。

- 结果：
  - 当前版本正式提升为 `v0.7.25`。
  - 本次稳定版纳入 `v0.7.25-dev.1` 的质量门修复：Docx 全量替换路径现复用调用方已经拿到的根块子节点数，不再在创建前多打一轮 `GET /blocks`；这避免了 `DocxService` 集成测试里的假响应序列被额外请求打乱，也减少了真实运行时的一次无意义 API 往返。
  - `apps/backend/tests/test_docx_service.py` 已同步补齐插入链路当前行为的全量回归预期，`replace_document_content`、图片/附件块上传、表格单元格填充与 Markdown 插入路径重新与现行 `DocxContentWriteService` / `DocxBlockCreateService` 行为对齐。
  - 仓库版本展示已统一切到稳定版：根包、后端、前端、锁文件、README、CHANGELOG、`release-notes-preview.md` 与本开发日志都已同步更新到 `v0.7.25` / `0.7.25`。

- 测试：
  - `python -m pytest tests/test_docx_service.py tests/test_docx_content_write_service.py tests/test_release.py tests/test_release_notes.py -q`（工作目录：`apps/backend/`）

- 问题：
  - `v0.7.24` 的 tag 工作流已经在远端留下失败记录；本轮通过新版本 `v0.7.25` 继续正式发布，不回写旧 tag 历史。

## v0.7.25-dev.1 (2026-05-31)

- 目标：
  - 修复 `v0.7.24` tag 在 GitHub Actions `quality` 阶段暴露的 7 条后端用例失败，确认问题来自 Docx 写入链路的额外根块重取与过时测试预期，而不是正式版元数据或发布工作流本身。

- 结果：
  - 通过失败日志确认，`replace_document_content()` 在已经持有根块 `children` 数量时仍调用 `create_from_convert(... current_root_children_count=None)`，导致写入前额外执行一次 `GET /blocks`；这会在使用固定假响应序列的 `tests/test_docx_service.py` 中打乱后续 `create / upload / delete` 响应顺序，也让真实运行多一次无意义请求。
  - `DocxContentWriteService.replace_document_content()` 现会把 `remaining_old_children` 直接传给 `create_from_convert()`，既复用当前上下文，也让全量替换与之前新增的失败回滚逻辑保持一致。
  - `tests/test_docx_service.py` 的 `test_insert_markdown_block_creates_children_at_index` 已改为显式覆盖“先 convert，再取根块 children，再插入”的当前调用顺序；配合前述代码修复，整组 `DocxService` 集成测试重新恢复通过。

- 测试：
  - `python -m pytest tests/test_docx_service.py -q`（工作目录：`apps/backend/`）
  - `python -m pytest tests/test_docx_service.py tests/test_docx_content_write_service.py tests/test_release.py tests/test_release_notes.py -q`（工作目录：`apps/backend/`）

- 问题：
  - 本轮只补了后端发布关键路径相关回归，没有再次本地执行完整前端与安装包构建；正式安装包仍以远端 Release Build 的结果为准。

## v0.7.24 (2026-05-31)

- 目标：
  - 将 `v0.7.24-dev.1` 到 `v0.7.24-dev.2` 的修复收口为正式稳定版，发布包含 Windows 自启动路径修正与 Docx 全量替换回滚修复的新安装包版本。

- 结果：
  - 当前版本正式提升为 `v0.7.24`。
  - 本次稳定版纳入两类核心修复：一是 Windows 自启动 Startup 路径拼接在跨平台环境下的兼容问题，避免 CI 在 macOS runner 上模拟 `win32` 时把反斜杠当普通字符；二是 Docx 全量替换在根块接近飞书子节点上限时的透明容器与失败回滚问题，避免空 `text.elements` 持续触发 `invalid param`，并阻止失败写入把云端文档反复追加膨胀。
  - 仓库版本展示已统一切到稳定版：根包、后端、前端、锁文件、README、CHANGELOG 与本开发日志都已同步更新到 `v0.7.24` / `0.7.24`，最新稳定版标识同步对齐。
  - 正式版 Release 继续沿用 tag 驱动的 GitHub Actions 发布链路：tag push 后会在远端执行 Windows 质量门、正式安装包构建、release notes 生成与 Release 资产上传。

- 测试：
  - `python -m pytest tests/test_docx_content_write_service.py tests/test_release.py tests/test_release_notes.py -q`（工作目录：`apps/backend/`）

- 问题：
  - 本轮未在本地执行完整 `build_installer.py` 用户级安装体验验证，正式安装包仍依赖 tag push 后的 GitHub Actions 构建与 smoke 结果确认。

## v0.7.24-dev.2 (2026-05-31)

- 目标：
  - 修复 Docx 全量替换在飞书根块子节点接近上限、且云端文档已经因为前一次失败出现部分重复内容时，继续使用空文本透明容器导致 `invalid param`，并让失败写入不再把云端文档越写越大。

- 结果：
  - 复核线上失败日志与异常 Markdown 样例后确认，这次 `软件设计说明书-V1.4-插图规划说明.md` 的直接触发点是透明容器块 payload 使用了空 `text.elements`，飞书 `docx/v1/.../children` 会返回 `1770001 invalid param`；同时全量替换链路在创建失败后没有回滚已插入的顶层块，会把同一份正文不断追加到云端文档里，形成“越失败越膨胀”的坏状态。
  - `DocxContentWriteService` 现改为先执行“最小尾部旧块腾位”，再根据腾位后的真实根块子节点数决定是否压缩一级块，避免在已经腾出空间后仍提前把 convert 结果包成透明容器。
  - 透明容器块现改为写入合法零宽字符段落，而不是空 `text.elements`，与飞书 Docx 创建子块参数约束保持一致。
  - `create_from_convert()` 现会在 `_create_children_recursive()` 过程中检测失败标记，并基于创建前的根块子节点数回滚本轮刚插入的顶层块，避免下一次同步面对已被部分污染的云端正文。
  - `apps/backend/tests/test_docx_content_write_service.py` 已补齐三条独立回归：透明容器 payload 合法化、删尾腾位后不再误包裹一级块、创建失败后的顶层回滚；仓库版本同步提升到 `v0.7.24-dev.2` / `0.7.24-dev.2`，README 与 CHANGELOG 已补齐本轮问题说明。
  - 现场任务 `算云项目更新` 已于 2026-05-31 21:14 左右完成一次手动重跑，状态为 `success`，原 `创建块失败` 不再出现；但目标文档当前被后端判定为“云端已更新，阻止本地覆盖”的冲突，需要在带本修复的后续构建中继续执行“使用本地”或其他冲突处理动作，才能把修好的 Markdown 正式回写云端。

- 测试：
  - `python -m pytest tests/test_docx_content_write_service.py`（工作目录：`apps/backend/`）

- 问题：
  - 当前正在运行的安装版程序仍是旧构建，尚未包含本次源码修复；如果要在现网任务上彻底完成该文档的云端覆盖，还需要把本修复随下一版构建部署，或在等价环境下用新代码执行一次冲突处理。

## v0.7.24-dev.1 (2026-05-29)

- 目标：
  - 修复 `main` 上非 tag `Release Build` 中的 `quality-macos-packaging` 红灯，避免 macOS runner 运行 Windows 自启动回归时因路径拼接语义差异误报失败。

- 结果：
  - `apps/tray/autostart.py` 的 Windows Startup 快捷方式路径已从单段反斜杠字符串改为逐级目录拼接，避免在非 Windows 主机上模拟 `sys.platform == "win32"` 时把 `Microsoft\Windows\...` 当成一个普通目录名。
  - 本次修复不改变真实 Windows 上自启动 `.lnk` 的目标、参数或工作目录，只消除了单元测试与跨平台 CI 环境中的路径语义漂移。
  - 仓库版本已切入下一开发版：根包、后端、前端、前端 lockfile、README、CHANGELOG 与本开发日志统一提升到 `v0.7.24-dev.1` / `0.7.24-dev.1`，最新稳定版继续保留为 `v0.7.23`。

- 测试：
  - `python -m pytest tests/test_tray_autostart.py tests/test_build_installer.py -q`（工作目录：`apps/backend/`）

- 问题：
  - 本轮只做了本地 Windows 回归；要完全验证 `quality-macos-packaging` 已转绿，还需要下一次远端 `main` workflow 重新运行。

## v0.7.23 (2026-05-29)

- 目标：
  - 将 `v0.7.23-dev.1` 的 CI workflow action 升级收口为正式稳定版，并发布新的 GitHub Release。

- 结果：
  - 正式版纳入 `release-build.yml` 的 action 升级：`actions/checkout`、`actions/setup-python`、`actions/setup-node`、`actions/upload-artifact` 与 `softprops/action-gh-release` 已统一切到当前主版本锚点，消除了发布流水线中的 Node 20 退役告警来源。
  - 后端 workflow 回归测试已覆盖上述 action 主版本，后续若配置回退到旧 action，仓库测试会先失败，不再等到 GitHub Actions 页面告警才发现。
  - 仓库版本展示已统一提升到稳定版：根包、后端、前端、前端 lockfile、README、CHANGELOG 与本开发日志现统一对齐到 `v0.7.23` / `0.7.23`，并继续沿用 tag 驱动的 Release 构建与出包流程。

- 测试：
  - `python -m pytest tests/test_release.py tests/test_release_workflow.py tests/test_build_installer.py -q`（工作目录：`apps/backend/`）

- 问题：
  - 稳定版 Release 资产仍依赖 tag push 后的 GitHub Actions 异步完成；如 runner 侧构建失败或排队，需要继续跟进对应 workflow run。

## v0.7.23-dev.1 (2026-05-29)

- 目标：
  - 升级 GitHub Release workflow 依赖的第三方 actions，清理发布流水线里的 Node 20 退役告警，并让仓库从 `v0.7.22` 稳定版切回下一开发版状态。

- 结果：
  - `.github/workflows/release-build.yml` 中的 `actions/checkout`、`actions/setup-python`、`actions/setup-node`、`actions/upload-artifact` 与 `softprops/action-gh-release` 已分别提升到 `v6`、`v6`、`v6`、`v7` 与 `v3`，Windows 与 macOS 质量检查、制品上传、Release 发布步骤现在统一使用当前主版本锚点。
  - 后端新增 workflow 配置回归测试，直接断言上述 action 的主版本；后续若有人把 workflow 回退到旧版本，CI 会先在仓库测试层失败，而不是等 GitHub Actions 页面再次出现退役告警。
  - 仓库版本号已切入下一开发版：根包、后端、前端、前端 lockfile、README、CHANGELOG 与本开发日志统一提升到 `v0.7.23-dev.1` / `0.7.23-dev.1`，最新稳定版继续保留为 `v0.7.22`。

- 测试：
  - `python -m pytest tests/test_release_workflow.py -q`（工作目录：`apps/backend/`）

- 问题：
  - 本轮只做了 workflow 配置级回归，没有在 GitHub 远端实际触发一次 `release-build.yml`；如需完全闭环，还需要后续通过 PR / tag run 再验证一次真实 runner 行为。

## v0.7.22 (2026-05-29)

- 目标：
  - 将 `v0.7.22-dev.1` 到 `v0.7.22-dev.2` 的公开试用准备与 Windows 开机自启动修复收口为正式稳定版，并触发 GitHub Release 构建与安装包发布。

- 结果：
  - 当前版本正式提升为 `v0.7.22`。
  - 本次稳定版纳入两类用户可见结果：一是公开 Beta 试用与文档入口收敛，首次安装、OAuth 配置、`download_only` 试用路径、安全边界和反馈通道已补齐；二是修复 Windows 开机自启动失效问题，开发态/安装版快捷方式入口已分别对齐到 `apps/tray/launcher.py` 与 `LarkSync.exe`，并支持自动修复历史残留的旧快捷方式。
  - 仓库内版本展示已统一切到稳定版：根包、后端、前端、前端 lockfile、README、CHANGELOG 与本开发日志都已同步到 `v0.7.22`。
  - 正式版 Release 仍沿用 tag 驱动的 GitHub Actions 发布链路：Windows 产物会生成 NSIS 安装包与 `.sha256`，macOS 产物会生成 `x86_64` / `arm64` 双架构 DMG 与 `.sha256`，Release 说明由 `scripts/release_notes.py` 基于 `CHANGELOG.md` 与 `DEVELOPMENT_LOG.md` 自动生成。

- 测试：
  - `python -m pytest tests/test_tray_autostart.py tests/test_build_installer.py -q`（工作目录：`apps/backend/`）
  - `python scripts/build_installer.py --skip-frontend`（工作目录：仓库根目录；确认本地 PyInstaller 打包仍可通过）

- 问题：
  - 稳定版安装包与 GitHub Release 资产仍依赖 tag push 后的 GitHub Actions 异步完成；若远端 runner 排队或失败，需要继续跟进对应 workflow run。

## v0.7.22-dev.2 (2026-05-29)

- 目标：
  - 修复 Windows 托盘版“开机自启动菜单显示已启用，但重启后实际没有拉起”的问题，并确认开发态与安装版入口都指向当前有效启动器。

- 结果：
  - 复核 `apps/tray/autostart.py` 后确认根因有两处：Windows 快捷方式始终硬编码根目录 `LarkSync.pyw`，没有跟随当前受版本控制的 `apps/tray/launcher.py` / 打包后的 `LarkSync.exe`；同时 `toggle_autostart()` 在启用失败时仍无条件返回 `True`，会把失败状态误报成“已启用”。
  - Windows 自启动入口现已按运行形态分流：开发态优先解析仓库内 `apps/tray/launcher.py`（保留 `LarkSync.pyw` 作为兼容回退），打包态直接使用当前 `sys.executable`，工作目录也随之切换为仓库根目录或安装目录，避免安装版继续引用仓库脚本。
  - 新增 Windows 快捷方式规范化与校验逻辑：托盘菜单判断自启动状态时不再只看 `.lnk` 是否存在，而是优先比对快捷方式是否仍指向当前期望入口；托盘手动启动时若发现历史 `.lnk` 仍指向旧入口，会自动重写修复，降低老用户升级后的残留配置风险。
  - `toggle_autostart()` 已改为返回真实启停结果，避免底层创建失败时仍把 UI 和通知文案显示为“已启用”。
  - 补充 `test_tray_autostart.py` 的 Windows 回归：覆盖开发态快捷方式指向 `launcher.py`、打包态快捷方式指向 `LarkSync.exe`、启用失败时 `toggle_autostart()` 返回 `False`。
  - 根包、后端、前端版本号已统一提升到 `v0.7.22-dev.2` / `0.7.22-dev.2`，README 与 CHANGELOG 已同步补齐本轮修复说明。

- 测试：
  - `python scripts/sync_feishu_docs.py`（工作目录：仓库根目录；成功刷新 `docs/feishu/_manifest.json`，终端中文输出仍有编码乱码）
  - `python -m pytest tests/test_tray_autostart.py tests/test_build_installer.py -q`（工作目录：`apps/backend/`）
  - `python scripts/build_installer.py --skip-frontend`（工作目录：仓库根目录；PyInstaller 打包通过，产出 `dist/LarkSync/LarkSync.exe`）

- 问题：
  - 本轮未执行真实用户级“安装包安装 -> 勾选开机自启动 -> 重启系统”体验验证，仍需在安装版环境做一次人工回归，确认旧快捷方式自动修复与开机拉起行为在真实桌面会话中一致。

## v0.7.22-dev.1 (2026-05-28)

- 目标：启动推广前完善工作，先把陌生用户首次试用所需的公开入口、权限/安全说明和反馈闭环补齐。
- 结果：
  - README 首屏新增公开 Beta 试用路径、推荐 `download_only` 起步、已知边界和关键文档入口，避免用户先被完整工程变更列表淹没。
  - 新增 `docs/QUICK_START.md`、`docs/SECURITY_AND_PRIVACY.md`、`docs/FEEDBACK.md`、`docs/FAQ.md`、`docs/PROMOTION_ARTICLE_DRAFT.md`、`docs/OPENCLAW_LOCAL_CACHE_GUIDE.md`、`docs/PROMOTION_ASSETS_CHECKLIST.md`、`docs/PROMOTION_READINESS.md`，分别覆盖首次安装授权、token/日志脱敏、问题反馈模板、常见问题、首篇中文推广草稿、OpenClaw/AI Agent 本地缓存教程、素材准备清单和推广前验收清单。
  - 新增 GitHub Issue Form：bug report、feature request 和联系链接，收集安装、OAuth、同步模式、数据风险、日志摘要等关键信息。
  - 修正 README / USAGE / package / pyproject / lockfile 中的版本展示，统一进入 `v0.7.22-dev.1` 开发态，并保留 `v0.7.21` 作为最近稳定版。
  - 复核 GitHub Release 后发现 `v0.7.21` 只有 tag、没有 Release 和安装包资产；已手动触发 `v0.7.21` 的 Release Build，并确认 Windows 安装包、macOS `arm64` / `x86_64` DMG 与对应 `.sha256` 已上传，`/releases/latest` 现指向 `v0.7.21`。
  - 新增公开 Beta 推广素材：OAuth 配置页、连接飞书页、仪表盘、`download_only` 任务向导、任务卡片、日志中心、本地 Markdown 输出、GitHub Release 下载入口等截图，以及 `quick-start-flow.gif` 快速开始动图；截图使用临时 mock API 和演示数据，避免泄露真实同步任务、路径或 token。
  - 继续补齐冲突管理页面截图和 OAuth 连接流程 GIF；冲突页面通过临时 mock API 构造公开演示数据，避免泄露真实同步任务、路径或 token。
  - 按“只使用真实截图”的素材标准，已撤下非真实托盘菜单示意图和包含该示意图的 Windows 下载启动 GIF；托盘菜单与 Windows 安装启动素材重新标记为待补真实截图 / 真实录屏。
  - `docs/QUICK_START.md`、`docs/PROMOTION_ARTICLE_DRAFT.md`、`docs/PROMOTION_ASSETS_CHECKLIST.md` 与 `assets/promotion/README.md` 已补充素材引用和完成状态；真实 Windows 安装器交互录屏不作为当前推广必需素材，后续如要单独宣传安装体验再补。
  - README 首屏参考高星开源项目常见结构重新收敛为一句话定位、下载/快速开始入口、适合人群、3 分钟试用路径、同步状态预览、核心能力和当前边界；长篇工程化功能列表改为折叠展示，减少陌生用户首次阅读负担。
  - 新增飞书开放平台 OAuth 配置真实脱敏截图：创建企业自建应用入口、应用凭证页、重定向 URL 配置页、权限管理页，并补入 `docs/OAUTH_GUIDE.md` 形成截图级教程。
  - `docs/PROMOTION_READINESS.md` 已同步用户首次试用、OAuth 指南和核心推广素材状态；托盘菜单与安装器交互截图明确降为非必需可选素材，后续只使用真实截图 / 录屏。
- 测试：
  - `python scripts/sync_feishu_docs.py`（已完成，终端中文输出存在编码乱码但脚本成功刷新 manifest）
  - 通过本地临时 mock API + Vite 前端 + Browser 截图验证 `conflict-management.png` 为 1280 × 720。
  - 使用 Pillow 生成并校验 `oauth-connect-flow.gif` 为 960 × 540，文件大小低于 300KB。
  - 人工复核 OAuth 真实脱敏截图为 1280 × 720，且已遮盖 App identity、App ID、企业信息、头像等敏感信息。
- 问题：
  - 公开 GitHub Release 页面仍需在推广前人工确认 Latest 是否指向最新稳定版，并确认 Windows/macOS 安装包与 sha256 完整。

## v0.7.21-dev.1 (2026-05-26)

- 目标：
  - 修复超长飞书文档执行全量 Markdown -> Docx 替换时，根块一级子节点数触及飞书上限后持续报 `too many children in block (1770007)`，并导致后续内容被错误标记为“无效块已跳过”的问题。

- 结果：
  - 复核安装目录日志后确认，问题根因不是块 payload 非法，而是全量替换路径在根块已有 `20000` 个子节点时仍尝试直接追加新的一级块，导致飞书根块子节点上限被击穿。
  - `DocxContentWriteService` 现已在根块接近上限或 convert 结果一级块过多时，自动把一级块压缩为透明文本容器块；这些容器本身不输出额外 Markdown 文本，只负责把大量一级块降层到子块，显著降低根块直接承载的子节点数量。
  - 全量替换路径现已在创建前先计算根块溢出量，只删除最小必要数量的尾部旧块腾位；新内容创建成功后，再删除剩余旧块，避免以往“先全量追加导致立即 1770007”或“为腾位一次删太多旧内容”的极端行为。
  - 新增独立 `test_docx_content_write_service.py`，覆盖“根块接近上限时自动透明包裹一级块”和“创建前只删除最小尾部旧块腾位”两条关键回归路径；既有 `docx_service`、`transcoder`、`sync_runner` 上传链路回归保持通过。
  - 根包、后端与前端版本号已同步更新到 `v0.7.21-dev.1` / `0.7.21-dev.1`，README 与 CHANGELOG 已同步补齐本轮大文档写入修复说明。

- 测试：
  - `python -m pytest tests/test_docx_content_write_service.py tests/test_docx_service.py tests/test_sync_runner_block_update.py tests/test_sync_runner_upload_new_doc.py tests/test_transcoder.py -q`（工作目录：`apps/backend/`）
  - `python -m pytest tests/test_config.py tests/test_config_api.py tests/test_auth_api.py -q`（工作目录：`apps/backend/`）

## v0.7.20-dev.2 (2026-05-26)

- 目标：
  - 确认并修复默认授权配置仍停留在旧 `docs:doc`，导致用户按默认指引完成授权后，Docx v1 文档接口仍可能报缺少权限的问题。

- 结果：
  - 复核当前实现后确认，LarkSync 的文档读写链路已经全面使用 `/open-apis/docx/v1/...`，包括块读取、块写入、图片回填与 `documents/blocks/convert`，原默认权限说明中的 `docs:doc` 已不再匹配实际接口集合。
  - `ConfigManager` 现已将默认 `auth_scopes` 切换为 `drive:drive`、`docx:document`、`docx:document:readonly`、`docx:document.block:convert`、`drive:drive.metadata:readonly`、`contact:contact.base:readonly`。
  - 对历史配置加入了运行时兼容迁移：若本地 `config.json` 仍保留旧 `docs:doc`，后端会自动把它展开为新版 Docx scopes，并补齐当前实现所需的最小权限集合。
  - OAuth 配置指南、前端内嵌 `oauth-guide.html`、README、USAGE、CLI 权限提示与任务创建页错误文案已同步更新，用户在授权失败时会看到新版 Docx 权限名，而不再被旧 `docs:doc` 误导。
  - 根包、后端与前端版本号已同步更新到 `v0.7.20-dev.2` / `0.7.20-dev.2`。

- 测试：
  - `python -m pytest tests/test_config.py tests/test_config_api.py tests/test_auth_api.py -q`（工作目录：`apps/backend/`）
  - `npm run test`（工作目录：`apps/frontend/`）
  - `npm run build`（工作目录：`apps/frontend/`）
  - `python scripts/build_installer.py --skip-frontend`（工作目录：仓库根目录；已完成 PyInstaller 构建，未执行用户级安装/启动体验验证）

## v0.7.20-dev.1 (2026-05-25)

- 目标：
  - 深入排查近期 `refresh token is invalid | refresh token not found (code=20026)` 的真实触发条件，并收口最可能复发的认证续期竞争窗口。

- 结果：
  - 复核当前项目实际使用的飞书 OAuth 端点后，确认 `https://open.feishu.cn/open-apis/authen/v1/access_token` 在收到无效 refresh token 时会真实返回 `code=20026` 与 `refresh token is invalid | refresh token not found`，不是前端拼接文案。
  - 通过受控并发实验复现了“同一个过期 access token 被两个协程同时续期，其中一个 refresh 成功并轮换 refresh token，另一个立即收到 `code=20026`”的竞争路径，确认现网风险来自本地 refresh 缺少串行化，而不只是飞书偶发波动。
  - `AuthService` 现已为 refresh / `get_valid_access_token()` 增加按事件循环共享的续期锁；等待中的协程会在前一个 refresh 完成后复读 token store，若 access token 已被更新则直接复用，不再带着旧 refresh token 再打一遍飞书。
  - token 响应缺少新 `refresh_token` 时，后端现会保留已有 refresh token 而不是覆盖为空字符串，减少兼容端点 / 临时响应差异导致后续续期链路自毁的风险。
  - README、CHANGELOG 与版本号已同步更新到 `v0.7.20-dev.1` / `0.7.20-dev.1`，便于后续继续跟踪 auth 稳定性问题。

- 测试：
  - `python -m pytest tests/test_auth_service.py tests/test_auth_api.py tests/test_security.py -q`（工作目录：`apps/backend/`）

## v0.7.19 (2026-05-24)

- 目标：
  - 将已完成并验证通过的 mac 版本开发结果收口为正式版发布。

- 结果：
  - 当前版本正式提升为 `v0.7.19`。
  - GitHub Actions 正式验证链路已覆盖 `macos-14 (arm64)` 与 `macos-15-intel (x86_64)`，两条 macOS 安装包构建与 install-launch smoke 均已通过。
  - DMG 安装包验证已覆盖卷内 `Applications` 安装入口校验、`.app` 复制与 bundle 启动 `/health` 检查。
  - 后端运行时与打包链路已显式固定 `greenlet` 依赖，避免 macOS bundle 在数据库初始化阶段冷启动崩溃。
  - README、USAGE、CHANGELOG、版本号与发布元数据已同步切换到正式版。

- 测试：
  - GitHub Actions run `26343462840`：`quality`、`quality-macos-packaging (macos-14, arm64)`、`quality-macos-packaging (macos-15-intel, x86_64)` 全部通过。
  - `python -m pip install --dry-run -e apps/backend`

## v0.7.19-dev.8 (2026-05-24)

- 目标：
  - 在 Apple Silicon 安装启动 smoke 已通过的前提下，继续缩小 Intel 验证的外部排队风险，并把 DMG 安装入口本身纳入自动化证据。

- 结果：
  - `.github/workflows/release-build.yml` 中的 Intel mac runner 已从 `macos-13` 切换到 `macos-15-intel`，继续保留 `arm64` 对应的 `macos-14`，以便更贴近 GitHub 当前可用的 Intel mac 标签并降低长期排队风险。
  - `scripts/macos_installer_smoke.py` 现在会在挂载 DMG 后显式检查卷内 `Applications` 安装入口是否存在且正确指向 `/Applications`，把“可拖拽安装”的关键入口也纳入 smoke 范围。
  - `test_macos_installer_smoke.py` 已补充 `Applications` 安装入口存在性与目标路径校验，`test_release_workflow.py` 已同步更新 Intel runner 期望值与双架构 matrix 断言。
  - 根包、后端与前端版本号已同步更新到 `v0.7.19-dev.8` / `0.7.19-dev.8`，README、USAGE、CHANGELOG 已同步补齐本轮 Intel runner 与 DMG 安装入口验证记录。

- 测试：
  - `python -m pytest tests/test_macos_installer_smoke.py tests/test_release_workflow.py -q`（工作目录：`apps/backend/`）

## v0.7.19-dev.7 (2026-05-24)

- 目标：
  - 在 arm64 mac smoke 已恢复通过的基础上，减少 GitHub matrix 策略本身对 Intel 验证结果的干扰，避免再次因为某个架构先失败而自动取消另一条验证。

- 结果：
  - `.github/workflows/release-build.yml` 中 `quality-macos-packaging` 与正式版 `build-macos` 的 matrix 现都显式设置 `fail-fast: false`。
  - 这样即使 `arm64` 或 `x86_64` 某一条先失败，另一条构建、DMG 生成和安装启动 smoke 仍会继续执行并保留结果，便于完整收集双架构证据，而不是被 GitHub 默认 fail-fast 中断。
  - `test_release_workflow.py` 已补充对双 mac matrix `fail-fast: false` 的断言，避免后续 CI 配置回退。
  - 根包、后端与前端版本号已同步更新到 `v0.7.19-dev.7` / `0.7.19-dev.7`，README、USAGE、CHANGELOG 已同步补齐本轮 CI 策略收口记录。

- 测试：
  - `python -m pytest tests/test_release_workflow.py -q`（工作目录：`apps/backend/`）

## v0.7.19-dev.6 (2026-05-24)

- 目标：
  - 修复 `v0.7.19-dev.5` 之后 arm64 安装启动 smoke 仍失败的问题，确认是“打包漏收”还是“构建环境根本没装依赖”，并把修复点前移到依赖声明层。

- 结果：
  - GitHub arm64 job 日志确认构建环境安装 `apps/backend/requirements.txt` 时并没有安装 `greenlet`，即 Python 3.14 arm64 上当前 `sqlalchemy` 发行元数据不会自动把该包带进来。
  - `apps/backend/requirements.txt` 与 `apps/backend/pyproject.toml` 现都已显式加入 `greenlet>=3.0`，保证本地开发、CI、可编辑安装和打包构建都在同一层面声明该运行时依赖。
  - 保留 `scripts/build_installer.py` / `scripts/larksync.spec` 对 `greenlet` 的显式 hiddenimport，避免即使依赖已安装，PyInstaller 后续再次因为分析路径变化漏收该模块。
  - `test_build_installer.py` 新增对后端运行时元数据中 `greenlet>=3.0` 的断言，防止依赖声明再次被回退。
  - 根包、后端与前端版本号已同步更新到 `v0.7.19-dev.6` / `0.7.19-dev.6`，README、USAGE、CHANGELOG 已同步补齐本轮依赖层修复记录。

- 测试：
  - `python -m pytest tests/test_build_installer.py tests/test_macos_installer_smoke.py tests/test_release_workflow.py -q`（工作目录：`apps/backend/`）

## v0.7.19-dev.5 (2026-05-24)

- 目标：
  - 根据 `v0.7.19-dev.4` 新增的 mac 安装启动 smoke 诊断，修复 arm64 打包产物真实启动失败的根因，而不是继续在 CI 上盲等或只调超时。

- 结果：
  - 通过 GitHub arm64 job 日志确认根因是安装后 bundle 在 `src/db/session.py -> sqlalchemy.ext.asyncio` 初始化数据库时崩溃，报 `ValueError: the greenlet library is required ... No module named 'greenlet'`。
  - `scripts/build_installer.py` 的 `PYINSTALLER_HIDDENIMPORTS` 与仓库内 `scripts/larksync.spec` 现都已显式加入 `greenlet`，避免 mac / Windows 打包产物在运行期缺少该依赖。
  - `test_build_installer.py` 已补充对生成 spec 中 `greenlet` hiddenimport 的断言，防止后续 spec 生成器与仓库内 spec 再次漂移。
  - 根包、后端与前端版本号已同步更新到 `v0.7.19-dev.5` / `0.7.19-dev.5`，README、USAGE、CHANGELOG 已同步补齐本轮 mac 打包修复记录。

- 测试：
  - `python -m pytest tests/test_build_installer.py tests/test_macos_installer_smoke.py tests/test_release_workflow.py -q`（工作目录：`apps/backend/`）

## v0.7.19-dev.4 (2026-05-24)

- 目标：
  - 针对 GitHub mac runner 上 `Run macOS install-launch smoke` 仍只报 `Connection refused` 的黑盒失败，补齐安装后启动 smoke 的进程诊断信息，并适度放宽等待窗口，尽快拿到可行动的 CI 证据。

- 结果：
  - `scripts/macos_installer_smoke.py` 现在会把安装后 bundle 的 stdout/stderr 分别落到临时日志文件，并在 bundle 提前退出或健康检查超时时，把退出码、stdout/stderr 尾部和 `AppData/logs/larksync.log` 尾部一起回抛到 CI 日志。
  - mac 安装启动 smoke 的默认等待时间已从 20 秒提升到 60 秒，降低 GitHub runner 上因为首次冷启动、数据库初始化或后台服务启动稍慢而误报失败的概率。
  - `test_macos_installer_smoke.py` 已补充失败诊断与提前退出场景回归，确保后续不会再回退到“CI 失败但没有有效上下文”的状态。
  - 根包、后端与前端版本号已同步更新到 `v0.7.19-dev.4` / `0.7.19-dev.4`，README、USAGE、CHANGELOG 已同步补齐本轮 mac smoke 诊断增强记录。

- 测试：
  - `python -m pytest tests/test_macos_installer_smoke.py tests/test_release_workflow.py tests/test_build_installer.py tests/test_update_service.py tests/test_backend_manager.py tests/test_system_update_api.py tests/test_tray_update_install.py tests/test_tray_autostart.py tests/test_security.py tests/test_paths.py -q`（工作目录：`apps/backend/`）

## v0.7.19-dev.3 (2026-05-24)

- 目标：
  - 在已有 mac 构建 smoke 基础上继续补足安装 / 启动级验证，尽量让 CI 直接覆盖“DMG 能挂载、`.app` 能安装、bundle 能启动”这条链路，而不是只停留在产物生成。

- 结果：
  - 新增 `scripts/macos_installer_smoke.py`，会自动选择指定架构 DMG、挂载镜像、复制 `LarkSync.app` 到临时安装目录，并直接启动 `.app/Contents/MacOS/LarkSync --backend` 轮询 `/health`，形成 macOS 安装 / 启动 smoke。
  - `quality-macos-packaging` 与正式版 `build-macos` workflow 现在都会在 DMG 构建后执行安装 / 启动 smoke，避免发布链路只验证“能打包”，不验证“安装后能否真实启动”。
  - macOS 打包与发布默认策略进一步收口为双架构原生产物：`macos-13 -> x86_64`、`macos-14 -> arm64`；更新服务新增架构感知选择逻辑，会优先选择与当前机器架构匹配的 DMG，在无匹配时再回退到 `universal2` / 通用命名产物。
  - `release-build.yml` 新增 workflow 级 `concurrency`，会按 PR 编号 / ref 自动取消旧的 in-progress / queued run，减少 macOS runner 被过期提交长期占队导致当前验证结果迟迟出不来的问题。
  - 新增 `test_macos_installer_smoke.py`，并扩展 `test_build_installer.py`、`test_update_service.py`、`test_release_workflow.py` 覆盖 DMG 架构后缀、安装 smoke、workflow matrix 与架构感知更新选择逻辑。
  - 根包、后端与前端版本号已同步更新到 `v0.7.19-dev.3` / `0.7.19-dev.3`，README、USAGE、CHANGELOG 已同步补齐本轮 mac 安装 smoke 记录。

- 测试：
  - `python -m pytest tests/test_macos_installer_smoke.py tests/test_release_workflow.py tests/test_build_installer.py tests/test_update_service.py tests/test_backend_manager.py tests/test_system_update_api.py tests/test_tray_update_install.py tests/test_tray_autostart.py tests/test_security.py tests/test_paths.py -q`（工作目录：`apps/backend/`）

## v0.7.19-dev.2 (2026-05-24)

- 目标：
  - 修复远端 macOS CI 在 `quality-macos-packaging` 阶段误报失败的问题，确保 darwin runner 能真正执行定向回归与 DMG smoke，而不是因为 workflow 缺依赖提前退出。

- 结果：
  - `quality-macos-packaging` 的 Python 依赖安装步骤现已与主 `quality` 任务对齐，除业务依赖外会额外显式安装 `pytest>=7.4` 与 `pytest-asyncio>=0.23`，修复 GitHub Actions `macos-14` runner 报 `No module named pytest` 后直接跳过 DMG smoke 的问题。
  - 新增 `apps/backend/tests/test_release_workflow.py`，解析 `.github/workflows/release-build.yml` 并断言 mac packaging job 复用与主 `quality` 一致的 pytest bootstrap，避免未来再次出现 Windows 任务能跑、mac 任务漏装测试依赖的回归。
  - `test_build_installer`、`test_backend_manager` 与 `test_update_service` 中原本写死的 Windows `PYTHONPATH` / `APPDATA` 假设已调整为跨平台断言：darwin runner 现在会使用 POSIX `site-packages` 样例与 `HOME/Library/Application Support/LarkSync` 期望根目录，不再因为测试样例本身带有 Windows 盘符与分隔符而误报失败。
  - 由于 `Pillow` 等扩展在 GitHub mac runner 上安装到的是单架构 wheel，PyInstaller 在 `target_arch=universal2` 下无法通过 `COLLECT` 阶段；为保证 Intel / Apple Silicon 真机均可持续验证，mac 打包默认策略已改为“按 runner 原生架构出包”，Release workflow 会分别生成 `x86_64` 与 `arm64` DMG，更新服务也会优先选择与当前机器架构匹配的安装包，并在无匹配时回退到 `universal2` / 通用命名资产。
  - 根包、后端与前端版本号已同步更新到 `v0.7.19-dev.2` / `0.7.19-dev.2`，CHANGELOG 已补齐本次 CI 修复记录。

- 测试：
  - `python -m pytest tests/test_release_workflow.py tests/test_build_installer.py tests/test_update_service.py tests/test_system_update_api.py tests/test_tray_update_install.py tests/test_backend_manager.py tests/test_tray_autostart.py tests/test_security.py tests/test_paths.py -q`（工作目录：`apps/backend/`）

## v0.7.19-dev.1 (2026-05-24)

- 目标：
  - 收口 macOS 安装版剩余缺口，确保 DMG 更新请求、自启动 LaunchAgent 与打包态托盘日志目录真正适配 `.app` 运行形态，而不是只在 Windows 链路下通过。

- 结果：
  - `update_service` 与 `tray_app` 现已统一安装包版本识别规则，同时支持 Windows `LarkSync-Setup-*.exe` 和 macOS `LarkSync-*.dmg`，旧版本 DMG 不再绕过“无需再次安装”与“忽略过期安装请求”保护。
  - `autostart.py` 的 mac 自启动链路改为开发态使用受版本控制的 `apps/tray/launcher.py`，打包态直接启动 `.app` 内可执行文件，并将 `tray-stdout.log` / `tray-stderr.log` 统一写入用户数据目录。
  - `backend_manager` 在打包态启动后端时，stderr 日志目录改为复用运行时用户数据目录，不再默认写回应用目录/包内目录；托盘更新通知文案也按 macOS 改为“打开安装包后手动重启应用”的真实行为说明。
  - 补充了 mac 侧自动化回归：覆盖 DMG 版本识别、DMG 旧版本拒绝安装、托盘对 `.dmg` 过期请求的忽略、自启动 LaunchAgent 生成、打包态日志目录，以及 `build_installer._build_dmg()` 的 `.app` 发现与环境变量透传。
  - GitHub Release 工作流的稳定版 tag 构建已改为默认同时产出 Windows `exe` 与 macOS `dmg`；仅手动 `workflow_dispatch` 重跑时才允许跳过 mac，避免正式版发布时漏掉 mac 安装包。
  - 额外新增 `pull_request` / `push main` 的 macOS 定向 pytest + 打包 smoke，持续验证 LaunchAgent、更新安装、路径与 `.app` / `dmg` 构建链路，把 mac 发布风险前移到日常 CI。
  - macOS PyInstaller spec 默认目标架构已收口到 `universal2`，并支持通过 `LARKSYNC_MACOS_TARGET_ARCH` 显式覆盖；日常 mac smoke 扩展到 Intel `macos-13` 与 Apple Silicon `macos-14` runner，更贴近规格里的 `Intel/M-series` 兼容目标。
  - 根包、后端与前端版本号已同步更新到 `v0.7.19-dev.1` / `0.7.19-dev.1`，README、CHANGELOG 已同步补齐本轮 mac 修复记录。

- 测试：
  - `python -m pytest tests/test_update_service.py tests/test_system_update_api.py tests/test_tray_update_install.py tests/test_backend_manager.py tests/test_tray_autostart.py tests/test_build_installer.py tests/test_security.py tests/test_paths.py -q`（工作目录：`apps/backend/`）

## v0.7.18 release (2026-05-24)

- 目标：
  - 发布 `v0.7.18` 稳定版，收口隐藏/缓存路径默认忽略开关，并消除 `SyncEventPipeline` 在测试与应用关闭阶段遗留的 pending task 噪音。

- 结果：
  - 同步器新增全局 `ignore_hidden_cache_paths` 开关，默认忽略所有以 `.` 开头的文件/目录以及 `__pycache__`，设置页可单独关闭。
  - `SyncEventPipeline` 改为 `TimerHandle + flush_now/close` 收尾模型；`SyncTaskRunner.close()`、应用 `lifespan` 关闭路径与 `/system/shutdown` 现已显式清空 pending 事件并停止 watcher，避免退出时遗留后台 flush task。
  - 根包、后端与前端版本号已同步收口到 `v0.7.18` / `0.7.18`，CHANGELOG 已追加正式版记录。

- 测试：
  - `$env:PYTHONPATH='apps/backend'; .\.venv\Scripts\python.exe -m pytest apps/backend/tests/test_sync_event_pipeline.py apps/backend/tests/test_main.py apps/backend/tests/test_config_api.py apps/backend/tests/test_sync_runner.py apps/backend/tests/test_release.py -q`
  - `npm --prefix apps/frontend run test -- src/components/settings/SettingsPanels.test.tsx src/pages/SettingsPage.test.tsx`
  - `npm --prefix apps/frontend run typecheck`
  - `npm --prefix apps/frontend run build`

## v0.7.18-dev.1 (2026-05-24)

- 目标：
  - 解决实际安装版持续扫描 `.docx_tools` 等隐藏工具目录导致的同步失败，为同步器补齐“默认忽略隐藏/缓存路径”的全局配置，并保留用户可关闭的设置开关。

- 结果：
  - `AppConfig` / `/config` 新增 `ignore_hidden_cache_paths`，默认值为 `true`，支持持久化保存和环境变量覆盖。
  - `sync_runner._should_ignore_path()` 新增隐藏/缓存路径判定：开启时默认跳过所有以 `.` 开头的文件或目录，以及 `__pycache__`，任务级 `ignored_subpaths` 仍继续生效。
  - 设置页“本地忽略目录”面板新增“默认忽略隐藏/缓存路径”开关，用户可以按需关闭该默认规则，再仅依赖任务级忽略目录。
  - README、CHANGELOG 与前后端版本号已同步更新到 `v0.7.18-dev.1` / `0.7.18-dev.1`，随后本轮正式收口为 `v0.7.18` / `0.7.18`。

- 测试：
  - `$env:PYTHONPATH='apps/backend'; .\.venv\Scripts\python.exe -m pytest apps/backend/tests/test_config_api.py apps/backend/tests/test_sync_runner.py -q`
  - `npm --prefix apps/frontend run test -- src/components/settings/SettingsPanels.test.tsx src/pages/SettingsPage.test.tsx`
  - `npm --prefix apps/frontend run typecheck`

## v0.7.17 release (2026-05-23)

- 目标：
  - 发布 `v0.7.17` 稳定版，将 `v0.7.17-dev.1` 到 `v0.7.17-dev.33` 的工程化治理、日志中心/前端组件化收口、后端大模块拆分、Windows 静默安装稳定性修复与 PyInstaller 构建基线治理作为正式能力对外发布。

- 结果：
  - 正式版纳入本轮全部工程化收口：前端质量门、FastAPI `lifespan`、SQLite schema version 迁移注册表、日志中心 DB-first 读取链路，以及 `sync_runner` / `docx_service` / `transcoder` / `tray_app` 的阶段性服务拆分已全部进入稳定版。
  - Windows 静默安装链路现已覆盖 PowerShell 5.1 BOM 编码兼容、helper `creationflags` 分级回退、真实 `bootstrap/worker` smoke 回归与安装脚本 helper 模块化，正式版更新链路较 `v0.7.16` 继续提升了受限环境下的可恢复性。
  - PyInstaller 构建基线已固定为 `Python 3.14.x / Node 25.x`，并通过仓库级 `hook-pydantic.py` / `hook-fastapi._compat.shared.py` 排除了未使用的 `pydantic.v1` 命名空间，正式版构建日志不再持续出现兼容层噪音。
  - 本地正式安装包已生成 `dist/LarkSync-Setup-v0.7.17.exe`，SHA256 为 `e32c397822b1c3b55e90f1c8dce2a26721f2199473ed90fdc00b767b01bfbc60`。

- 测试：
  - `python -m pytest -q`（工作目录：`apps/backend/`，并将 `TEMP/TMP` 指向仓库内 `.tmp-tests-root`）
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - `python scripts/update_install_smoke.py`
  - `python scripts/build_installer.py --nsis`

## v0.7.17-dev.33 (2026-05-23)

- 目标：
  - 继续收口工作流 A/F 中遗留的构建噪音问题，确认 Python 3.14 基线下的 PyInstaller 打包不再把未使用的 `pydantic.v1` 兼容层带进分析结果。
- 结果：
  - 新增 `scripts/pyinstaller_hooks/hook-pydantic.py` 与 `hook-fastapi._compat.shared.py`，分别在 PyInstaller hook 层排除 `pydantic.v1` 子模块，以及 FastAPI `_compat.shared` 中对 `pydantic.v1` 的静态兼容导入。
  - `scripts/larksync.spec` 和 `scripts/build_installer.py` 已切换到仓库自定义 `hookspath`，确保正式打包与本地重建 spec 都使用同一套 hooks。
  - 重新构建后，PyInstaller 日志不再出现 `Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater`；同时 `build/larksync/PYZ-00.toc`、`xref-larksync.html`、`warn-larksync.txt` 中也已确认没有 `pydantic.v1` 命中。
- 测试：
  - `python -m pytest tests/test_build_installer.py -q`（工作目录：`apps/backend/`，并将 `TEMP/TMP` 指向仓库内 `.tmp-tests-root`）
  - `python scripts/build_installer.py --nsis`
  - `rg -n "pydantic\\.v1" build/larksync/PYZ-00.toc build/larksync/xref-larksync.html build/larksync/warn-larksync.txt`
- 问题：
  - 当前规划相关代码和阶段性验收已经进一步收口，但 `.git` 目录 ACL 仍阻止创建 `index.lock`，所以本轮版本依旧无法按要求落本地 Git 提交；如果下一步要推进到正式版收口或发布，仍需先解除该环境阻塞。

## v0.7.17-dev.32 (2026-05-23)

- 目标：
  - 继续落实工作流 B/F，把 `apps/tray/tray_app.py` 中耦合的 Windows 安装链路 helper 收口出去，在不改变静默安装行为的前提下继续降低托盘主入口复杂度。
- 结果：
  - 新增 `apps/tray/windows_install_helper.py`，承载 PowerShell helper 启动参数、PowerShell 命令构造、脚本文件写入编码、安装脚本 stem 生成，以及静默安装 `worker.ps1` / `bootstrap.ps1` 模板文本。
  - `tray_app.py` 现通过薄包装函数委托这些实现，保留 `_build_windows_installer_worker_script`、`_build_windows_silent_bootstrap_command`、`_launch_hidden_helper_process` 等原有接口与测试入口；主文件从 1247 行降到 1034 行。
  - 真实 `python scripts/update_install_smoke.py` 继续能在当前受限环境下推进到 `launch_failed`，说明这轮拆分没有破坏前一版刚修好的 helper 启动回退链路。
- 测试：
  - `python -m pytest tests/test_tray_update_install.py tests/test_update_install_smoke.py tests/test_system_update_api.py tests/test_main.py tests/test_tray_status.py -q`（工作目录：`apps/backend/`，并将 `TEMP/TMP` 指向仓库内 `.tmp-tests-root`）
  - `python scripts/update_install_smoke.py`
- 问题：
  - 当前代码与回归都已完成，但 `.git` 目录 ACL 仍阻止创建 `index.lock`，所以本轮版本依旧无法按要求落本地 Git 提交；如果下一步要继续严格执行“一版一提交”，仍需要先解除该环境阻塞。

## v0.7.17-dev.31 (2026-05-23)

- 目标：
  - 收口工作流 F 的最后一个实际阻塞点，修复 Windows 静默安装 smoke 在受限环境下因 helper 进程无法使用 `CREATE_BREAKAWAY_FROM_JOB` 启动而直接失败的问题，并让真实托盘静默安装链路也具备同样的回退能力。
- 结果：
  - `apps/tray/tray_app.py` 新增隐藏 helper 启动回退逻辑：优先尝试 `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB`，若遇到 `PermissionError` / `WinError 1314` 等受限环境错误，会自动回退到不带 breakaway 的隐藏进程组，必要时最终回退到 `creationflags=0`。
  - `scripts/update_install_smoke.py` 现复用同一套 helper 启动回退逻辑，并把实际采用的 `launch_creationflags` 与回退日志写进 smoke 结果，便于区分“helper 启动失败”和“安装器自身失败”。
  - 新增对应回归测试，覆盖托盘真实静默安装调度的回退顺序，以及 smoke 脚本在首轮 `PermissionError` 后仍能推进到 `launch_failed` 的场景。
- 测试：
  - `python -m pytest tests/test_update_install_smoke.py tests/test_tray_update_install.py tests/test_system_update_api.py -q`（工作目录：`apps/backend/`，并将 `TEMP/TMP` 指向仓库内 `.tmp-tests-root`）
  - `python -m pytest tests/test_main.py tests/test_tray_status.py -q`（工作目录：`apps/backend/`，并将 `TEMP/TMP` 指向仓库内 `.tmp-tests-root`）
  - `python scripts/update_install_smoke.py`
- 问题：
  - 当前代码和回归都已完成，但 `.git` 目录仍存在 ACL 写入限制，当前环境下无法创建 `index.lock`，因此本轮版本仍不能按要求落本地 Git 提交；后续若要继续严格执行“一版一提交”，需先解除该环境阻塞。

## v0.7.17-dev.30 (2026-05-23)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/transcoder.py` 中的内嵌 sheet 预览与 add-ons 渲染逻辑，把表格矩阵处理和附加块文本渲染从主转码器中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/transcoder_sheet_helper.py`，承载内嵌 sheet 预览转码、token 解析、表格矩阵裁剪、单元格富文本格式化，以及 add-ons 的 Mermaid/text 代码块渲染。
  - `DocxTranscoder` 现通过 `TranscoderSheetHelper` 处理 `sheet_tables` 预取、sheet placeholder 回退和 add-ons 文本块渲染，`transcoder.py` 从 1031 行进一步降到 754 行。
- 测试：
  - `python -m pytest tests/test_transcoder.py -q`
  - `python -m pytest tests/test_docx_service.py tests/test_transcoder.py tests/test_sync_runner.py -q`
  - 上述 pytest 在当前沙箱下需将 `TEMP/TMP` 指向仓库内 `.tmp-tests-root` 目录，否则 `tmp_path` fixture 会因系统临时目录写权限受限而失败。
- 问题：
  - 当前主要剩余的大模块已集中到 `sync_runner.py`（2595 行）、`docx_service.py`（1428 行）和 `tray_app.py`（1199 行）；后续若继续做结构治理，应优先在这三个模块里挑“高风险行为 + 已有回归保护”的区段继续拆。

## v0.7.17-dev.29 (2026-05-23)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/docx_service.py` 中的 Markdown convert 前后处理，把 continuation/placeholder 预处理与文本块修补 helper 从主文档服务中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/docx_markdown_convert_helper.py`，承载列表 continuation 归一化、placeholder pattern 处理、块纯文本重写和 continuation 重新挂接逻辑。
  - `docx_service.py` 现通过独立 helper 模块复用这些能力，并继续保留 `_normalize_markdown_for_convert`、`_replace_continuation_placeholders` 等原导出名以兼容现有测试；主文件从 1766 行降到 1428 行。
- 测试：
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_docx_service.py tests/test_main.py -q`
  - 上述 pytest 在当前沙箱下需将 `TEMP/TMP` 指向仓库内 `.tmp-tests-root` 目录，否则 `tmp_path` fixture 会因系统临时目录写权限受限而失败。
- 问题：
  - `.git` 目录仍存在写入限制，当前环境下无法创建 `index.lock`，因此这两轮版本还不能按“一版一提交”落本地 Git；代码与回归已完成，但版本提交仍受环境阻塞。

## v0.7.17-dev.28 (2026-05-23)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/sync_runner.py` 中的 Markdown 上传主编排，把冲突校验、块级状态、同 token 覆盖与导入重建回退从主 runner 中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/sync_markdown_upload_service.py`，承载 `_upload_markdown` 的链接读取、资源签名判断、冲突阻断、块级状态跳过、同 token 覆盖、导入重建回退、镜像同步与最终链接回写。
  - `SyncTaskRunner` 现通过 `SyncMarkdownUploadService` 执行 `_upload_markdown`，保留原方法作为兼容代理；`sync_runner.py` 进一步从 2707 行降到 2595 行。
  - 修复了服务拆分后的一个关键回归点：测试会在 runner 构造后替换 `runner._block_service`，因此 `SyncMarkdownUploadService` 改为通过动态 `list_block_states` 回调读取当前 block service，而不是静态持有初始化时的实例。
- 测试：
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py tests/test_main.py -q`
  - 上述 pytest 在当前沙箱下需将 `TEMP/TMP` 指向仓库内 `.tmp-tests-root` 目录，否则 `tmp_path` fixture 会因系统临时目录写权限受限而失败。
- 问题：
  - 当前沙箱对 `.git` 目录存在 ACL 写入限制，`git add/commit` 会在创建 `.git/index.lock` 时直接被拒绝；代码与测试已经完成，但这轮版本暂时无法在当前环境内落本地 Git 提交。

## v0.7.17-dev.27 (2026-05-23)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/sync_runner.py` 中的单文件上传细节，把上传路径分发、通用文件上传与旧云端文件清理从主 runner 中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/sync_path_upload_service.py`，承载 `_upload_path` 的路径分发、重复触发保护、MD 模式跳过判断，以及 `_upload_file` 的签名检查、父目录解析、旧云端同名文件清理和链接更新。
  - `SyncTaskRunner` 现通过 `SyncPathUploadService` 处理 `_upload_path`、`_upload_file` 与 `_cleanup_replaced_cloud_files`，保留原方法作为兼容代理，Markdown 上传主链路继续留在 runner 中，便于下一轮继续拆深层逻辑。
  - 新增 `_upload_path` 的 Markdown/普通文件双回调透传回归，验证 runner 创建后再 monkeypatch `_upload_markdown` / `_upload_file` 仍然生效。
- 测试：
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -k "upload_path_uses_latest_markdown_callback or upload_path_uses_latest_file_callback or upload_path_skips_md_when_mode_is_download_only or upload_file_updates_link_timestamp or upload_file_replaces_previous_cloud_file_and_cleans_same_name_duplicates" -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py tests/test_main.py -q`
  - 上述 pytest 在当前沙箱下需将 `TEMP/TMP` 指向仓库内 `.tmp-tests` 目录，否则 `tmp_path` fixture 会因系统临时目录写权限受限而失败。
- 问题：
  - `sync_runner.py` 已进一步降到 2707 行，但 `_upload_markdown` 仍承担冲突校验、块级状态和导入重建回退等复杂职责；下一轮应优先继续拆 Markdown 上传主链路，而不是继续在 runner 内堆叠分支。

## v0.7.17-dev.26 (2026-05-23)

- 目标：
  - 继续落实工作流 B，在 `apps/backend/src/services/transcoder.py` 中拆出块解析职责，把 `DocxParser`、块类型常量和相关 helper 从转码编排主类中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/docx_parser.py`，承载 `DocxParser`、块类型常量，以及提醒格式化、表格单元格文本规范化、编号列表索引解析等解析辅助逻辑。
  - `transcoder.py` 现在从 `docx_parser.py` 导入并继续兼容导出 `DocxParser` 与相关常量，外部调用面保持不变，但转码编排与块解析职责已经分层。
  - `transcoder.py` 文件规模已从 1270 行降到 956 行，为后续继续拆 `MediaDownloader` 或 sheet/table 渲染逻辑预留了更清晰的边界。
- 测试：
  - `python -m pytest tests/test_transcoder.py -k "sheet_block or internal_full_coverage_document" -q`
  - `python -m pytest tests/test_transcoder.py -q`
  - `python -m pytest tests/test_docx_service.py tests/test_transcoder.py tests/test_sync_runner.py -q`
- 问题：
  - 当前剩余最大模块仍是 `sync_runner.py`（2834 行）和 `docx_service.py`（1598 行）；下一轮应优先在 `sync_runner` 的单文件上传/下载细节与 `transcoder` 的 sheet/table 渲染逻辑之间择一继续拆分。

## v0.7.17-dev.25 (2026-05-23)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/sync_runner.py` 的下载主编排，把树扫描、候选筛选、写回循环和运行时服务组装从主 runner 中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/sync_download_orchestration_service.py`，承载下载阶段的运行时服务容器、树扫描、候选筛选、重复项跳过、文档/导出文件/普通文件写回，以及资源关闭逻辑。
  - `SyncTaskRunner` 现通过 `_resolve_download_runtime_services()` 组装下载运行时服务，并通过 `SyncDownloadOrchestrationService` 执行 `_run_download`，保留原方法作为兼容入口。
  - 新增 `_run_download` 目标回归，验证 runner 创建后再 monkeypatch `_download_docx` 仍然生效，确保下载编排服务按调用时读取 runner 当前回调。
- 测试：
  - `python -m pytest tests/test_sync_runner.py -k "run_download_uses_latest_download_docx_callback or download_additive_mode_does_not_enqueue_cloud_missing_delete or runner_downloads_docx_and_files or runner_download_only_never_creates_cloud_md_mirror_even_if_md_mode_is_enhanced or runner_prefers_persisted_link_when_cloud_has_duplicates or runner_skips_unchanged_when_persisted" -q`
  - `python -m pytest tests/test_sync_runner.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_sync_runner.py tests/test_main.py -q`
- 问题：
  - `sync_runner.py` 已从上一轮的 3079 行压到 2834 行，但仍保留单文件上传/下载细节、任务编排和部分本地/云端状态判断；下一轮应在 `sync_runner` 与 `transcoder` 之间择一继续拆分，优先看复杂度与回归收益。

## v0.7.17-dev.24 (2026-05-23)

- 目标：
  - 继续落实工作流 B，开始拆 `apps/backend/src/services/sync_runner.py` 的上传主编排，把全量上传、按路径上传和运行时服务组装从主 runner 中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/sync_upload_orchestration_service.py`，承载上传阶段的运行时服务容器、全量上传循环、按路径上传循环、失败归档和资源关闭逻辑。
  - `SyncTaskRunner` 现通过 `_resolve_upload_runtime_services()` 组装运行时服务，并通过 `SyncUploadOrchestrationService` 执行 `_run_upload` / `_run_upload_paths`，保留原方法作为兼容入口。
  - 新增 `_run_upload_paths` 目标回归，验证 runner 创建后再 monkeypatch `_upload_path` 仍然生效，且 `force_paths` 能正确透传到上传执行层。
- 测试：
  - `python -m pytest tests/test_sync_runner.py -k "run_upload_paths_uses_latest_upload_callback or handle_local_event_calls_upload_with_all_dependencies or run_task_performs_additive_reconcile_for_new_task or run_task_skips_additive_reconcile_when_recently_run" -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest tests/test_sync_runner.py -k "_run_download or runner_downloads_docx_and_files or download_only_never_creates_cloud_md_mirror_even_if_md_mode_is_enhanced or runner_prefers_persisted_link_when_cloud_has_duplicates or runner_skips_unchanged_when_persisted" -q`
- 问题：
  - `sync_runner.py` 仍保留下载主编排和单文件上传/下载细节；下一轮应继续优先拆下载主编排，把 `run_download` 的扫描、候选筛选和写回循环从主 runner 中分离。

## v0.7.17-dev.23 (2026-05-22)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/docx_service.py` 中的内容写入主编排，把文档替换、`convert -> create` 写入和 Markdown 块插入从文档服务主类中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/docx_content_write_service.py`，承载 `replace_document_content`、`create_from_convert` 与 `insert_markdown_block` 的写入编排。
  - `DocxService` 现通过组合 `DocxContentWriteService` 复用这部分能力，并保留 `replace_document_content`、`_create_from_convert`、`insert_markdown_block` 原方法作为兼容代理，现有文档替换与插入回归无需改写。
  - 新增 `insert_markdown_block` 目标测试，补齐块插入路径的自动化覆盖；`docx_service` 继续向“文档 API 能力集合 + 薄编排层”收口。
- 测试：
  - `python -m pytest tests/test_docx_service.py -k "insert_markdown_block_creates_children_at_index or replace_document_content_clears_and_creates or replace_document_content_creates_nested_children" -q`
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_docx_service.py tests/test_main.py -q`
- 问题：
  - `docx_service.py` 仍保留请求基类、转换入口和部分 block mutation；下一轮应优先考虑继续拆 `convert_markdown_with_images`/请求适配层，或切回 `sync_runner` 的 `run_download/run_upload` 主编排。

## v0.7.17-dev.22 (2026-05-22)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/docx_service.py` 中的子块创建主链路，把创建请求、失败拆分重试和图片/附件回填从文档服务主类中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/docx_block_create_service.py`，承载子块批次规划、创建请求、图片/附件回填、失败拆分重试与表格块创建失败后的降级分支。
  - `DocxService` 现通过组合 `DocxBlockCreateService` 复用这部分能力，并保留 `_create_children_recursive`、`_handle_create_children_error` 等原方法作为兼容代理，现有文档写回与上传回归无需改写。
  - `docx_service` 现已进一步拆出“Markdown 资源处理 / 表格运行时处理 / 局部更新 diff / 子块创建执行”四块服务边界，主类继续向“飞书文档 API 编排层”收口。
- 测试：
  - `python -m pytest tests/test_docx_service.py -k "build_create_chunks or replace_document_content_uploads_local_file_link_as_file_block or replace_document_content_falls_back_to_plain_text_when_table_create_invalid or replace_image_block_preserves_source_ratio" -q`
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_docx_service.py tests/test_main.py -q`
- 问题：
  - `docx_service.py` 仍集中着 `replace_document_content` 主流程、网络请求基类和部分转换编排；下一轮应优先继续拆内容替换主编排，或转去继续拆 `sync_runner` 的 `run_download/run_upload` 主编排。

## v0.7.17-dev.21 (2026-05-22)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/docx_service.py` 中的块级局部更新链路，把 diff、重复签名规避与锚点匹配从文档服务主类中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/docx_partial_update_service.py`，承载块级局部更新的签名计算、重复签名检测、唯一锚点匹配与 diff 应用流程。
  - `DocxService` 现通过组合 `DocxPartialUpdateService` 复用这部分能力，并保留 `_apply_partial_update` 原方法作为兼容代理，现有局部更新回归无需改写。
  - `docx_service` 现已进一步拆出“Markdown 资源处理 / 表格运行时处理 / 局部更新 diff 处理”三块服务边界，主类继续向“飞书文档 API 编排层”收口。
- 测试：
  - `python -m pytest tests/test_docx_service.py -k "partial_update or duplicate_signatures or table_children" -q`
  - `python -m pytest tests/test_docx_service.py -k "replace_document_content_clears_and_creates or replace_document_content_creates_nested_children or replace_document_content_populates_table_cells_without_creating_cells" -q`
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_docx_service.py tests/test_main.py -q`
- 问题：
  - `docx_service.py` 仍集中着块创建重试、部分网络请求编排和内容替换主流程；下一轮应优先继续拆 `replace_document_content` 主链路，或转去继续拆 `sync_runner` 的 `run_download/run_upload` 主编排。

## v0.7.17-dev.20 (2026-05-22)

- 目标：
  - 继续落实工作流 B，拆 `apps/backend/src/services/docx_service.py` 中的表格运行时逻辑，把大表格降级、单元格回填和插行补足从文档服务主类中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/docx_table_runtime_service.py`，承载大表格降级重建、表格单元格回填和插入缺失行后的单元格刷新。
  - `DocxService` 现通过组合 `DocxTableRuntimeService` 复用这部分能力，并保留 `_fallback_table_block_without_code`、`_populate_table_cells`、`_ensure_table_row_capacity` 等原方法作为兼容代理，现有表格回归无需改写。
  - `docx_service` 现已初步拆出“Markdown 资源处理”和“表格运行时处理”两块服务边界，主类进一步向“飞书文档 API 编排层”收口。
- 测试：
  - `python -m pytest tests/test_docx_service.py -k "populate_large_table or falls_back_to_plain_text_when_table_create_invalid or convert_markdown_patches_table_property or patch_table_properties or split_large_markdown_tables_for_convert or has_markdown_table_exceeding_create_limit or partial_update_table_children" -q`
  - `python -m pytest tests/test_docx_service.py -k "replace_document_content_populates_table_cells_without_creating_cells or sanitize_block_caps_large_table_rows_on_create" -q`
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_docx_service.py tests/test_main.py -q`
- 问题：
  - `docx_service.py` 仍然集中着块级局部更新 diff、块创建重试与网络请求编排；下一轮应优先拆局部更新链路，或转去继续拆 `sync_runner` 的 `run_download/run_upload` 主编排。

## v0.7.17-dev.19 (2026-05-22)

- 目标：
  - 继续落实工作流 B，开始拆 `apps/backend/src/services/docx_service.py` 中与 Markdown 资源占位/替换强相关的逻辑，把本地图片、HTML 图片和附件链接处理从文档服务主类中分离出去。
- 结果：
  - 新增 `apps/backend/src/services/docx_markdown_asset_service.py`，承载 Markdown 图片 placeholder 构建、HTML 图片解析、本地附件 placeholder 构建、资源路径解析与 placeholder 回填。
  - `DocxService` 现通过组合 `DocxMarkdownAssetService` 复用这部分能力，并保留 `_build_image_placeholders`、`_build_file_placeholders`、`_resolve_html_image_path`、`_resolve_markdown_image_path`、`_replace_placeholders_with_images`、`_resolve_image_path` 等原方法作为兼容代理，现有文档转换回归无需改写。
  - `docx_service` 的“文档 API 编排 / 表格策略 / Markdown 资源处理”边界开始分层，为后续继续拆表格处理和局部更新链路预留了更清晰的切口。
- 测试：
  - `python -m pytest tests/test_docx_service.py -k "build_image_placeholders or convert_markdown_with_images_falls_back_on_missing_image or replace_placeholders_with_files_attaches_to_list_children or replace_placeholders_keeps_list_text_and_appends_image or replace_document_content_uploads_local_images or replace_document_content_uploads_embedded_html_images or replace_document_content_uploads_local_file_link_as_file_block" -q`
  - `python -m pytest tests/test_docx_service.py -k "resolve_image_path_supports_file_url_and_encoded_relative_path or convert_markdown_patches_table_property" -q`
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_docx_service.py tests/test_main.py -q`
- 问题：
  - `docx_service.py` 仍集中着表格行扩容、表格降级重建、局部更新 diff 和块创建重试等复杂逻辑；下一轮应优先拆表格处理或局部更新链路，而不是继续在主类中堆叠分支。

## v0.7.17-dev.18 (2026-05-22)

- 目标：
  - 继续落实工作流 B，把 `sync_runner.py` 中与下载候选构建、导出任务和导出文件下载强相关的逻辑抽成独立服务，减少下载链路在主 runner 中的实现细节。
- 结果：
  - 新增 `apps/backend/src/services/sync_download_support_service.py`，承载下载候选构建、表格/多维表格 `sub_id` 补齐、候选去重/优选、Docx 下载转码、导出任务轮询与导出文件下载。
  - `SyncTaskRunner` 现通过组合 `SyncDownloadSupportService` 复用这部分能力，并保留 `_build_download_candidate`、`_hydrate_export_sub_ids`、`_select_download_candidates`、`_download_exported_file`、`_wait_for_export_task` 等原私有方法作为兼容代理，现有下载回归无需改写。
  - 下载链路的“候选规划 + 导出执行”边界已经开始从主同步 runner 中脱离，为后续继续抽 `run_download` 主编排与下载后状态落库逻辑预留了更清晰的服务边界。
- 测试：
  - `python -m pytest tests/test_sync_runner.py -k "runner_downloads_docx_and_files or export_poll or export_retries_with_sub_id or should_skip_download_for_unchanged or download_prefers_persisted_link" -q`
  - `python -m pytest tests/test_sync_runner.py -k "run_download_silences or run_download_enqueues_cloud_missing_delete or runner_download_only_never_creates_cloud_md_mirror_even_if_md_mode_is_enhanced" -q`
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest tests/test_sync_task_api.py tests/test_main.py -q`
- 问题：
  - `sync_runner.py` 虽已进一步降薄，但 `run_download` / `run_upload` 主编排与 `docx_service.py` 内的差量更新/表格/资源处理仍集中；下一轮应继续向“下载编排服务”或 `docx_service` 拆分推进。

## v0.7.17-dev.17 (2026-05-22)

- 目标：
  - 继续落实工作流 B，把 `sync_runner.py` 中与 Markdown 云端文档导入/重导入强相关的逻辑抽成独立服务，减少上传链路在主 runner 中的实现细节。
- 结果：
  - 新增 `apps/backend/src/services/sync_markdown_cloud_doc_service.py`，承载 Markdown 新建云端文档、复用同名文档、导入重建、导入源文件清理、同名旧文档清理与新建文档 `modified_time` 兜底等逻辑。
  - `SyncTaskRunner` 现通过组合 `SyncMarkdownCloudDocService` 复用这部分能力，并保留 `_create_cloud_doc_for_markdown`、`_reimport_cloud_doc_for_markdown`、`_import_markdown_doc`、`_cleanup_duplicate_docs_by_name`、`_cleanup_import_source_file` 等原私有方法作为兼容代理，现有上传回归无需改写。
  - `sync_runner` 的上传链路进一步从“主流程 + 细节实现”转向“主流程编排 + 专项服务”，为后续继续抽离下载候选/导出任务链路预留了更清晰的边界。
- 测试：
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest tests/test_sync_runner.py -k "parse_mtime or upload_markdown or upload_file_replaces_previous_cloud_file" -q`
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest tests/test_sync_task_api.py tests/test_main.py -q`
- 问题：
  - `sync_runner.py` 仍然集中着下载候选筛选、导出任务轮询和块级更新编排；下一轮应继续沿下载/导出链路抽服务，而不是在主 runner 里继续堆条件分支。

## v0.7.17-dev.16 (2026-05-22)

- 目标：
  - 继续落实工作流 B，把 `sync_runner.py` 中与删除墓碑、本地回收目录和删除映射清理强相关的逻辑抽成独立服务，减少主 runner 继续承担删除链路细节。
- 结果：
  - 新增 `apps/backend/src/services/sync_delete_sync_service.py`，承载删除策略解析、删除墓碑创建/执行、活动映射保护、本地回收目录移动、删除后映射/块状态清理，以及“云端已删除”错误的幂等判断。
  - `SyncTaskRunner` 现通过组合 `SyncDeleteSyncService` 复用这部分能力，并保留 `_enqueue_local_delete_tombstone`、`_process_pending_deletes`、`_move_to_local_trash`、`_cleanup_deleted_state` 等原私有方法作为兼容代理，现有测试和调用面无需改写。
  - 拆分过程中补回了 `sync_runner.py` 顶部缺失的 `datetime` 导入，修复 `_parse_mtime()` 解析 ISO8601 字符串时的兼容回归。
- 测试：
  - `python -m pytest tests/test_sync_runner.py -k "process_pending_deletes or move_to_local_trash or pending_tombstones" -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -k "cloud_mirror" -q`
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py -q`
- 问题：
  - `sync_runner.py` 仍有较大的上传/下载主流程分支，下一轮应继续沿“上传文档导入/重导入”或“下载候选/导出任务”方向抽专项服务，避免在主 runner 中继续累积条件分支。

## v0.7.17-dev.15 (2026-05-22)

- 目标：
  - 继续落实工作流 B，开始把 `sync_runner.py` 中与云端父目录解析、MD 镜像目录和目录缓存强相关的逻辑抽成独立服务，减少主 runner 继续承担目录编排细节。
- 结果：
  - 新增 `apps/backend/src/services/sync_cloud_folder_service.py`，承载云端父目录解析、目录链接持久化、MD 镜像目录查找/创建、目录缓存、目录遍历与导入后文档探测等逻辑。
  - `SyncTaskRunner` 现通过组合 `SyncCloudFolderService` 复用这部分能力，并保留 `_resolve_cloud_parent`、`_cleanup_md_mirror_copy`、`_find_existing_doc_by_name`、`_wait_for_imported_doc` 等原私有方法作为兼容代理，现有测试和调用面无需改写。
  - `apps/backend/src/services/sync_runner.py` 已从 4279 行压到 4111 行，虽然仍然很大，但“云端目录/镜像目录”这块边界已经独立，为后续继续抽下载/上传/删除链路打下基础。
- 测试：
  - `python -m pytest tests/test_sync_runner.py -k "resolve_cloud_parent or removes_md_mirror_copy or md_mirror" -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -k "cloud_mirror" -q`
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py -q`
- 问题：
  - `sync_runner.py` 仍是当前最大的技术债，下一轮应继续沿“删除墓碑处理”或“上传链路”抽服务，而不是回到主文件里追加新逻辑。

## v0.7.17-dev.14 (2026-05-22)

- 目标：
  - 继续落实工作流 B，优先拆分 `apps/backend/src/api/sync_tasks.py` 中已经自然聚集的任务诊断与同步日志接口，实现“共享对象保留、实现下沉”的第一轮后端 API 收口。
- 结果：
  - 新增 `apps/backend/src/api/sync_task_models.py`，把 `SyncTaskCreateRequest / SyncTaskUpdateRequest / MarkdownReplaceRequest` 以及任务状态、任务概览、任务诊断、同步日志等请求/响应模型从 `sync_tasks.py` 中独立出来。
  - 新增 `apps/backend/src/services/sync_task_diagnostics_service.py`，统一承载任务运行摘要构建、`sync_run_events`/JSONL 的 DB-first 回退读取、任务诊断拼装和同步日志响应组装。
  - `apps/backend/src/api/sync_tasks.py` 已从 1065 行压到 312 行，当前主要保留共享依赖对象、兼容导出、任务 CRUD/维护动作以及薄路由包装层；现有测试仍可继续通过 `sync_tasks` 模块级对象做 monkeypatch。
- 测试：
  - `python -m pytest tests/test_sync_task_api.py tests/test_tray_status.py tests/test_main.py -q`
- 问题：
  - `sync_tasks.py` 已明显降薄，但工作流 B 还没有完成；下一轮最该继续的是把任务维护动作再独立，或直接进入 `sync_runner.py` / `docx_service.py` 的主服务边界拆分。

## v0.7.17-dev.13 (2026-05-22)

- 目标：
  - 继续落实工作流 D，把 `TasksPage.tsx` 与 `NewTaskModal.tsx` 从大段内联渲染收口为“页面编排 + 独立卡片/步骤组件 + 纯逻辑 helper”的结构。
- 结果：
  - 新增 `apps/frontend/src/components/tasks/TasksPageHeader.tsx`、`TasksEmptyState.tsx`、`TaskCard.tsx`，任务页主文件现在只保留任务列表编排、局部状态与 mutation 接线；`TasksPage.tsx` 已从 517 行压到 191 行。
  - 新增 `apps/frontend/src/components/tasks/NewTaskWizardStepIndicator.tsx`、`NewTaskLocalStep.tsx`、`NewTaskCloudStep.tsx`、`NewTaskStrategyStep.tsx`，`NewTaskModal.tsx` 已从 535 行压到 269 行，主要只负责向导状态和创建提交。
  - 新增 `apps/frontend/src/lib/taskManagement.ts` 与 `newTaskWizard.ts`，把路径摘要、任务健康判断、删除宽限解析、手动云端目录解析和创建 payload 组装沉到可测试 helper。
  - 新增 `TaskPanels.test.tsx`、`NewTaskWizardPanels.test.tsx`、`taskManagement.test.ts`、`newTaskWizard.test.ts`，为任务页卡片和新建任务向导补上组件级 smoke 与纯逻辑测试。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/lib/taskManagement.test.ts src/lib/newTaskWizard.test.ts src/components/tasks/TaskPanels.test.tsx src/components/tasks/NewTaskWizardPanels.test.tsx src/pages/TasksPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 前端大页拆分已基本收口到日志中心、设置页、任务页三个主入口，但后续若要完全完成本轮规划，仍需要继续推进后端 `sync_runner.py` / `sync_tasks.py` 等大文件的服务边界拆分。

## v0.7.17-dev.12 (2026-05-22)

- 目标：
  - 继续落实工程化规划中的前端页面拆分，把 `SettingsPage.tsx` 中仍然集中的设置区块拆成独立面板组件，降低页面体积并补上面板级 smoke test。
- 结果：
  - 新增 `apps/frontend/src/components/settings/SettingsOAuthPanel.tsx`、`SettingsSyncStrategyPanel.tsx`、`SettingsMorePanel.tsx`、`SettingsGeneralPanel.tsx`、`SettingsUpdatePanel.tsx`、`SettingsIgnoredDirectoriesPanel.tsx`、`SettingsMaintenancePanel.tsx`，将设置页主要配置区从单文件内联 JSX 拆成独立组件。
  - `apps/frontend/src/pages/SettingsPage.tsx` 进一步收口为状态编排与事件接线层；同步策略、OAuth、高级设置、忽略目录和维护工具等区域都改为消费独立面板。
  - 新增 `apps/frontend/src/components/settings/SettingsPanels.test.tsx`，把设置页面板组合的关键渲染入口单独锁定，避免后续继续拆分时回归风险上升。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/components/settings/SettingsPanels.test.tsx src/pages/SettingsPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
- 问题：
  - `SettingsPage` 虽已显著收口，但仍持有较多跨面板状态与 mutation 接线；下一轮可继续评估是否把更新状态、忽略目录草稿和维护动作下沉为更细的 state hook。

## v0.7.17-dev.11 (2026-05-22)

- 目标：
  - 继续压缩日志中心主诊断 hook，把概览排序、`runAlert` 判断和展示派生状态从 `useLogCenterTaskDiagnostics.ts` 中拆出去，减少 hook 内的纯派生分支。
- 结果：
  - 新增 `apps/frontend/src/lib/taskDiagnosticsState.ts` 与 `taskDiagnosticsState.test.ts`，把任务概览按最近活动排序、`runAlert` 生成、`currentFile / diagnosticCounts / lastActivityAt / selectedStateKey` 等展示派生状态集中到可测试 helper。
  - `useLogCenterTaskDiagnostics.ts` 现通过 `deriveTaskDiagnosticsState()` 和 `sortTaskOverviewsByActivity()` 获取展示派生结果，不再直接维护多段 `??` 链和 `runAlert` 文案判断。
  - `TaskDiagnosticsOverviewTab.tsx` 与 `TaskDiagnosticsDetailPanel.tsx` 的 `RunAlertMeta` 类型也已改为直接复用 helper 导出的类型，减少重复定义。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/lib/taskDiagnosticsState.test.ts src/lib/taskDiagnosticsQuery.test.ts src/lib/taskDiagnosticsSelection.test.ts src/lib/taskEventTimeline.test.ts src/components/log-center/TaskDiagnosticsDetailTabs.test.tsx src/components/log-center/TaskDiagnosticsPanels.test.tsx src/pages/LogCenterPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 当前主诊断 hook 已明显变薄，但仍承担 overview query、diagnostics query 和多个子 hook 编排；下一轮可评估是否把 overview query 自身也抽成独立 resource hook，进一步统一“query hook + state hook + panel 组件”的边界。

## v0.7.17-dev.10 (2026-05-22)

- 目标：
  - 继续压缩日志中心主诊断 hook，把诊断 query 的 `include_problems` 判断、URL 参数组装和轮询间隔判断从 `useLogCenterTaskDiagnostics.ts` 中拆出去，避免 hook 内继续保留低层查询细节。
- 结果：
  - 新增 `apps/frontend/src/lib/taskDiagnosticsQuery.ts` 与 `taskDiagnosticsQuery.test.ts`，把诊断请求参数拼装、`include_problems` 判断和轮询间隔判断下沉到可测试 helper。
  - `useLogCenterTaskDiagnostics.ts` 现在通过 helper 驱动诊断 query key、API path 和 polling 间隔，不再在 hook 内直接拼 `URLSearchParams`。
  - 这轮没有改页面或组件对外接口，日志中心视图层和既有子 hook 接线保持不变。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/lib/taskDiagnosticsQuery.test.ts src/lib/taskDiagnosticsSelection.test.ts src/lib/taskEventTimeline.test.ts src/components/log-center/TaskDiagnosticsDetailTabs.test.tsx src/components/log-center/TaskDiagnosticsPanels.test.tsx src/pages/LogCenterPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 当前主诊断 hook 的剩余复杂度主要集中在概览排序、展示派生状态和 `runAlert` 判断；下一轮应评估是否继续把这些纯派生逻辑下沉到 helper，进一步让主 hook 更接近纯编排层。

## v0.7.17-dev.9 (2026-05-22)

- 目标：
  - 继续收口日志中心主诊断 hook，把任务选择、任务筛选和运行选择状态从 `useLogCenterTaskDiagnostics.ts` 中拆出去，避免主 hook 继续直接承担 selection 状态管理。
- 结果：
  - 新增 `apps/frontend/src/hooks/useTaskDiagnosticsSelection.ts`，统一管理任务选择、运行选择、任务选择器搜索与开合状态。
  - 新增 `apps/frontend/src/lib/taskDiagnosticsSelection.ts` 与 `taskDiagnosticsSelection.test.ts`，把默认任务选中、任务筛选和 active run 解析下沉到可测试 helper。
  - `useLogCenterTaskDiagnostics.ts` 现主要负责概览排序、诊断 query、事件时间线 hook 编排和派生展示状态；事件分页也补到 `selectedTaskId` 变更时自动重置，避免切任务后沿用旧页码。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/lib/taskDiagnosticsSelection.test.ts src/lib/taskEventTimeline.test.ts src/components/log-center/TaskDiagnosticsDetailTabs.test.tsx src/components/log-center/TaskDiagnosticsPanels.test.tsx src/pages/LogCenterPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 当前主诊断 hook 的主要剩余复杂度集中在诊断 query、概览排序和展示派生状态；下一轮应评估是否继续把诊断请求参数组装/轮询判断也下沉成 helper，进一步减少 hook 内的分支判断。

## v0.7.17-dev.8 (2026-05-22)

- 目标：
  - 继续收口日志中心主诊断 hook，把事件时间线相关的筛选状态、分页状态与时间线查询从 `useLogCenterTaskDiagnostics.ts` 中拆出去，避免主 hook 继续同时承担过多职责。
- 结果：
  - 新增 `apps/frontend/src/hooks/useTaskEventTimeline.ts`，统一管理事件筛选、搜索、分页、轮询和时间线 query；`useLogCenterTaskDiagnostics.ts` 现在只负责组合任务概览、运行选择、问题列表与该子 hook 的接线。
  - 新增 `apps/frontend/src/lib/taskEventTimeline.ts` 与 `taskEventTimeline.test.ts`，把时间线请求参数拼装和轮询判断下沉到可测试 helper，避免查询细节再次散落在 hook 内。
  - `TaskDiagnosticsDetailPanel` / `LogCenterPage` 的对外接线保持不变，页面层无需感知这次 hook 内部拆分。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/lib/taskEventTimeline.test.ts src/components/log-center/TaskDiagnosticsDetailTabs.test.tsx src/components/log-center/TaskDiagnosticsPanels.test.tsx src/pages/LogCenterPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 当前主 hook 已不再直接管理事件时间线 query，但任务选择、运行选择和诊断 query 仍在同一个 hook 中；下一轮应评估是否继续把任务选择/运行选择状态拆成更独立的 selection hook，进一步降低主 hook 的耦合面。

## v0.7.17-dev.7 (2026-05-22)

- 目标：
  - 继续压缩日志中心任务诊断详情组件，把 `overview / problems / events` 三个大分支从 `TaskDiagnosticsDetailPanel.tsx` 中独立出去，避免详情组件再次演化成新的大文件。
- 结果：
  - 新增 `apps/frontend/src/components/log-center/TaskDiagnosticsOverviewTab.tsx`、`TaskDiagnosticsProblemsTab.tsx`、`TaskDiagnosticsEventsTab.tsx`，分别承载概览、问题、事件三个展示分支。
  - 新增 `apps/frontend/src/components/log-center/TaskDiagnosticsDetailTabs.test.tsx`，单独锁定三类详情 tab 的关键渲染内容与分页壳层。
  - `TaskDiagnosticsDetailPanel.tsx` 已从约 326 行进一步收口到约 181 行，当前主要负责 header、tab 切换与数据接线，不再承载大段详情 JSX。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/components/log-center/TaskDiagnosticsDetailTabs.test.tsx src/components/log-center/TaskDiagnosticsPanels.test.tsx src/pages/LogCenterPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 详情区的纯展示已经拆开，但 `useLogCenterTaskDiagnostics.ts` 仍同时管理任务选择、运行选择、事件筛选、分页与多个 query；下一轮应考虑把事件筛选/分页状态从主 hook 中进一步分离，继续降低 hook 的职责密度。

## v0.7.17-dev.6 (2026-05-22)

- 目标：
  - 继续推进日志中心页面拆分，把“任务选择 / 运行记录 / 诊断详情”三大块从 `LogCenterPage.tsx` 中抽离，避免页面继续承担大段诊断视图 JSX。
- 结果：
  - 新增 `apps/frontend/src/components/log-center/TaskSelectionPanel.tsx`、`RunHistoryPanel.tsx`、`TaskDiagnosticsDetailPanel.tsx`，分别承载任务选择、运行列表与任务诊断详情工作台。
  - 新增 `apps/frontend/src/components/log-center/TaskDiagnosticsPanels.test.tsx`，用静态渲染 smoke test 锁定拆分后关键壳层文案与详情概览结构。
  - `LogCenterPage.tsx` 已从约 800 行进一步收口到约 250 行，当前主要负责 query/hook 接线、页签切换和 panel 装配，不再直接承载大段任务诊断 JSX。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/components/log-center/TaskDiagnosticsPanels.test.tsx src/pages/LogCenterPage.test.tsx`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 任务诊断详情组件虽然已经脱离页面，但 `TaskDiagnosticsDetailPanel.tsx` 内部仍有多段概览/问题/事件视图分支；下一轮应继续把 detail tabs 按 `Overview / Problems / Events` 再拆成更细的纯展示组件，进一步降低单组件复杂度。

## v0.7.17-dev.5 (2026-05-22)

- 目标：
  - 把日志中心页面里剩余的冲突处理队列状态机从组合层抽走，避免页面继续直接维护 queue ref、处理中标记、活动 ID 和重试逻辑。
- 结果：
  - 新增 `apps/frontend/src/hooks/useConflictResolutionQueue.ts`，统一管理冲突处理队列、串行提交、任务忙时自动重试、成功/失败状态写回与 toast 提示。
  - 新增 `apps/frontend/src/lib/conflictResolution.ts`，沉淀 `isTaskBusyConflictError()`、状态统计汇总、状态文案/色调判断以及冲突动作文案常量；`ConflictManagementPanel` 改为直接消费这些 helper，而不是在组件内部重复判断。
  - 新增 `apps/frontend/src/lib/conflictResolution.test.ts`，独立锁定冲突忙闲重试识别、状态统计汇总和状态文案映射，保证后续继续拆冲突管理时能维持行为不漂移。
  - `LogCenterPage.tsx` 不再直接维护冲突队列 ref 或多段状态统计 memo，日志中心组合层进一步变薄。
- 测试：
  - `npm --prefix apps/frontend exec vitest run src/lib/conflictResolution.test.ts src/pages/LogCenterPage.test.tsx src/lib/logCenter.test.ts`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 当前日志中心剩余的大头主要是“任务诊断详情工作台”本身的 JSX 与交互分支；下一轮应优先继续拆任务诊断视图组件，而不是再在系统日志或冲突管理上做边际收益较小的整理。

## v0.7.17-dev.4 (2026-05-22)

- 目标：
  - 继续推进第二阶段前端结构拆分，把日志中心从“页面内同时管理查询、派生状态和多块大 JSX”推进到“组合层 + hook + 分区视图”的结构。
- 结果：
  - 新增 `apps/frontend/src/hooks/useLogCenterTaskDiagnostics.ts`，将任务诊断 Tab 的任务选择、运行选择、事件筛选、分页、三组查询以及派生状态统一收口到独立 hook。
  - 新增 `apps/frontend/src/components/log-center/SystemLogPanel.tsx` 与 `apps/frontend/src/components/log-center/ConflictManagementPanel.tsx`，分别承载系统日志和冲突管理的视图层，`LogCenterPage.tsx` 进一步退化为组合与编排层。
  - 现有 `apps/frontend/src/lib/logCenter.ts` 继续承接纯 helper，页面结构现在已经形成“lib helper -> hook 状态/查询 -> panel 视图 -> page 组合层”的清晰分层，为下一轮继续拆任务诊断详情区和冲突处理队列 hook 打下边界。
- 测试：
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend exec vitest run src/pages/LogCenterPage.test.tsx src/lib/logCenter.test.ts`
  - `npm --prefix apps/frontend run build`
- 问题：
  - 当前任务诊断视图本身的 JSX 仍然较大，且冲突处理队列状态机还留在页面组合层；下一轮应继续把任务诊断主视图和冲突处理状态机各自再抽一层，而不是停在“只把系统日志/冲突视图分出去”。

## v0.7.17-dev.3 (2026-05-22)

- 目标：
  - 按第三阶段规划把数据库结构演进从“启动时散落补列/补索引”升级为显式、可追踪的 schema version 迁移流程，并补齐老库升级测试。
- 结果：
  - `apps/backend/src/db/session.py` 新增 `SchemaMigration` 注册表、`CURRENT_SCHEMA_VERSION`、`sync_meta.schema_version` 读写逻辑和顺序迁移执行流程；`init_db()` 在 `create_all()` 后不再直接调用单个 `_ensure_schema()`，而是执行显式迁移列表。
  - 现有历史 `_ensure_column` / `_ensure_index` 补齐逻辑已收拢到第一个基线迁移 `v1`，作为当前 schema 的显式升级步骤，后续新增列/索引可以继续按版本追加，不再无限堆回 `init_db()` 主体。
  - 新增 `test_init_db_records_schema_version()` 与 `test_init_db_upgrades_legacy_schema_with_versioned_migrations()`，验证新库会写入 schema version，且旧库在缺少列/索引时能够通过迁移注册表自动升级到当前版本。
- 测试：
  - `python -m pytest tests/test_db_session.py -q`（工作目录：`apps/backend/`）
  - 后续完整回归会继续覆盖所有依赖 `init_db()` 的数据库服务测试
- 问题：
  - 当前只建立了 schema version 机制和 `v1` 基线迁移，尚未把所有历史结构变化拆成更细粒度的多版本迁移；下一步应在新增 schema 变更时严格通过新 migration 条目落地，而不是再回到散落 `_ensure_*` 的路径。

## v0.7.17-dev.2 (2026-05-22)

- 目标：
  - 按第二阶段规划做第一轮低风险结构拆分，优先把 `sync_runner` 中独立的事件状态流水线抽离出来，同时收口日志中心页面中的纯映射和格式化逻辑，为后续继续拆大文件降低耦合面。
- 结果：
  - 新增 `apps/backend/src/services/sync_runner_state.py`，将 `SyncFileEvent`、`SyncTaskStatus` 和状态日志窗口逻辑从 `sync_runner.py` 中独立出来，后续相关测试和其他模块不再必须依赖整个 runner 文件。
  - 新增 `apps/backend/src/services/sync_event_pipeline.py`，负责同步事件的状态计数、`SyncEventStore` 追加、SQLite 运行事件批量落库和异步 flush；`SyncTaskRunner` 现在通过该服务组合事件流水线，而不再自己持有 pending queue / flush task / flush lock 这些内部细节。
  - 新增 `apps/backend/tests/test_sync_event_pipeline.py`，单独锁定事件状态计数、任务名解析和批量落库 flush 行为，避免后续继续拆 `sync_runner` 时回归只能靠全量 runner 测试兜底。
  - 新增 `apps/frontend/src/lib/logCenter.ts`，把日志中心页面里的 snake_case -> camelCase 映射、最近活动时间选择、路径压缩、运行耗时格式化和 run_id 短码化等纯逻辑集中到独立 helper。
  - 新增 `apps/frontend/src/lib/logCenter.test.ts`，与既有 `LogCenterPage.test.tsx` 一起为日志中心后续继续拆 hook / view / state 分层提供稳定回归基线。
- 测试：
  - `python -m pytest tests/test_sync_event_pipeline.py tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py tests/test_conflict_resolution_runner.py -q`（工作目录：`apps/backend/`）
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend exec vitest run src/lib/logCenter.test.ts src/pages/LogCenterPage.test.tsx`
- 问题：
  - 当前这轮只先拆了“纯状态/纯 helper”边界，`sync_runner` 的上传/下载/删除主流程以及 `LogCenterPage` 的查询状态仍在原文件中；下一轮应继续向“组合服务 + hook/state/view 分层”推进，而不是重新把新 helper 逻辑回流进页面或 runner 主文件。

## v0.7.17-dev.1 (2026-05-22)

- 目标：
  - 按 `engineering_hardening_plan_v0.7.17-dev.1` 的第一阶段落地工程化收口，先解决构建基线漂移、FastAPI 生命周期弃用、前端质量门薄弱，以及自动更新缺少更接近真实用户链路的 smoke 验证这四类问题。
- 结果：
  - `scripts/build_installer.py` 现在会固定校验发布构建基线为 `Python 3.14.x` 与 `Node 25.x`，启动时打印 Python/Node/平台环境摘要；若处于非基线环境会直接 fail fast，只允许通过显式环境变量临时放行。
  - `apps/backend/src/main.py` 重构为 `create_app()` + `lifespan` 模式，统一收口数据库初始化、watcher、同步调度、更新调度和日志维护后台服务的启动/关闭顺序，并补充生命周期回归测试。
  - 前端补齐 `eslint` 配置、`vitest` smoke 用例与页面壳层回归，覆盖 App、任务页、日志中心和设置页；为避免 Windows 上 `jsdom` + 大页面测试导致 Node 堆内存暴涨，smoke 用例最终改为 `renderToStaticMarkup` 的轻量字符串渲染，稳定保留挂载回归而不再依赖浏览器 DOM 环境。
  - 新增 `scripts/update_install_smoke.py`，可在 Windows 上用真实 PowerShell bootstrap/worker 脚本和 handoff 文件验证静默安装链路是否能推进到目标阶段；脚本同时修复了仓库根目录运行时的导入路径、自定义 handoff 等待路径，以及 GBK 控制台输出 UTF-8 结果失败的问题。
  - GitHub Actions `Release Build` 的 quality job 现补齐前端 `lint/test/build` 和 Windows 静默安装 smoke，使这类“脚本存在但流程未验证”的工程缝隙进入 CI 质量门。
- 测试：
  - `python -m pytest tests/test_main.py tests/test_build_installer.py tests/test_update_install_smoke.py tests/test_system_update_api.py tests/test_tray_update_install.py tests/test_tray_status.py -q`（工作目录：`apps/backend/`）
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test`
  - `npm --prefix apps/frontend run build`
  - `python scripts/update_install_smoke.py`
- 问题：
  - 当前发布构建基线固定在本机与 CI 都已验证过的 `Python 3.14.x / Node 25.x`；如果后续团队决定回退到 LTS 运行时，需要把这一轮基线约束、CI 版本和打包脚本一并调整，而不是只改单处版本号。

## v0.7.13 release (2026-05-16)

- 目标：
  - 发布 `v0.7.13` 稳定版，收口 Markdown 上行表格列宽过宽的两轮修正。
- 结果：
  - 稳定版包含 `v0.7.13-dev.1` 和 `v0.7.13-dev.2`：表格列宽策略从页面级 `1080` 逐步收紧到 `732`，贴近飞书原生云文档默认表格宽度。
  - 继续保留短列最小宽度和长文本列内容权重分配，避免回退到早期按 `列数 * 180` 导致的过早换行。
  - 表格渲染修复标记升级到 `#md-table-render-v10`，已有 `#md-table-render-v9` 或更早标记的历史 Markdown 大表文档会在下一次普通同步时同 token 全量重建一次。
- 测试：
  - 沿用 `v0.7.13-dev.1` 与 `v0.7.13-dev.2` 的后端表格回归测试、后端全量 pytest、前端构建、editable 安装校验和 NSIS 安装包构建验证。

## v0.7.13-dev.2 (2026-05-16)

- 目标：
  - 按飞书原生云文档默认表格宽度信号，将 Markdown 上行生成的常见多列表格从 960 进一步收紧到 732，减少表格宽于正文内容的问题。
- 结果：
  - 表格列宽偏好总宽从 `960` 调整为 `732`，继续保留短列最小宽度和长文本列内容权重分配。
  - V1.5 修订说明示例表格的估算列宽从 `[120, 241, 250, 154, 195]` 收紧到 `[120, 180, 174, 122, 136]`，总宽从 `960` 降为 `732`。
  - 表格渲染修复标记升级为 `#md-table-render-v10`，已有 `#md-table-render-v9` 的历史文档下一次普通同步会在原 doc token 内全量重建一次。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py::test_convert_markdown_patches_table_property apps/backend/tests/test_docx_service.py::test_patch_table_properties_overrides_narrow_convert_width apps/backend/tests/test_docx_service.py::test_patch_table_properties_caps_long_table_width_to_enable_wrapping apps/backend/tests/test_docx_service.py::test_patch_table_properties_expands_common_tables_to_preferred_width apps/backend/tests/test_docx_service.py::test_patch_table_properties_keeps_multicolumn_tables_compact apps/backend/tests/test_docx_service.py::test_replace_document_content_populates_table_cells_without_creating_cells apps/backend/tests/test_sync_runner_upload_new_doc.py::test_upload_new_markdown_with_large_table_runs_block_replace_after_import apps/backend/tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_repairs_previous_table_marker_large_table_link_once -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest`（在 `apps/backend` 目录执行，428 passed）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`，生成 `dist/LarkSync-Setup-v0.7.13-dev.2.exe`

## v0.7.13-dev.1 (2026-05-16)

- 目标：
  - 收紧 v0.7.12 Markdown 上行生成的飞书表格总宽，解决常见多列表格内容不需要整页宽度但表格仍被撑得过宽的问题。
- 结果：
  - 表格列宽目标从固定页面级 `1080` 调整为常见多列表格 `960` 偏好总宽，继续按内容权重分配列宽，并保留每列最小宽度兜底。
  - V1.5 修订说明示例表格的估算列宽从 `[120, 281, 294, 165, 220]` 收紧到 `[120, 241, 250, 154, 195]`，总宽从 `1080` 降为 `960`。
  - 表格渲染修复标记升级为 `#md-table-render-v9`，已有 `#md-table-render-v8` 的历史文档下一次普通同步会在原 doc token 内全量重建一次。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py::test_patch_table_properties_overrides_narrow_convert_width apps/backend/tests/test_docx_service.py::test_patch_table_properties_caps_long_table_width_to_enable_wrapping apps/backend/tests/test_docx_service.py::test_patch_table_properties_expands_common_tables_to_preferred_width apps/backend/tests/test_docx_service.py::test_patch_table_properties_keeps_multicolumn_tables_compact apps/backend/tests/test_docx_service.py::test_replace_document_content_populates_table_cells_without_creating_cells apps/backend/tests/test_sync_runner_upload_new_doc.py::test_upload_new_markdown_with_large_table_runs_block_replace_after_import apps/backend/tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_repairs_previous_table_marker_large_table_link_once -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest`（在 `apps/backend` 目录执行，428 passed）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`，生成 `dist/LarkSync-Setup-v0.7.13-dev.1.exe`

## v0.7.12 release (2026-05-16)

- 目标：
  - 发布 `v0.7.12` 稳定版，收口 v0.7.11 下载成功后静默安装 handoff 因 UTF-8 BOM 读取失败而超时的问题。
- 结果：
  - 稳定版包含 `v0.7.12-dev.1`：Python 侧兼容 BOM 读取，PowerShell helper 后续写出无 BOM handoff JSON。
  - 注意：已安装的旧版本仍使用旧的静默安装代码，升级到本版本需要手动运行一次安装包；安装到 `v0.7.12` 后，后续静默更新才会使用本次修复。
- 测试：
  - `python -m pytest`（在 `apps/backend` 目录执行，427 passed）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`
  - 本地安装包：`dist/LarkSync-Setup-v0.7.12.exe`，sha256=`DEFA7DBC1BD0F32B16E4A64D09696B552217E11F3A2ACB7DAB49947E1219E2EC`

## v0.7.12-dev.1 (2026-05-16)

- 目标：
  - 修复 v0.7.11 下载成功后静默安装没有生效的问题，现场表现为 handoff 停在 `helper_started`，托盘随后报“静默安装接管超时”。
- 结果：
  - `_read_install_handoff()` 改为 `utf-8-sig` 读取，兼容 PowerShell 5.1 `Set-Content -Encoding UTF8` 写出的 BOM JSON。
  - `install-request.json` 读取同步兼容 UTF-8 BOM，避免同类编码问题影响安装请求消费。
  - bootstrap/worker PowerShell 脚本的 `Write-Handoff` 改为 `[System.IO.File]::WriteAllText(..., [System.Text.UTF8Encoding]::new($false))`，后续新版本会写出无 BOM JSON。
  - 已用现场 `install-handoff.json` 复核：文件头为 `EF BB BF`，Python `utf-8` 读取会触发 `Unexpected UTF-8 BOM`，`utf-8-sig` 可正常解析。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_tray_update_install.py::test_read_install_handoff_accepts_utf8_bom apps/backend/tests/test_tray_update_install.py::test_windows_handoff_scripts_write_json_without_bom -q`

## v0.7.11 release (2026-05-15)

- 目标：
  - 发布 `v0.7.11` 稳定版，收口 v0.7.10 自动更新检查在 GitHub Release API 匿名限流时失败的问题。
- 结果：
  - 稳定版包含 `v0.7.11-dev.1`：GitHub API 返回 403/429 时回退公开 Release 跳转页解析最新 tag，并生成平台安装包与 `.sha256` 下载地址。
  - 该修复不改变安装包下载与 sha256 校验链路，只修复“获取 Release 元数据”被 API 限流时的入口失败。
- 测试：
  - `python -m pytest`（在 `apps/backend` 目录执行，425 passed）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`
  - 本地安装包：`dist/LarkSync-Setup-v0.7.11.exe`，sha256=`FE0A3F41DBDBB52098C25C4E2DC5222EBD0CD8DB8F411559AAA0671CC0E0819E`

## v0.7.11-dev.1 (2026-05-15)

- 目标：
  - 修复 v0.7.10 自动更新检查在 GitHub Release API 匿名限流时直接失败的问题，错误表现为“获取 Release 失败: HTTP 403”。
- 结果：
  - `_fetch_latest_release()` 在 GitHub API 返回 403/429 时，会回退访问公开 `https://github.com/gooderno1/LarkSync/releases/latest`，通过跳转目标解析最新 tag。
  - 回退路径会按平台生成 `LarkSync-Setup-vX.Y.Z.exe` 或 `LarkSync-vX.Y.Z.dmg` 下载地址，并附带对应 `.sha256` 地址，后续下载和校验继续走既有链路。
  - 本地复现确认：当前匿名 GitHub API 已返回 403，但公开 Release 跳转可解析到 `v0.7.10`，安装包与 `.sha256` 资产可访问。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_update_service.py::test_fetch_latest_release_falls_back_to_public_redirect_on_api_403 -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_update_service.py -q`
  - 手工调用 `UpdateService()._fetch_latest_release()`，确认 403 环境下回退返回 `v0.7.10` 及 Windows 安装包、`.sha256` 下载地址。

## v0.7.10 release (2026-05-15)

- 目标：
  - 发布 `v0.7.10` 稳定版，收口 v0.7.9 表格列宽过度收紧导致 V1.5 飞书文档提前换行的问题。
- 结果：
  - 稳定版包含 `v0.7.10-dev.1`：Markdown 表格列宽估算改为页面级总宽目标，避免 2/3/4/5 列表格按 `列数 * 180` 被压窄。
  - 短列保留最小宽度，长文本列按内容权重分配剩余空间；超过页面目标时继续压回受控总宽，避免横向滚动回归。
  - 表格渲染修复标记升级为 `#md-table-render-v8`，已有 `#md-table-render-v7` 的历史文档下一次普通同步会在原 doc token 内全量重建一次。
- 测试：
  - 沿用 `v0.7.10-dev.1` 的表格列宽回归测试、后端全量 pytest、前端构建、editable 安装校验和 NSIS 安装包构建验证。

## v0.7.10-dev.1 (2026-05-15)

- 目标：
  - 修复 v0.7.9 生成的 V1.5 飞书文档中表格还没占满页面就提前换行的问题。
- 结果：
  - Markdown 表格列宽估算不再使用 `列数 * 180` 作为目标总宽，改为多列表格使用页面级总宽目标。
  - 列宽扩展时按内容估算权重分配剩余空间，短列保留最小宽度，长文本列获得更多宽度；超过页面目标时继续压回受控总宽，避免横向滚动回归。
  - 表格渲染修复标记升级为 `#md-table-render-v8`，已有 `#md-table-render-v7` 的历史文档下一次普通同步会在原 doc token 内全量重建一次。
  - 使用 V1.5 本地源文件验证 118 张 Markdown 表格，2/3/4/5/6 列表格均生成 `1080` 总列宽。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py::test_convert_markdown_patches_table_property apps/backend/tests/test_docx_service.py::test_patch_table_properties_overrides_narrow_convert_width apps/backend/tests/test_docx_service.py::test_patch_table_properties_caps_long_table_width_to_enable_wrapping apps/backend/tests/test_docx_service.py::test_patch_table_properties_expands_common_tables_to_page_width apps/backend/tests/test_docx_service.py::test_replace_document_content_populates_table_cells_without_creating_cells apps/backend/tests/test_sync_runner_upload_new_doc.py::test_upload_new_markdown_with_large_table_runs_block_replace_after_import apps/backend/tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_repairs_previous_table_marker_large_table_link_once -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest`（在 `apps/backend` 目录执行，424 passed）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`

## v0.7.9 release (2026-05-15)

- 目标：
  - 发布 `v0.7.9` 稳定版，收口 v0.7.8 已下载安装包无法静默安装的问题。
- 结果：
  - 稳定版包含 `v0.7.9-dev.1`：Windows 静默安装 bootstrap/worker 改为落地 `.ps1` 并用 PowerShell `-File` 启动，避免嵌套 `-EncodedCommand` 过长触发 `WinError 206`。
  - 更新检查会复用已校验且版本、文件名、大小和 sha256 匹配的安装包路径，避免下载完成后 UI/CLI 状态回退为未下载。
- 测试：
  - 沿用 `v0.7.9-dev.1` 的自动更新回归测试、后端全量 pytest、editable 安装校验和 NSIS 安装包构建验证。

## v0.7.9-dev.1 (2026-05-15)

- 目标：
  - 修复 v0.7.8 安装包下载完成后，Windows 静默安装未启动并在日志中报 `WinError 206 文件名或扩展名太长` 的问题。
  - 修复更新检查覆盖 `download_path`，导致已校验安装包在状态中又显示为未下载的问题。
- 结果：
  - Windows 静默安装 bootstrap/worker 改为落地 `.ps1` 脚本，并用 PowerShell `-File` 启动，避免把完整 worker 脚本嵌入嵌套 `-EncodedCommand` 造成命令行过长。
  - 更新检查会复用已缓存且版本、文件名、大小和 sha256 匹配的安装包路径，保持 UI/CLI 对“已下载可安装”的状态判断稳定。
  - 补充自动更新回归测试，覆盖短命令启动与已校验下载包路径保留。
- 测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_tray_update_install.py apps/backend/tests/test_update_service.py -p pytest_asyncio.plugin -q`

## v0.7.8 release (2026-05-15)

- 目标：
  - 发布 `v0.7.8` 稳定版，收口文件夹删除同步和 V1.5 软件设计说明书表格上行列宽过宽导致横向滚动的问题。
- 结果：
  - 稳定版包含 `v0.7.8-dev.1`：文件夹作为同步对象持久化映射，本地/云端文件夹删除进入删除联动链路，并递归清理子映射。
  - 稳定版包含 `v0.7.8-dev.2`：Markdown 表格列宽估算增加整表总宽上限，V1.5 长文本多列表格不再被撑到横向滚动，已有 `#md-table-render-v6` 文档下一次同步会同 token 重建一次。
- 测试：
  - `python -m pytest`（在 `apps/backend` 目录执行）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`

## v0.7.8-dev.2 (2026-05-15)

- 目标：
  - 修复 v0.7.7 表格列宽修复过度放大长文本列，导致飞书表格横向滚动、单元格看起来不自动换行的问题。
- 结果：
  - Markdown 表格列宽估算增加整表总宽上限；当长文本把多列撑宽时，会在保留每列最小宽度和内容权重的前提下压缩回页面级宽度。
  - V1.5 这类 5 列长文本表不再出现 1900+ 的总列宽，长列会在受控宽度内自动换行。
  - 表格渲染修复标记升级为 `#md-table-render-v7`，已有 `#md-table-render-v6` 的历史文档下一次普通同步会在原 doc token 内全量重建一次。
- 测试：
  - `python -m pytest tests/test_docx_service.py::test_patch_table_properties_overrides_narrow_convert_width tests/test_docx_service.py::test_patch_table_properties_caps_long_table_width_to_enable_wrapping tests/test_sync_runner_upload_new_doc.py::test_upload_new_markdown_with_large_table_runs_block_replace_after_import tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_repairs_previous_table_marker_large_table_link_once`
  - `python -m pytest tests/test_docx_service.py tests/test_sync_runner_upload_new_doc.py`
  - `python -m pytest`（在 `apps/backend` 目录执行，422 passed）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`

## v0.7.8-dev.1 (2026-05-15)

- 目标：
  - 修复删除同步只覆盖文件、不覆盖文件夹的问题，让已同步文件夹的本地删除和云端删除都能进入删除联动链路。
- 结果：
  - Watcher 不再丢弃目录事件，并在事件中保留 `is_directory` 标记；非删除的目录事件不会进入文件上传队列。
  - 云端扫描会为文件夹创建本地目录并持久化 `cloud_type=folder` 的同步映射，上传链路按需创建父文件夹时也会持久化 folder 映射。
  - 本地删除已同步文件夹会生成 folder 删除墓碑，执行时调用飞书 Drive 删除对应文件夹，并递归清理该文件夹及子文件的同步映射。
  - 云端文件夹缺失时只生成一条文件夹墓碑，不再把同一目录下的子文档拆成多条删除；本地侧仍按当前删除策略移动到回收目录或直接删除。
  - 同步根目录不存在时跳过本地缺失删除判定，避免本地根目录异常丢失时误删整棵云端目录。
- 测试：
  - `python -m pytest tests/test_watcher.py tests/test_sync_runner.py`（在 `apps/backend` 目录执行）
  - `python -m pytest`（在 `apps/backend` 目录执行，421 passed）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`

## v0.7.7 release (2026-05-15)

- 目标：
  - 发布 `v0.7.7` 稳定版，收口 V1.5 软件设计说明书表格上行仍存在的空行、视觉下沉、列宽过窄和长表被拆分问题。
- 结果：
  - 稳定版包含 `v0.7.7-dev.1`：Markdown 表格上行不再在转换前拆分超限表格，而是在创建同一张飞书表格后用表格行插入补齐剩余行。
  - 表格单元格写入改为先把真实内容插入默认空段落之前，再删除被后移的占位段落，避免文字被空段落顶到下方。
  - 列宽修复按文档顺序匹配 Markdown 表格规格，覆盖飞书转换器返回的窄默认列宽。
  - 表格渲染修复标记升级为 `#md-table-render-v6`，已有 `#md-table-render-v5` 的历史文档下一次普通同步会在原 doc token 内全量重建一次。
- 测试：
  - `python -m pytest -q`（在 `apps/backend` 目录执行）
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `python scripts/build_installer.py --nsis`
  - 使用当前 V1.5 本地文件调用真实 `blocks/convert` 干跑：Markdown 118 张表，转换后按文档顺序仍为 118 张表，窄宽度表为 0。
  - 使用 V1.5 中 16 行 2 列真实大表创建飞书临时文档：上传后读取为 1 张原生表格、`row_size=16`、`cells=32`、每个单元格 1 个子块、前置空段落 0，验证后已删除临时文档。

## v0.7.7-dev.1 (2026-05-15)

- 目标：
  - 修复 V1.5 软件设计说明书上传后仍有表格单元格空行、表格过窄，以及长表被拆成多张飞书表格的问题。
- 结果：
  - Markdown 上行不再在 `blocks/convert` 前拆分超限表格，V1.5 干跑转换从 159 张拆分表恢复为 118 张源表。
  - 创建飞书表格时只把初始 `row_size` 限制在飞书建表上限内，随后通过 `insert_table_row` 在同一张表内补齐剩余行，避免长表被拆成多张表。
  - 单元格内容改为插入到默认空段落之前，并在写入后删除被后移的默认空段落；真实云端临时文档验证 V1.5 中 16 行表为 1 张表、32 个单元格、每个单元格 1 个子段落、前置空段落 0。
  - 列宽修复改为按 `first_level_block_ids` 文档顺序匹配 Markdown 表格规格，覆盖飞书转换器返回的等宽窄列；V1.5 第一张表干跑列宽为 `[120, 600, 600, 244, 398]`。
  - 表格渲染修复标记升级为 `#md-table-render-v6`，使已带 `#md-table-render-v5` 的历史文档下一次同步仍会在原 doc token 内全量重建一次。
- 测试：
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py::test_upload_new_markdown_with_large_table_runs_block_replace_after_import tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_forces_full_replace_for_existing_large_table_doc tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_repairs_previous_table_marker_large_table_link_once -q`
  - `python -m pytest -q`（在 `apps/backend` 目录执行）
  - 使用当前 V1.5 本地文件调用真实 `blocks/convert` 干跑：Markdown 118 张表，转换后按文档顺序仍为 118 张表，第一张表保持 5 列且补齐可读列宽，窄宽度表为 0。
  - 真实云端临时文档验证 V1.5 中 16 行 2 列大表：上传后读取为 1 张飞书原生表格、`row_size=16`、`cells=32`、每个单元格 1 个子块、前置空段落 0，验证后已删除临时文档。

## v0.7.6 release (2026-05-15)

- 目标：
  - 发布 `v0.7.6` 稳定版，修复 `v0.7.5` 自动更新安装后可能未自动拉起新版本、且日志把空退出码误判为安装失败的问题。
- 结果：
  - 稳定版包含 `v0.7.6-dev.1`：Windows 静默更新 helper 会解析安装包目标版本，安装器退出后复核安装目录中的实际版本；当退出码为空但目标版本已安装时按成功处理。
  - 安装后重启改为最多 3 轮启动确认与重试，连续两轮确认新进程仍在运行或单实例锁端口已恢复后才视为启动成功，并通过 `restart_succeeded` / `restart_failed` handoff 和安装日志暴露结果。
  - 日志补充 expected/installed、空退出码、非零退出码但版本已安装、重启 attempt、进程过早退出等细节，便于后续判断是安装失败还是启动阶段失败。
- 测试：
  - `python -m pytest -q`（在 `apps/backend` 目录执行）
  - `python -m pytest apps/backend/tests/test_tray_update_install.py -q`
  - `python -m pip install --dry-run -e apps/backend`
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python scripts/build_installer.py --nsis`
  - `python scripts/release_notes.py --version v0.7.6 --asset "dist/LarkSync-Setup-v0.7.6.exe" --output "dist/release-notes-v0.7.6.md"`
  - 生成的 Windows helper PowerShell 脚本通过 `[scriptblock]::Create(...)` 语法解析

## v0.7.6-dev.1 (2026-05-15)

- 目标：
  - 针对本轮现场日志：安装器退出码为空、应用实际已安装到新版本但没有自动启动，补齐 helper 对安装结果与重启动作的可验证判断。
- 结果：
  - `_build_windows_installer_worker_script` 从安装包文件名解析 expected version，并在安装器退出后读取安装目录 `_internal/apps/backend/pyproject.toml` 或开发布局 `apps/backend/pyproject.toml` 复核 installed version。
  - 安装器退出码为空时不再直接进入失败分支；只有版本复核也失败时才判定安装失败并尝试恢复启动。
  - 重启 LarkSync 改为 `Start-RestartTarget`，最多 3 次启动，连续探测确认新进程/单实例锁，记录每次 attempt、PID、进程是否过早退出，并在启动确认失败时写出 `restart_failed`。
  - 新增托盘更新安装测试，锁定版本复核、空退出码处理和重启重试脚本片段。
- 测试：
  - `python -m pytest apps/backend/tests/test_tray_update_install.py -q`
  - 生成的 Windows helper PowerShell 脚本通过 `[scriptblock]::Create(...)` 语法解析

## v0.7.5 release (2026-05-15)

- 目标：
  - 发布 `v0.7.5` 稳定版，修复 Markdown 表格上传到飞书后单元格真实内容被默认空段落顶到下方的问题。
- 结果：
  - 稳定版包含 `v0.7.5-dev.1`：表格单元格填充前会先删除飞书新建 cell 自动生成的默认空段落，再写入 Markdown 转换后的真实内容。
  - 表格渲染修复标记升级为 `#md-table-render-v5`；已有 `#md-table-render-v4` 的文档会被视为旧修复状态，下一次同步仍会在原 doc token 内全量重建一次，以清理云端残留的“空段落 + 内容”结构。
- 测试：
  - `python -m pytest -q`（在 `apps/backend` 目录执行）
  - `python -m pip install --dry-run -e apps/backend`
  - `npm run build`（在 `apps/frontend` 目录执行）
  - `python scripts/build_installer.py --nsis`
  - `python scripts/release_notes.py --version v0.7.5 --asset "dist/LarkSync-Setup-v0.7.5.exe" --output "dist/release-notes-v0.7.5.md"`

## v0.7.5-dev.1 (2026-05-15)

- 目标：
  - 修复 V1.5 文档表格上传后部分单元格视觉上靠下的问题；确认原因是飞书新建表格 cell 自带默认空段落，LarkSync 追加真实内容时没有先清理。
- 结果：
  - `DocxService._populate_table_cells` 在向每个目标 cell 写入内容前调用 `batch_delete` 删除第 1 个默认子块，避免单元格最终变成两个文本块。
  - 更新回归测试，锁定表格 cell 填充必须先清理默认空段落，并且不会继续向 table block 本身创建 cell 子块。
  - `SyncTaskRunner` 将超限表格渲染修复标记从 `#md-table-render-v4` 升级到 `#md-table-render-v5`，使已经完成过 v0.7.4 修复的历史文档在升级后仍会通过普通同步重新覆盖一次云端文档。
- 测试：
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py::test_upload_new_markdown_with_large_table_runs_block_replace_after_import tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_repairs_previous_table_marker_large_table_link_once -q`

## v0.7.4 release (2026-05-12)

- 目标：
  - 发布 `v0.7.4` 稳定版，纠正 `v0.7.3` 将用户期望的“垂直居中”误实现为文本水平居中的问题。
- 结果：
  - 稳定版包含 `v0.7.4-dev.1`：撤销表格单元格文本 `Text.style.align=2` 写入逻辑，保持飞书默认水平左对齐。
  - 超限表格渲染修复标记升级为 `#md-table-render-v4`；已有 `#md-table-render-v3` 的文档会被视为旧修复状态，下一次同步仍会在原 doc token 内全量重建一次，以清理 v0.7.3 造成的水平居中样式。
  - 已确认飞书官方 Docx Block 数据结构中 `Text.style.align` 是水平对齐字段，`TableCell` 目前没有公开可写的垂直对齐字段；后续若要实现垂直居中，需要先取得飞书返回的表格单元格样式 JSON 或新的官方字段定义。
- 测试：
  - `python -m pytest -q`（在 `apps/backend` 目录执行）
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`
  - `python scripts/release_notes.py --version v0.7.4 --asset "dist/LarkSync-Setup-v0.7.4.exe" --output release-notes-preview.md`
  - `python -m pytest tests/test_release.py tests/test_release_notes.py tests/test_version.py -q`

## v0.7.4-dev.1 (2026-05-12)

- 目标：
  - 修正 `v0.7.3` 表格样式方向错误：水平对齐应保持默认左对齐，不能写成水平居中。
- 结果：
  - 移除 `DocxService` 中递归给表格 cell 内文本类 block 写入 `style.align=2` 的逻辑。
  - 更新回归测试，锁定 Markdown 表格上传转换结果不会主动写入水平 `style.align`。
  - `SyncTaskRunner` 将超限表格渲染修复标记从 `#md-table-render-v3` 升级到 `#md-table-render-v4`，使已安装并运行过 `v0.7.3` 的用户在升级后通过普通同步重新覆盖一次云端文档。
- 测试：
  - `python -m pytest tests/test_docx_service.py::test_patch_table_properties_leaves_table_cell_horizontal_alignment_default tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_repairs_previous_table_marker_large_table_link_once -q`

## v0.7.3 release (2026-05-12)

- 目标：
  - 发布 `v0.7.3` 稳定版，补齐 Markdown 表格上传到飞书后的单元格文本居中，并让已执行过 `v0.7.2` 修复的历史文档再触发一次重建。
- 结果：
  - 稳定版包含 `v0.7.3-dev.1`：表格单元格内文本块会写入飞书 `style.align=2` 居中样式。
  - 超限表格渲染修复标记升级为 `#md-table-render-v3`；已有 `#md-table-render-v2` 的文档会被视为旧修复状态，下一次同步仍会在原 doc token 内全量重建一次。
  - 修复范围继续覆盖“软件设计说明书 V1.5”这类历史表格坏块场景，不要求用户手动改动 Markdown 文件。
- 测试：
  - `python -m pytest -q`（在 `apps/backend` 目录执行）
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`
  - `python scripts/release_notes.py --version v0.7.3 --asset "dist/LarkSync-Setup-v0.7.3.exe" --output release-notes-preview.md`
  - `python -m pytest tests/test_release.py tests/test_release_notes.py tests/test_version.py -q`

## v0.7.3-dev.1 (2026-05-12)

- 目标：
  - 继续收口用户反馈的飞书表格显示问题：表格已经变成原生表格后，单元格内部文本仍未居中。
- 结果：
  - `DocxService` 在补齐表格行列数和列宽后，会递归遍历表格 cell 内的文本类 block，仅对表格内部文本写入 `style.align=2`，不影响表格外正文。
  - `SyncTaskRunner` 将超限表格渲染修复标记从 `#md-table-render-v2` 升级到 `#md-table-render-v3`，使已安装并运行过 `v0.7.2` 的用户在升级后仍能通过普通同步重新覆盖一次云端文档。
  - 新增回归测试覆盖表格内部文本居中，以及已有旧 `#md-table-render-v2` 标记但本地 hash 未变化时仍不跳过同步。
- 测试：
  - `python -m pytest tests/test_docx_service.py::test_patch_table_properties_centers_table_cell_text_blocks tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_repairs_old_table_marker_large_table_link_once -q`
  - `python -m pytest tests/test_docx_service.py tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest -q`（在 `apps/backend` 目录执行）

## v0.7.2 release (2026-05-11)

- 目标：
  - 发布 `v0.7.2` 稳定版，交付既有云端 Markdown 文档的大表格历史坏块重建修复。
- 结果：
  - 稳定版包含 `v0.7.2-dev.1`：缺少 `#md-table-render-v2` 标记的超限表格文档，会在下一次同步时跳过局部 diff，在原 doc token 内全量重建。
  - 修复范围覆盖用户反馈的“软件设计说明书 V1.5 更新后仍有表格式代码、表格框仍窄”的残留云端块问题。
- 测试：
  - `python -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`
  - `python scripts/release_notes.py --version v0.7.2 --asset "dist/LarkSync-Setup-v0.7.2.exe" --output release-notes-preview.md`
  - `python -m pytest tests/test_release.py tests/test_release_notes.py tests/test_version.py -q`

## v0.7.2-dev.1 (2026-05-11)

- 目标：
  - 修复 `v0.7.1` 只改善新转换块、无法重建历史坏表格块的问题；用户更新后重新同步 V1.5 仍可看到旧代码块和窄表格。
- 结果：
  - 定位到 V1.5 在 `v0.7.1` 下已上传，但同步器走局部块 diff，源 Markdown hash 未变化的旧云端表格块不会被重建。
  - `SyncTaskRunner` 在 `auto` 模式检测到超限 Markdown 表格时，会跳过局部块更新，直接在原 doc token 内执行 full replace，再重建块状态。
  - 为超限表格修复加入 `#md-table-render-v2` 渲染修复标记；既有云端文档缺少该标记时，即使本地文件 hash 和块状态未变化，也会自动执行一次同 token 全量重建。
  - 新建 Markdown 文档如果含超限表格，飞书导入创建后会立刻再走一次块级覆盖，避免初始导入产物残留代码块表格。
  - 用当前 V1.5 做飞书 `blocks/convert` dry-run：转换输出 `159` 个表格块、`0` 个代码块，确认转换本身已正确，问题来自历史云端块未被重建。
- 测试：
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py::test_upload_markdown_forces_full_replace_for_existing_large_table_doc -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_sync_runner_block_update.py tests/test_docx_service.py -q`
  - `python -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`（生成 `dist/LarkSync-Setup-v0.7.2-dev.1.exe`）

## v0.7.1 release (2026-05-11)

- 目标：
  - 发布 `v0.7.1` 稳定版，交付“算云项目更新”中软件设计说明书 V1.5 的表格上传修复。
- 结果：
  - 版本号从 `v0.7.1-dev.1` 收敛为稳定版 `v0.7.1`。
  - 稳定版包含 Markdown 表格上传前拆分超限大表、补齐表格列宽、避免表格失败后降级为代码块的修复。
  - 推送 `v0.7.1` tag 后由 GitHub Actions `Release Build` 自动构建并上传 GitHub Release Windows 安装包与校验文件。
- 测试：
  - `python -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`
  - `python scripts/release_notes.py --version v0.7.1 --asset "dist/LarkSync-Setup-v0.7.1.exe" --output release-notes-preview.md`
  - `python -m pytest tests/test_release.py tests/test_release_notes.py tests/test_version.py -q`

## v0.7.1-dev.1 (2026-05-11)

- 目标：
  - 修复“算云项目更新”中 `软件设计说明书-V1.5.md` 上传飞书后表格过窄、部分大表被写成代码块的问题。
- 结果：
  - `DocxService` 在调用飞书 `blocks/convert` 前会把超过飞书建表行数限制的 Markdown 表格拆成多个原生表格，保留表头并避免触发表格创建失败。
  - 表格属性会根据 Markdown 单元格内容补齐 `column_width`，创建请求继续剥离 `cells/merge_info`，但保留合法列宽，改善默认窄表格显示。
  - 表格创建失败的兜底逻辑改为“拆表重试 -> 普通文本兜底”，不再把表格包装成 fenced `markdown` 代码块。
  - 用 `软件设计说明书-V1.5.md` 做本地 dry-run：原 118 个表格中 37 个超过 8 行，拆分后为 159 个表格，最大行数为 8。
- 测试：
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_markdown_blocks.py tests/test_sync_runner_block_update.py -q`
  - `python -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`（生成 `dist/LarkSync-Setup-v0.7.1-dev.1.exe`）

## v0.7.0 release (2026-05-11)

- 目标：
  - 发布 `v0.7.0` 稳定版，收口日志中心事件时间线按动作类型筛选的用户可见能力。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.7.0`。
  - 稳定版包含 `v0.6.21-dev.1`：日志中心运行详情的事件时间线可按 `上传 / 下载 / 删除 / 问题 / 跳过 / 实际变更` 分别筛选，删除筛选覆盖删除成功、待删除和删除失败。
  - Release notes 生成逻辑支持跨 minor/major 稳定版发布时按 changelog 变更区间收集 dev 开发日志，确保 `v0.7.0` 这种目标版本仍能展示本次纳入的实际开发版本详情。
- 测试：
  - `$env:PYTHONPATH='apps/backend'; python -m pytest apps/backend/tests/test_release_notes.py -q`
  - `npm --prefix apps/frontend test`
  - `npm run build --prefix apps/frontend`
  - `$env:PYTHONPATH='apps/backend'; python -m pytest apps/backend/tests/test_version.py apps/backend/tests/test_release_notes.py -q`
  - `$env:PYTHONPATH=''; python -m pytest -q`（在 `apps/backend` 目录执行）
  - `python scripts/build_installer.py --nsis`

## v0.6.21-dev.1 (2026-05-11)

- 目标：
  - 在日志中心运行详情的“事件”时间线中，支持按上传、下载、删除等动作类型分别筛选。
- 结果：
  - 前端新增 `eventFilters` 纯函数模块，统一维护事件筛选项和后端 `statuses` 查询参数映射。
  - 日志中心事件 Tab 新增 `上传 / 下载 / 删除` 动作级筛选；删除筛选覆盖 `deleted / delete_pending / delete_failed`，可单独查看删除成功、待删除和删除失败相关事件。
  - 前端引入 Vitest 并补充事件筛选规则单元测试，锁定上传、下载、删除和既有聚合筛选的状态映射。
- 测试：
  - `npm --prefix apps/frontend test`
  - `npm run build --prefix apps/frontend`

## v0.6.20 release (2026-05-06)

- 目标：
  - 发布 `v0.6.20` 稳定版，收口删除链路状态在日志中心“实际变更”和多个任务状态摘要里被漏显示的问题。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.20`，正式版会随稳定 tag 触发 Release Build 工作流自动生成安装包、校验文件和发布说明。
  - 后端 `/sync/tasks/status` 响应补齐 `uploaded_files / downloaded_files / deleted_files / conflict_files / delete_pending_files / delete_failed_files`，前端实时状态轮询可以拿到完整删除链路计数。
  - 日志中心运行记录、概览状态胶囊、运行判断，以及任务页/仪表盘摘要统一展示 `删除 / 待删除 / 删除失败`，不再只露出上传、下载、失败、冲突。
- 测试：
  - `python -m pytest apps/backend/tests/test_version.py apps/backend/tests/test_sync_task_api.py apps/backend/tests/test_tray_status.py -p pytest_asyncio.plugin -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.20-dev.1 (2026-05-06)

- 目标：
  - 修复删除链路在日志中心“实际变更”和多个任务状态摘要里被漏显示的问题。
- 结果：
  - 后端 `/sync/tasks/status` 响应补齐 `uploaded_files / downloaded_files / deleted_files / conflict_files / delete_pending_files / delete_failed_files`，前端实时状态轮询现在可以拿到完整删除链路计数。
  - 日志中心运行记录、概览状态胶囊、运行判断，以及任务页/仪表盘摘要统一补上 `删除 / 待删除 / 删除失败` 展示，不再只露出上传、下载、失败、冲突。
  - 补充后端回归测试，锁定实时状态接口和任务概览接口都不能再丢删除相关计数。
- 测试：
  - `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONPATH='apps/backend'; python -m pytest apps/backend/tests/test_sync_task_api.py apps/backend/tests/test_tray_status.py -p pytest_asyncio.plugin -q`
  - `npm run build --prefix apps/frontend`

## v0.6.19 release (2026-05-06)

- 目标：
  - 在 `v0.6.18` 的基础上继续收口两个现场残留问题：任务切换仍慢，以及冲突管理连续点击多条时最后只真正处理成功一条。
- 结果：
  - 复核现场安装目录日志后确认，任务切换剩余卡顿不在 `sync_runs` 查询，而在 `get_task_diagnostics()` 缺少摘要时仍会回退扫描 `sync-events.jsonl`；现在仅在明确查看事件/问题明细或指定 `run_id` 时才允许回退扫描，概览模式直接返回轻量结果。
  - 冲突管理前端改为 `ref` 驱动的单 worker 串行泵，移除 `useEffect + state` 启动队列的竞态；连续点击多条冲突时会严格按顺序提交，不再把多个 `resolve` 请求并发打到后端。
  - 根包、前端和后端版本统一更新为 `v0.6.19`，用于正式发布。
- 测试：
  - `python -m pytest tests/test_conflict_resolution_service.py tests/test_conflict_resolution_runner.py tests/test_sync_task_api.py tests/test_sync_event_store.py -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.19-dev.1 (2026-05-06)

- 目标：
  - 修复冲突管理“看起来支持多选排队，但连续点击多条时最后只有一条真正处理成功”的现场问题。
- 结果：
  - 复核现场 `v0.6.18` 日志后确认根因在前端排队实现：`useEffect + state` 启动队列存在竞态，连续点击时多个 `resolve` 请求会在 `activeConflictResolution` 提交前并发打到后端，同任务的其余请求因此收到 `409 任务运行中`。
  - 冲突管理改为 `ref` 驱动的单 worker 串行泵，`conflictQueueRef` 作为唯一队列真源，避免 React state 延迟导致同任务请求并发发出。
  - `useConflicts` 去掉共享 mutation，改为单次 `apiFetch` 成功后再刷新冲突列表，减少并发状态耦合。
  - 继续复核现场任务切换耗时后确认另一个慢点在 `get_task_diagnostics()`：当任务缺少 `sync_runs` 摘要时，概览模式也会回退扫描整个 `sync-events.jsonl` 来补历史 run，导致切任务仍然卡在 5~15 秒。
  - 任务诊断改为只在真正查看事件/问题明细或指定 `run_id` 时才允许回退扫描 `sync-events.jsonl`；概览模式下若缺少 `sync_runs` 摘要，直接返回轻量结果，不再为补历史 run 阻塞切换。
- 测试：
  - `npm run build --prefix apps/frontend`
  - `python -m pytest tests/test_sync_task_api.py tests/test_sync_event_store.py -q`

## v0.6.18 release (2026-05-06)

- 目标：
  - 继续收口日志中心的现场交互问题，解决“切换任务仍然很慢”和“冲突管理点击后反馈不清”。
- 结果：
  - 日志中心任务诊断默认改为 `概览` 标签页；切换任务时会同步清空已选 run，并避免在 `概览 / 事件` 间因为相同 diagnostics 参数重复发请求，减少切换任务时误触发的大日志扫描。
  - 冲突管理状态扩展为 `已排队 / 处理中 / 等待任务空闲 / 已完成 / 处理失败`；同一条冲突在后台任务占用时会自动等待并重试，不再直接把状态清空成“像没点过一样”。
  - 手动刷新任务诊断时，只有当前就在 `事件` 标签页才会额外刷新事件时间线，避免无意义地触发 `sync-events.jsonl` 扫描。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.17 release (2026-05-05)

- 目标：
  - 发布 `v0.6.17` 稳定版，收口本轮三项修复：文件占用写盘提示、冲突管理排队处理、日志中心切任务提速。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.17`。
  - 稳定版包含三项核心修复：一是云端文件下载写回本地时，遇到 WPS/Office 占用会短重试，并给出明确“文件被其他程序占用”的错误提示；二是冲突管理允许连续为多条冲突选择“使用本地 / 使用云端”，前端显示“已排队 / 处理中”并按顺序提交；三是日志中心切换任务时优先使用 `sync_runs` 摘要表，只在真正查看事件/问题明细时才读取 `sync-events.jsonl`，显著降低大日志场景的切换卡顿。
  - README、CHANGELOG、版本号与正式安装包均已同步到 `v0.6.17`。
- 测试：
  - `python -m pytest tests/test_file_writer.py tests/test_conflict_resolution_service.py tests/test_conflict_resolution_runner.py tests/test_sync_task_api.py tests/test_sync_event_store.py -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.17-dev.3 (2026-05-05)

- 目标：
  - 修复日志中心任务诊断切换任务时明显卡顿的问题，降低大体积 `sync-events.jsonl` 对 UI 交互的拖累。
- 结果：
  - 前端任务切换改为单轮 diagnostics：不再先拉一版基础 diagnostics、再拉一版指定 run 的 diagnostics；当前任务的运行摘要直接由同一条查询返回。
  - 事件时间线继续走独立 `/sync/logs/sync` 分页接口，但仅在 `事件` 标签页激活时请求；`问题` 标签页才请求 problems，避免切换任务时无条件扫事件日志。
  - 后端 `/sync/tasks/overview` 与 `/sync/tasks/{id}/diagnostics` 优先使用 `sync_runs` 摘要表；只在真正需要事件/问题明细时才读取 `sync-events.jsonl`，并保留“没有 run 摘要时再回退扫历史日志”的兼容兜底。
  - README、CHANGELOG 与版本号已同步更新到 `v0.6.17-dev.3`。
- 测试：
  - `python -m pytest tests/test_sync_task_api.py tests/test_sync_event_store.py -q`
  - `npm run build --prefix apps/frontend`

## v0.6.17-dev.2 (2026-05-05)

- 目标：
  - 修复冲突管理里“前一个没处理完，后一个就不能先选方案”的交互阻塞问题，并清理前端暴露但后端并不支持的冲突动作。
- 结果：
  - 日志中心冲突管理新增前端排队器：用户可以连续为多条冲突选择“使用本地 / 使用云端”，页面会即时显示“已排队 / 处理中”，并按顺序提交给后端执行。
  - 保留后端按任务串行执行的安全边界，不改变现有手动冲突处理的覆盖逻辑，只修正前端交互与状态反馈。
  - 冲突管理页移除未实现的“保留双方”按钮，避免前端发出后端 `409/422` 必然失败的无效动作。
  - README、CHANGELOG 与版本号已同步更新到 `v0.6.17-dev.2`。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.17-dev.1 (2026-05-05)

- 目标：
  - 修复云端文件下行写回本地时，目标文件被 WPS/Office 占用只暴露原始 `[Errno 13] Permission denied`、用户无法判断根因的问题。
- 结果：
  - `FileWriter` 新增 Windows 文件占用识别：遇到 `winerror=32/33` 的共享冲突时，会做短暂重试，覆盖 WPS/Office 刚释放句柄的瞬时场景。
  - 若重试后仍失败，会抛出可直接行动的错误文案“目标文件正被其他程序占用，请关闭后重试”，同步日志和运行摘要不再只显示裸 `Permission denied`。
  - README、CHANGELOG 与版本号已同步更新到 `v0.6.17-dev.1`。
- 测试：
  - `python -m pytest tests/test_file_writer.py -q`

## v0.6.16 release (2026-05-04)

- 目标：
  - 发布 `v0.6.16` 稳定版，交付“任务级独立调度”和运行结束后 `current_run_id` 收尾修正，解决单个任务阻塞其它任务开启新 run 的问题。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.16`。
  - 稳定版包含两项核心修正：一是上传/下载调度改为任务级独立循环，单个任务长时间运行、失败或卡住时不再阻塞其他任务的新一轮 run；二是同步运行结束后统一清空 `current_run_id`，后续 `queued` 事件不会再错误挂入上一轮已完成 run 的时间线。
  - README、CHANGELOG 已同步更新。
- 测试：
  - `C:\\Python314\\python.exe` + 临时隔离依赖目录执行 `pytest apps/backend/tests -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.16-dev.1 (2026-05-04)

- 目标：
  - 修复“某个任务长时间运行时，其它任务的新上传迟迟不开新 run”的串行调度问题，并清理 run 结束后的旧 `current_run_id` 遗留。
- 结果：
  - `SyncScheduler` 改为任务级独立上传/下载循环；每个可同步任务都有自己的调度 worker，单个任务长跑、失败或卡在块替换时，不再阻塞其它任务按周期开启新的同步 run。
  - `SyncTaskRunner` 在运行结束后统一清空 `current_run_id`，新的 `queued` 事件不再错误归到上一轮已完成的 run，任务时间线与运行详情保持一致。
  - README、CHANGELOG 与后端版本号已同步更新到 `v0.6.16-dev.1`。
- 测试：
  - `C:\\Python314\\python.exe` + 临时隔离依赖目录执行 `pytest apps/backend/tests/test_sync_scheduler.py apps/backend/tests/test_sync_runner.py -q`
  - `C:\\Python314\\python.exe` + 临时隔离依赖目录执行 `pytest apps/backend/tests -q`

## v0.6.15 release (2026-05-02)

- 目标：
  - 发布 `v0.6.15` 稳定版，交付“超限表格优先整表块替换”的行为修正，解除 `partial` 模式下大表文档与冲突处理的主要卡点。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.15`。
  - 稳定版包含两项核心修正：一是运行中更新忽略目录等执行范围配置会自动取消并重启任务，确保新配置立刻生效；二是已有云端 Markdown 文档遇到超限表格时，`partial/auto` 会优先按整表块替换并尽量保持原文档 token，只有块替换与同 token 全量覆盖都失败时才回退到导入重建。
  - README、CHANGELOG 已同步更新。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.15-dev.2 (2026-05-02)

- 目标：
  - 修复 `partial` 模式遇到超限 Markdown 表格时直接报错、冲突里的“使用本地版本”无法落地的问题，并避免已有云端文档一上来就被导入重建换 token。
- 结果：
  - `SyncTaskRunner._upload_markdown()` 调整为“大表优先整块替换”的顺序：已有云端文档在 `auto/partial` 下会先走块级替换；`partial` 不再直接拒绝超限表格。
  - `auto` 模式下若块替换未命中，会先尝试同 token 全量覆盖；只有同 token 覆盖也失败时，才回退到飞书原生 Markdown 导入重建。
  - 补充回归测试，覆盖已有云端大表文档在 `auto` 和 `partial` 下都优先保持原 token、不会触发导入重建。
  - README、CHANGELOG 与后端版本号已同步更新到 `v0.6.15-dev.2`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_runner_upload_new_doc.py tests/test_sync_runner_block_update.py -q`
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `npm run build --prefix apps/frontend`

## v0.6.15-dev.1 (2026-05-01)

- 目标：
  - 修复“忽略目录已保存，但运行中的任务仍继续扫描和上传旧目录范围”的问题。
- 结果：
  - 新增任务更新重启判定：当用户修改 `ignored_subpaths`、同步模式、更新模式、本地路径、云端目录等会影响执行范围的字段时，运行中的任务会先取消，再按最新配置自动重启。
  - `SyncTaskRunner` 新增配置变更重启能力，支持在当前 run 结束清理后立刻拉起带新配置的下一轮，避免 `start_task()` 在旧 run 尚未退出时直接返回旧状态。
  - 现场核实当前安装版运行库位于 `F:\\Program Files (x86)\\LarkSync\\_internal\\data\\larksync.db`；`同步-宁怡` 的 `ignored_subpaths` 已正确持久化为 `POC/GENESIS`。本次问题的直接原因不是“没保存”，而是当前 run `93ba280a-7d00-42fc-ab9f-084e3e2c3e5e` 启动于配置更新之前，随后仍按旧配置继续上传。
  - 已现场将 `同步-宁怡` 停止并重新启动，新 run `76716b42-a127-49a6-bdf9-5e1f6bf842b3` 启动后未再出现 `POC/GENESIS` 相关事件。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_runner.py -k restart_task_restarts_running_task_with_latest_config -q`
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_task_api.py -q`
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_task_service.py -k ignored_subpaths -q`
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_runner.py -k 'ignored_subpaths or cloud_missing_delete_for_ignored_path' -q`
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`

## v0.6.14 release (2026-05-01)

- 目标：
  - 发布 `v0.6.14` 稳定版，修复 Windows 静默安装卡在 handoff 超时、安装器未真正接管的问题。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.14`。
  - 静默安装改为两阶段链路：托盘先起隐藏 bootstrap，bootstrap 再起独立 PowerShell worker 执行安装、等待退出并重启新版本。
  - README、CHANGELOG 已同步更新。
- 测试：
  - `python scripts/sync_feishu_docs.py`
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.14-dev.1 (2026-05-01)

- 目标：
  - 修复当前 `v0.6.11 -> v0.6.13` 静默升级时卡在“安装程序未返回接管确认”的问题。
- 结果：
  - 把原来 Python 直接拉起 detached helper 的做法改成“隐藏 bootstrap -> 独立 worker”两阶段接管，先稳定拿到 handoff，再让 worker 脱离主程序生命周期执行静默安装。
  - 新增 bootstrap 命令构造测试，并调整 Windows 静默安装测试，确保接管逻辑不再依赖 Python 侧直接起 detached helper。
  - README、CHANGELOG、根包/后端/前端版本已更新到 `v0.6.14`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_tray_update_install.py -q`
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `npm run build --prefix apps/frontend`

## v0.6.13 release (2026-05-01)

- 目标：
  - 发布 `v0.6.13` 稳定版，交付任务级双向忽略目录能力，避免忽略目录继续参与下载或云删本地。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.13`。
  - 稳定版包含双向忽略目录：已忽略子目录不会再参与本地上传、云端下载、云删本地以及已排队删除墓碑执行。
  - README、CHANGELOG 已同步更新。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.13-dev.1 (2026-05-01)

- 目标：
  - 把上一版“忽略目录”从只挡本地上行，补成真正的双向忽略，避免用户把目录加入忽略后仍被云端下载或云端删除联动影响本地。
- 结果：
  - 云端下载候选在落地本地前会先经过任务级忽略目录过滤，被忽略目录下的云端文件不会再下载到本地。
  - 云端缺失检测在为本地文件创建 `source="cloud"` 删除墓碑前，也会跳过已忽略目录下的既有映射。
  - 已排队但尚未执行的云端删除墓碑，在执行阶段如果发现目标路径已被加入忽略目录，会直接取消，不再删除本地文件。
  - 设置页文案改为“双向忽略目录”，明确该能力会同时跳过上传、下载和删除联动。
  - README、CHANGELOG、根包/后端/前端版本已更新到 `v0.6.13-dev.1`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_runner.py -q`
  - `npm run build --prefix apps/frontend`

## v0.6.12 release (2026-05-01)

- 目标：
  - 发布 `v0.6.12` 稳定版，交付任务级本地忽略目录能力，并收口重复安装同版本时的错误感知。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.12`。
  - 稳定版包含设置页按任务配置本地忽略目录、后端按任务忽略对应子目录的监听与上传扫描，以及静默安装接口对同版本/旧版本重复安装的明确阻断提示。
  - CHANGELOG 与 README 已更新。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py`

## v0.6.12-dev.1 (2026-05-01)

- 目标：
  - 为本地上行同步增加任务级忽略子目录能力，避免工程目录和缓存目录进入飞书；同时确认并收口“升级成功后再次触发同版本安装，看起来像失败”的体验问题。
- 结果：
  - `sync_tasks` 新增任务级 `ignored_subpaths` 配置，支持在设置页为每个任务维护多条本地忽略目录。
  - 后端会在本地全量扫描、待上传补扫和 watcher 事件处理阶段统一跳过这些子目录，避免 `node_modules`、`.git` 等工程目录继续进入上行同步链路。
  - 设置页新增“本地忽略目录”区块，支持手填相对路径或调用系统文件夹选择器挑选当前任务根目录下的子目录，并按任务保存。
  - `/system/update/install` 现在会在排队前判断安装包版本是否真的比当前版本新；若当前已是该版本或更高版本，会直接返回明确错误，不再让前端误以为“静默安装失败”。
  - 本机最新一次“升级失败”实查结果为：当前程序已运行 `v0.6.11`，安装目录 `F:\Program Files (x86)\LarkSync\LarkSync.exe` 时间戳已更新到 `2026-05-01 17:24:12`；日志中的 `忽略过期安装请求 (current=v0.6.11 request=v0.6.11)` 表示升级完成后又收到同版本请求并被正常忽略，并非安装器执行失败。
  - README、CHANGELOG、根包/后端/前端版本已更新到 `v0.6.12-dev.1`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_task_service.py tests/test_sync_runner.py tests/test_system_update_api.py -q`
  - `npm run build --prefix apps/frontend`

## v0.6.11 release (2026-05-01)

- 目标：
  - 发布 `v0.6.11` 稳定版，包含静默更新 helper 脱离修复与设置页“打开安装包目录”入口。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.11`。
  - 稳定版包含 Windows 静默更新 helper detached + breakaway 启动修复，以及设置页更新区新增“打开安装包目录”按钮。
  - CHANGELOG 与 README 已更新。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py`

## v0.6.11-dev.3 (2026-05-01)

- 目标：
  - 给设置页更新区增加“打开安装包目录”入口，方便静默安装失败后快速手动排查或重试。
- 结果：
  - 后端新增 `/system/update/open-download-folder` 接口，只允许打开当前已下载更新所在目录；若安装包不存在或尚未下载，会返回明确错误。
  - 设置页更新区在已下载更新包时新增“打开安装包目录”按钮，位置与“静默安装已下载更新”并列，点击后直接打开下载目录。
  - 已下载路径展示改为 `break-all`，长路径不会在卡片内溢出。
  - README、CHANGELOG、根包/后端/前端版本已更新到 `v0.6.11-dev.3`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_system_update_api.py -q`
  - `npm run build --prefix apps/frontend`

## v0.6.11-dev.2 (2026-05-01)

- 目标：
  - 修复用户刚发起的 `v0.6.10` 静默升级再次停在“installer_started”后没有完成安装/重启的问题。
- 结果：
  - 本机 `update-install.log` 显示 16:41:14 已成功写入 `installer_started pid=19088`，但之后没有 `install_succeeded` / `install_failed` / `已请求重启新版本`，同时主程序已退出且 `localhost:8000` 不再可连。
  - 安装目录 `F:\Program Files (x86)\LarkSync\LarkSync.exe` 时间戳仍停留在 `2026-05-01 15:39:04`，说明本次静默升级没有完成落盘。
  - 结合链路实现，问题收敛为静默更新 helper 进程虽被拉起，但没有在托盘退出后稳定脱离父进程继续执行安装收尾。
  - Windows 静默更新 helper 的创建参数改为同时启用 `DETACHED_PROCESS` 与 `CREATE_BREAKAWAY_FROM_JOB`，保留隐藏窗口和新进程组，确保托盘退出后 helper 仍能继续等待安装器结束并负责重启新版本。
  - README、CHANGELOG、根包/后端/前端版本已更新到 `v0.6.11-dev.2`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_tray_update_install.py -q`
  - `npm run build --prefix apps/frontend`

## v0.6.11-dev.1 (2026-05-01)

- 目标：
  - 排查并修复“静默更新已下载但再次安装失败/无反应”的缓存误导问题。
- 结果：
  - 本机日志确认 `v0.6.10` Release 与安装包构建成功；失败不在 GitHub 发布链路。
  - 运行中的 `v0.6.9` 客户端在 15:56 检查过更新，早于 16:20 发布的 `v0.6.10`，因此 `/system/update/status` 只读缓存时仍认为最新是 `v0.6.9`。
  - 旧缓存还会保留 `download_path`，在某些页面状态下可能把旧安装包当作“已下载更新”再次安装；托盘会按版本兜底忽略同版本安装包，于是表现成静默安装失败或无反应。
  - `UpdateService.load_cached_status()` 新增缓存净化：当前版本不低于 cached latest 时清空 `download_path`；cached latest 是新版本但本地安装包文件名版本不一致或文件不存在时也清空 `download_path`。
  - 已手动触发本机 `/system/update/check` 和 `/system/update/download`，确认 `v0.6.10` 可被发现并下载，sha256 与 Release 资产一致。
  - README、CHANGELOG、根包/后端/前端版本已更新到 `v0.6.11-dev.1`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_update_service.py -q`

## v0.6.10 release (2026-05-01)

- 目标：
  - 发布 `v0.6.10` 补丁版，尽快交付 `v0.6.10-dev.1` 对同步诊断与上传错误可观测性的修复。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.10`。
  - 稳定版包含历史中断运行不再误显示“同步中”、等待上传事件补齐 run_id、上传错误显示飞书 code/http/request_id，以及日志中心运行耗时修复。
  - CHANGELOG 与 README 已更新。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `npm run build --prefix apps/frontend`

## v0.6.10-dev.1 (2026-05-01)

- 目标：
  - 修复用户升级 `v0.6.9` 后“算云项目更新”同步失败只显示 `unknown error.`、日志中心存在多条历史“同步中”运行，以及运行耗时显示不可信的问题。
- 结果：
  - 运行诊断读取持久化 `sync_runs` 时，若历史记录仍为 `running` 且当前内存中没有对应运行，会展示为 `cancelled` 并提示“运行被中断”，避免应用更新/退出遗留记录继续显示同步中。
  - 同步队列事件在已有 `current_run_id` 时也写入 run_id，后续按单次运行查看事件时不会丢失等待上传记录。
  - 文件上传 API 错误信息保留飞书 `code`、HTTP 状态与请求 ID（如有），方便定位 `unknown error.` 这类飞书侧错误。
  - 日志中心运行耗时改为按秒级时间戳计算，修复几分钟运行显示成 1 秒的问题。
  - README、CHANGELOG、根包/后端/前端版本已更新到 `v0.6.10-dev.1`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_runner.py::test_handle_local_event_records_run_id_for_active_queued_event tests/test_tray_status.py::test_sync_task_diagnostics_marks_stale_persisted_running_runs_cancelled tests/test_file_uploader.py::test_upload_error_includes_code_and_http_status -q`

## v0.6.9 release (2026-05-01)

- 目标：
  - 发布 `v0.6.9` 稳定版，收口 `v0.6.9-dev.1` 的前端同步健康体验优化。
- 结果：
  - 根包、前端和后端版本统一更新为 `v0.6.9`。
  - 稳定版包含仪表盘同步健康总览、任务卡片健康摘要、冲突可信反馈和维护动作应用内确认框。
  - CHANGELOG 与 README 已更新。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.9-dev.1 (2026-05-01)

- 目标：
  - 按“补充 NAS 不足、让本地文件与飞书保持一致”的产品本质，优化前端同步健康表达与关键操作可信度。
- 结果：
  - 仪表盘从日志事件计数改为同步健康总览，展示健康状态、待同步、问题处理和最近成功，并将右侧日志流降噪为“需要关注”摘要。
  - 任务卡片默认突出本地目录与飞书目录的同步关系、待上传、失败、冲突和最近同步状态；任务 ID、base_path 等工程字段收进展开管理区。
  - 冲突解决操作改为等待后端成功后再 toast 成功，处理中禁用当前冲突操作，失败时保留冲突并显示错误。
  - 静默安装与重置同步映射改用应用内确认框，补充影响范围说明。
  - 根包与前端版本同步到 `v0.6.9-dev.1`，README 与 CHANGELOG 已更新。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.8-dev.1 (2026-05-01)

- 目标：
  - 收口本轮整体审查发现的三项工程质量问题：后端测试红灯、后端包不可 editable 安装、发布工作流缺少质量门。
- 结果：
  - `test_conflict_resolution_runner.py` 的 `UploadLinkService.upsert_link` 测试替身补齐 `local_resource_signature` 与 `resource_sync_revision` 参数，并写入 `SyncLinkItem`，恢复冲突处理“使用本地版本”路径测试。
  - `apps/backend/pyproject.toml` 改用内联 readme 元数据，避免 setuptools 拒绝读取包根目录外的 `../../README.md`，`pip install --dry-run -e apps/backend` 已可通过。
  - `.github/workflows/release-build.yml` 新增 `quality` job，在发布安装包前执行后端依赖安装、editable 安装 dry-run、后端 pytest 和前端构建；同时让正式 Windows / macOS 构建依赖该质量门。
  - README、CHANGELOG、根包/后端/前端版本与 lockfile 版本已同步到 `v0.6.8-dev.1`。
- 测试：
  - `$env:PYTHONPATH=''; ..\\..\\.venv\\Scripts\\python.exe -m pytest -q`
  - `$env:PYTHONPATH=''; .venv\\Scripts\\python.exe -m pip install --no-user --dry-run -e apps\\backend`
  - `npm run build --prefix apps/frontend`

## v0.6.7-dev.2 (2026-05-01)

- 目标：
  - 修复新版本安装完成后，旧静默安装请求仍残留在 `AppData\\Roaming\\LarkSync\\updates\\install-request.json`，导致新版本一启动又继续安装自己、表现成打不开或反复重启的问题。
- 结果：
  - 托盘新增安装请求版本兜底：解析安装包文件名中的版本号，并与当前运行版本比较；若安装包版本小于等于当前版本，则直接视为过期请求，清理 `install-request.json` 和 `install-handoff.json`，不再继续调度安装。
  - 配套补了单测，覆盖“同版本安装请求必须被清理、且不能再触发调度”。
  - 这层兜底和 `Start-Process -FilePath` 修复叠加后，既能避免 helper 参数错误，也能避免旧请求在安装成功后反复拉起更新流程。
- 测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .\\.venv\\Scripts\\python.exe -m pytest apps/backend/tests/test_tray_update_install.py -q`

## v0.6.7 release (2026-05-01)

- 目标：
  - 发布 `v0.6.7` 稳定版，完整收口 Windows 静默更新链路里“helper 参数错误”和“安装成功后旧请求残留循环”的两个问题。
- 结果：
  - 稳定版纳入 `v0.6.7-dev.1` 和 `v0.6.7-dev.2`：先修复 `v0.6.5 -> v0.6.6` 静默更新时 helper 使用 `Start-Process -LiteralPath` 导致安装器根本未启动的问题，再补上安装成功后对过期 `install-request.json` 的版本兜底清理。
  - PowerShell helper 已统一改为 `Start-Process -FilePath`，覆盖安装器启动、安装失败回退和安装成功后重启三处调用，避免再次出现“接管成功但安装器没起”的假成功链路。
  - 托盘现在会忽略安装包版本小于等于当前运行版本的静默安装请求，防止新版本一启动又被旧请求拉进自更新循环，表现成打不开或反复重启。
  - 配套单测已锁定 helper 生成脚本必须使用 `-FilePath`，并覆盖“同版本安装请求必须被清理”的场景，防止回归。
- 测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .\\.venv\\Scripts\\python.exe -m pytest apps/backend/tests/test_tray_update_install.py -q`
  - `npm run build --prefix apps/frontend`

## v0.6.7-dev.1 (2026-05-01)

- 目标：
  - 修复 Windows 静默更新在 helper 已经接管后，PowerShell 启动安装器阶段直接失败的问题。
  - 锁定 helper 脚本中安装器启动命令，避免后续再回归到无效参数。
- 结果：
  - 根据现场日志定位到 `v0.6.5 -> v0.6.6` 失败点：helper 已写入 handoff，但 PowerShell 执行 `Start-Process -LiteralPath` 报“找不到与参数名称 LiteralPath 匹配的参数”，导致安装器根本未启动。
  - `apps/tray/tray_app.py` 中 helper 脚本已统一改为 `Start-Process -FilePath`，覆盖安装器启动、安装失败回退和安装成功后重启当前版本三处调用。
  - 补充单测锁定生成脚本必须使用 `-FilePath`，避免这类参数错误再次进入正式版。
- 测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .\\.venv\\Scripts\\python.exe -m pytest apps/backend/tests/test_tray_update_install.py -q`

## v0.6.6 release (2026-05-01)

- 目标：
  - 发布 `v0.6.6` 稳定版，收口 Markdown 资源基线修复和日志中心任务诊断页整轮布局改造。
- 结果：
  - 稳定版纳入 `v0.6.6-dev.1` 至 `v0.6.6-dev.8`：修复双向同步中“云端下载生成本地 Markdown 后又被同轮回传覆盖云端”的问题，明确把正文内容和本地资源引用都纳入同步基线判断。
  - 日志中心任务诊断页完成整轮结构重做：从按任务堆叠视图改为按任务选择、运行记录、运行详情排障；运行记录按 `run_id` 独立查看，默认聚焦当前运行，历史问题不再混入当前诊断。
  - 页面交互继续收口到更紧凑的桌面工作台：任务选择改为可搜索 Combobox，详情头部保留最近活动时间，`概览` 去除重复的当前处理文件信息，并让左右下方面板与侧边栏底边对齐。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.6-dev.8 (2026-05-01)

- 目标：
  - 修正日志中心任务诊断页底部未对齐的问题，让左下运行记录和右下运行详情与左侧边栏底边一致。
  - 重做 `概览` 中重复的当前处理文件信息，避免同一内容在摘要和卡片中重复出现。
- 结果：
  - 任务诊断页在桌面端改为按主界面可用高度拉满，顶部页头和任务选择区固定后，底部双栏工作区占满剩余空间，左下与右下卡片底边跟随侧边栏统一对齐。
  - `概览` 顶部摘要仍保留当前处理文件，但下方原“当前处理文件”卡片改成“同步目标”，专门展示本地目录和云端目录；当前处理文件信息不再重复。
  - 当前处理条补充处理说明消息，避免把有用状态藏进重复卡片里。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.6-dev.7 (2026-05-01)

- 目标：
  - 按页面细节继续收口日志中心任务诊断页，解决任务选择器信息冗余和详情头部分割线过多的问题。
  - 保留最近活动时间，但让它更自然地并入详情头部。
- 结果：
  - 任务选择区正式改为可搜索 Combobox，主选择框只显示任务名，不再在选择框中混入路径信息；搜索和选择收拢到同一个下拉面板。
  - 右侧详情头部把最近活动时间提升到任务名同一行，下方只保留运行短码和路径，减少头部层级与分割线。
  - 右下常驻运行摘要继续保留在 `概览` 标签页，默认详情视图把更多高度让给 `事件` 时间线。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.6-dev.6 (2026-05-01)

- 目标：
  - 进一步提高日志中心任务诊断页的空间利用率，把任务选择从“下拉 + 独立搜索框”收成真正的可搜索 Combobox。
  - 让右侧详情头部信息更集中，减少分割线和重复块。
- 结果：
  - 任务选择区改为可搜索 Combobox：主输入框只显示任务名，展开后支持按任务名搜索并直接选中；本地路径从选择框中移除，只保留在右侧任务摘要信息里。
  - 右侧详情头部把最近活动时间提到任务名同一行，头部下方只保留运行短码和路径；去掉额外分割线，详情区更连贯。
  - 任务选择区保留“当前任务信息”摘要，但不再拆成低效的多块区域。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.6-dev.5 (2026-05-01)

- 目标：
  - 进一步收紧日志中心任务诊断页里仍然偏松散的区域，重点解决标题命名不准、说明文案无意义和详情区常驻摘要占空间的问题。
  - 保留最近活动时间，但把运行状态主摘要挪入 `概览`，给 `事件` 时间线更多默认高度。
- 结果：
  - `任务上下文` 区更名为 `任务选择`，移除说明文案与常驻任务筛选标签；任务名称、同步模式和最近活动时间改为更紧凑的单行任务摘要。
  - `运行记录` 区删除无意义副标题，继续保持紧凑列表。
  - 右下常驻运行状态摘要整体并入 `概览` 标签页，详情头部只保留任务名、路径、运行短码和最近活动时间，减少默认占高。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.6-dev.4 (2026-04-30)

- 目标：
  - 基于实际截图继续压缩日志中心任务诊断页的垂直和横向占用，减少重复信息。
  - 保持“上方选任务 / 下方看运行与详情”的结构不变，只做密度收口。
- 结果：
  - 任务上下文区改成更扁的选择条：当前任务、搜索和筛选集中排列，原先独立的任务信息块收成一行摘要文字。
  - 运行记录卡改成更紧凑的两行结构，`run_id` 默认显示短码，指标从网格改为横向简表，失败摘要行进一步压缩。
  - 运行详情头部去掉重复的路径/运行时间堆叠，摘要条补入当前处理文件，并把最近活动合并进头部元信息，整体更紧凑。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.6-dev.3 (2026-04-30)

- 目标：
  - 继续降低日志中心任务诊断页的横向拥挤感，去掉“任务常驻一整列”的布局负担。
  - 让任务数量不多时的使用路径更直接：先在上方选任务，再在下方看运行和详情。
- 结果：
  - 任务选择改为顶部上下文选择条，支持下拉切换、关键词检索和状态筛选；原先常驻左列任务列表被移除。
  - 日志中心主区域收敛为“左侧运行记录 / 右侧运行详情”双栏，横向空间集中留给真正的排障内容。
  - 现有独立滚动、摘要条和事件 Tab 专属筛选策略继续保留，整体结构更适合任务量较少的场景。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.6-dev.2 (2026-04-30)

- 目标：
  - 收紧日志中心任务诊断页的布局密度，解决保留全局侧边栏和顶部页头后内容区仍然过挤的问题。
  - 继续保留“任务 -> 运行 -> 详情”的排障主线，同时明确任务、运行记录、运行详情三块独立滚动。
- 结果：
  - 日志中心内容区调整为更克制的工作台：左侧任务栏压缩到更窄宽度，右侧继续分为“运行记录 / 运行详情”两层；任务卡和运行卡均改为更低高度、更轻信息密度。
  - 运行详情顶部不再拆成 6 张碎片化统计卡，而是合并为紧凑摘要条，统一展示运行时间、耗时、进度以及上传/下载/跳过/失败/冲突/总数。
  - 事件筛选和搜索框只在“事件”Tab 下显示；全局侧边栏和整体容器同步收窄/放宽，减少横向拥挤并保留现有导航框架。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.6.6-dev.1 (2026-04-30)

- 目标：
  - 修复双向同步中“云端下载生成本地 Markdown 与本地资源引用后，同一轮上传阶段又把该文档回传覆盖云端”的问题。
  - 明确区分“用户真实本地改动”和“同步器为了对齐云端而写入本地的改动”。
- 结果：
  - `sync_links` 新增 `local_resource_signature` 与 `resource_sync_revision`，把 Markdown 关联的本地图片/附件状态作为独立同步基线持久化。
  - `doc/docx -> markdown` 下载成功后，会基于当前本地资源引用计算资源签名，并和本次云端 revision 一起落库；后续上传只有在正文 hash 或本地资源签名偏离基线时才继续执行。
  - 上传短路判断从“是否存在本地图片引用”改成“正文是否偏离基线 + 本地资源是否偏离基线”，避免下载刚写回的 Markdown 因资源占位被误判为本地修改。
- 测试：
  - `.\\.venv\\Scripts\\python.exe -m pytest apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py -p pytest_asyncio.plugin -q`
  - `.\\.venv\\Scripts\\python.exe -m compileall apps/backend/src`

## v0.6.3-dev.2 (2026-04-29)

- 目标：
  - 修复双向同步中“云端下载写本地后被 watcher 误判成用户本地修改，随后又触发上传反向覆盖云端”的回流问题。
- 结果：
  - 下载链路在写本地文件前就会先静默 watcher，不再等写入完成后才补静默；覆盖 `docx/doc -> markdown`、导出型文件、普通附件三条下载分支。
  - 新增回归测试，明确约束本地写入发生时目标路径必须已经处于 watcher 静默状态，避免后续再出现“下载自己触发上传”的时序回退。
- 测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_runner.py -p pytest_asyncio.plugin -q`

## v0.6.3-dev.1 (2026-04-29)

- 目标：
  - 修复 Windows 静默更新里“主程序已退出，但安装器并未真正接管”的链路缺口。
  - 避免坏掉的安装请求在新版本启动后被反复消费，导致托盘持续尝试一个不存在的安装包。
- 结果：
  - 安装请求新增 `request_id`，托盘发起静默更新前会清理旧 handoff 状态，并等待 detached PowerShell helper 写入“已接管 / 安装器已启动 / 启动失败”的明确回执；只有 helper 成功接管后，主程序才会退出。
  - helper 启动安装器失败、安装器非零退出时，会记录 handoff 状态与安装日志，并尝试恢复拉起当前版本，避免“程序先退了，但后续没人管”的中断状态。
  - 托盘处理坏掉的 `install-request.json` 时会直接清理请求并弹出失败通知，不再每 5 秒重复尝试一个已不存在的安装包。
- 测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_update_service.py apps/backend/tests/test_system_update_api.py apps/backend/tests/test_tray_update_install.py -p pytest_asyncio.plugin -q`

## v0.6.2 release (2026-04-29)

- 目标：
  - 发布 `v0.6.2` 稳定版，收口删除安全、冲突中心、冲突执行和自动更新链路的连续修复。
  - 将 GitHub Release 说明升级为“升级重点 + 逐个 dev 版本详细变更”的明确结构，作为后续发布标准。
- 结果：
  - 稳定版基于 `v0.6.2-dev.1` 至 `v0.6.2-dev.5`：删除墓碑执行前会校验同 token 的有效本地链接，冲突列表去重，冲突管理的“使用本地 / 使用云端”会真正执行一次定向同步，不再只改状态。
  - Windows 自动更新链路补齐用户数据目录落盘、静默安装、安装器退出码记录和自动重启，降低正式版更新失败与状态误判风险。
  - 新增 [`docs/RELEASE_STANDARD.md`](docs/RELEASE_STANDARD.md)，`scripts/release_notes.py` 改为优先读取 `DEVELOPMENT_LOG.md` 生成 GitHub Release 说明；后续正式版发布页必须先给升级重点，再给逐个 `dev` 版本的详细结果，避免模糊摘要。
- 测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_release_notes.py apps/backend/tests/test_conflict_service.py apps/backend/tests/test_conflict_resolution_service.py apps/backend/tests/test_conflict_resolution_runner.py apps/backend/tests/test_tray_status.py -p pytest_asyncio.plugin -q`
  - `npm run build --prefix apps/frontend`

## v0.6.2-dev.5 (2026-04-29)

- 目标：
  - 修复冲突管理里“使用本地 / 使用云端”只改冲突状态、不执行实际同步的问题。
- 结果：
  - 新增 `ConflictResolutionService`，冲突解决从“仅写 resolved 标记”升级为“先定位关联任务，再调用同步执行器执行定向上传/下载，成功后才标记冲突已解决”。
  - `SyncTaskRunner` 新增冲突定向处理入口：`run_conflict_upload()` 会按本地优先强制绕过云端修改时间阻断，直接上传当前本地版本；`run_conflict_download()` 会按云端优先强制绕过“本地较新”跳过逻辑，下载指定云端文件覆盖本地。
  - 解决失败时冲突保持未解决状态，不再出现“页面显示已处理，但文件其实没变化”的假成功。
- 测试：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_conflict_service.py apps/backend/tests/test_conflict_resolution_service.py apps/backend/tests/test_conflict_resolution_runner.py apps/backend/tests/test_tray_status.py -p pytest_asyncio.plugin -q`
  - `npm run build --prefix apps/frontend`

## v0.6.2-dev.4 (2026-04-29)

- 目标：
  - 为 Windows 自动更新补齐静默安装能力，并在安装完成后自动重启新版本。
- 结果：
  - `/system/update/install` 默认会把 `silent=true`、`restart_path=<当前 LarkSync.exe>` 写入安装请求；前端安装入口改为“静默安装已下载更新”。
  - 托盘在 Windows 上检测到静默安装请求后，不再直接 ShellExecute 安装包，而是启动 detached PowerShell helper，以 NSIS `/S` 静默参数运行安装器、等待安装器退出，并在退出码为 0 时自动重启新版本。
  - `update-install.log` 新增静默安装阶段日志：安装器启动请求、PID、退出码、自动重启请求，便于定位“托盘已发起”和“安装器实际执行结果”之间的问题。
  - 仍保留 UAC 风险提示：如果安装目录位于 `Program Files`，Windows 可能继续弹出系统权限确认，这不属于安装向导界面。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_system_update_api.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_tray_update_install.py -q`
  - `npm run build --prefix apps/frontend`

## v0.6.2-dev.3 (2026-04-29)

- 目标：
  - 修复正式版自动更新“拉起安装程序不稳定”和更新完成后仍误报有新版本的问题。
- 结果：
  - 自动更新的安装包、`status.json`、`install-request.json`、`update.log` / `update-install.log` 在冻结打包环境下改为写入用户数据目录，不再落在安装目录 `_internal\\data` 下，降低自更新时与安装目录互相影响的风险。
  - 更新状态读取会始终以当前运行版本覆盖缓存中的 `current_version`，并在最新版本不高于当前版本时自动清掉 `update_available`，避免安装完成后继续提示同一版本更新。
  - 托盘日志文案从“使用 ShellExecute 启动安装包”改为“已请求 ShellExecute 启动安装包”，避免把系统已接收启动请求误记成安装器已经实际启动成功。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_update_service.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_system_update_api.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_tray_update_install.py -q`

## v0.6.2-dev.2 (2026-04-29)

- 目标：
  - 修复“冲突管理”页面会展示两条相同未解决冲突的问题。
- 结果：
  - `ConflictService.add_conflict()` 新增未解决冲突查重；同一路径、同一 cloud token、同一版本差异重复检测时复用原记录，不再重复写库。
  - `ConflictService.list_conflicts()` 会折叠历史残留的重复未解决记录；即使旧库里已存在重复数据，冲突管理页面也只展示一条当前冲突。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_conflict_service.py -q`

## v0.6.2-dev.1 (2026-04-29)

- 目标：
  - 修复云端删除旧路径后，本地安全回收动作被 watcher 当成用户删除，进而反向删除仍被新路径使用的云端文档的问题。
- 结果：
  - `source=local` 删除墓碑执行云端删除前，会检查同一任务内是否仍有其他存在且未被忽略的本地路径绑定同一个 cloud token。
  - 若同一 cloud token 仍有有效本地路径，删除墓碑会取消执行并记录跳过事件，不再调用飞书删除接口。
  - 本地安全删除移入 `.larksync_trash` 前，会静默源路径和回收目标路径的 watcher 事件，避免程序自身移动文件再次触发本地删除墓碑。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_runner.py::test_process_pending_deletes_cancels_cloud_delete_when_token_has_active_link apps/backend/tests/test_sync_runner.py::test_move_to_local_trash_silences_source_and_trash_target apps/backend/tests/test_sync_runner.py::test_process_pending_deletes_passes_cloud_type_to_drive_delete apps/backend/tests/test_sync_runner.py::test_handle_local_deleted_event_creates_tombstone -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.1 release (2026-04-28)

- 目标：
  - 发布 `v0.6.1` 稳定版，收口同步覆盖保护、任务状态展示和日志中心诊断能力。
- 结果：
  - 稳定版基于 `v0.6.1-dev.1` 至 `v0.6.1-dev.4`：Markdown 上行覆盖前会复核云端修改时间，避免本地旧版本覆盖飞书协作版本。
  - 仪表盘与任务页区分“当前运行”和“最近同步”，任务状态、最近运行和进度展示使用更真实的运行数据。
  - 日志中心升级为任务诊断入口，后端提供任务概览与单任务诊断接口，同步事件带 `run_id`，便于按任务和运行批次排查问题。
  - 根目录、前端与后端版本统一提升到 `v0.6.1`。
- 测试：
  - 沿用 `v0.6.1-dev.4` 的后端全量测试、前端构建与 NSIS 安装包构建验证。

## v0.6.1-dev.4 (2026-04-28)

- 目标：
  - 继续完善日志中心，让页面基于后端真实任务诊断数据展示当前同步情况，而不是由前端从日志片段中临时推断。
- 结果：
  - 同步事件新增 `run_id`，任务运行开始时生成本次运行 ID，便于按运行批次追踪事件。
  - 后端新增任务概览与单任务诊断接口，统一返回任务配置、运行状态、当前处理文件、最近事件统计和问题事件。
  - 同步日志查询支持按 `run_id` / `run_ids` 过滤，保留任务、状态、搜索等既有过滤能力。
  - 日志中心前端切换为使用后端诊断接口，左侧任务列表、右侧运行概览和问题摘要均使用同一份后端诊断结果。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_event_store.py apps/backend/tests/test_tray_status.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.1-dev.3 (2026-04-28)

- 目标：
  - 将日志中心从全局日志列表重构为面向任务排查的诊断入口。
- 结果：
  - 默认页签改为“任务诊断”，左侧按任务展示状态、最近活动、同步模式和问题数量。
  - 右侧选中任务后显示运行概览：最近运行时间、本次进度、最近事件统计、当前处理文件和最近错误。
  - 新增“问题摘要”，优先聚合失败、冲突、删除失败和取消事件，减少被大量跳过日志淹没。
  - 任务事件时间线只展示当前任务事件，支持全部事件、问题优先、实际变更、跳过记录四类过滤。
  - 系统日志与冲突管理继续保留为辅助排查入口。
- 测试：
  - `npm run build --prefix apps/frontend`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q`
  - `python scripts/build_installer.py --nsis`

## v0.6.1-dev.2 (2026-04-28)

- 目标：
  - 梳理界面中“当前运行”“活跃任务”“最近同步”“启用任务”的显示关系，降低任务状态理解成本。
- 结果：
  - 仪表盘 Header 去掉前端本地假暂停状态，改为根据真实任务状态显示“正在同步 N 个任务 / 当前无运行任务 / 暂无启用任务”。
  - 仪表盘任务区域由“活跃任务”改为“任务概览”，拆分为“当前运行”和“最近同步”两段。
  - 最近同步排序按任务状态时间、`last_run_at`、最近同步日志、任务更新时间依次兜底，不再直接展示创建时间最新的前 4 个任务。
  - 任务页最近同步时间增加 `last_run_at` 兜底，服务重启后不再轻易显示“暂无”。
  - 进度计算改为“已处理/总数”，跳过文件也计入处理进度，修复全跳过成功任务不显示进度的问题。
- 测试：
  - `npm run build --prefix apps/frontend`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q`
  - `python scripts/build_installer.py --nsis`

## v0.6.1-dev.1 (2026-04-28)

- 目标：
  - 修复双向同步 Markdown 上行在云端已更新时仍可能覆盖飞书云文档的问题。
- 结果：
  - Markdown 上行进入覆盖前会按 `sync_links` 的云端基线复核飞书目录中的当前 `modified_time`。
  - 若云端相对本地同步基线已更新且本地也有变化，会跳过上传、记录冲突，并写入同步事件“云端已更新，已阻止本地覆盖”。
  - 若云端已更新但本地内容未变化，会跳过上传并等待后续下载阶段拉取云端版本。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_runner_upload_new_doc.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py apps/backend/tests/test_sync_runner_block_update.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.6.0 release (2026-04-28)

- 目标：
  - 发布 `v0.6.0` 稳定版，交付首次运行/长时间离线恢复同步的无删除补齐机制。
- 结果：
  - 稳定版基于 `v0.6.0-dev.1` 收口：新建任务或距离上次运行超过 48 小时的任务，在常规同步前先执行只新增、不删除的双向补齐。
  - 根目录、前端与后端版本统一提升到 `v0.6.0`。
  - GitHub Release 由稳定 tag 触发 `Release Build` 工作流自动构建 Windows 安装包并上传 `.sha256` 校验文件。
- 测试：
  - 沿用 `v0.6.0-dev.1` 的后端全量测试、前端构建与 NSIS 安装包构建验证。

## v0.6.0-dev.1 (2026-04-28)

- 目标：
  - 将版本推进到 `v0.6.0-dev.1`。
  - 修复新建任务或长时间未运行任务在第一次恢复同步时，因一侧扫描/映射缺失而误判删除的问题。
- 结果：
  - `sync_tasks` 新增 `last_run_at`，并在任务完成后记录运行时间。
  - 任务运行前若 `last_run_at` 为空或距今超过 48 小时，会先执行一轮无删除补齐。
  - 无删除补齐阶段复用现有下载/上传链路，但跳过删除墓碑创建与待删除墓碑执行；完成后再进入常规同步。
  - `SyncTaskResponse` 与前端 `SyncTask` 类型补齐 `last_run_at` 字段。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_task_service.py apps/backend/tests/test_sync_runner.py::test_run_task_performs_additive_reconcile_for_new_task apps/backend/tests/test_sync_runner.py::test_run_task_skips_additive_reconcile_when_recently_run apps/backend/tests/test_sync_runner.py::test_download_additive_mode_does_not_enqueue_cloud_missing_delete -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py apps/backend/tests/test_sync_runner_block_update.py apps/backend/tests/test_sync_task_service.py apps/backend/tests/test_db_session.py apps/backend/tests/test_db.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`

## v0.5.64-dev.1 (2026-04-28)

- 目标：
  - 修复 Markdown 上行调用飞书 `docx/v1/documents/blocks/convert` 偶发 `502 Bad Gateway` 时任务直接失败的问题。
- 结果：
  - `FeishuClient.request_with_retry()` 新增 500/502/503/504 临时服务端错误重试，继续复用 `Retry-After` 与指数退避策略。
  - 保留普通 4xx 错误的快速失败行为，避免掩盖参数、权限等确定性问题。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_feishu_client.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_feishu_client.py -q`
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py`
  - `python scripts/build_installer.py --nsis`

## v0.5.63 release (2026-04-23)

- 目标：
  - 发布 `v0.5.63` 稳定版，交付飞书图片块比例修复。
- 结果：
  - 根目录 `package.json`、前端 `apps/frontend/package.json` 与后端 `apps/backend/pyproject.toml` 版本统一提升到 `v0.5.63 / 0.5.63`。
  - 发布内容基于 `v0.5.63-dev.1`：图片 token 回填时同步写入等比 `width/height`，避免飞书空图片块默认尺寸造成横向拉伸。

## v0.5.63-dev.1 (2026-04-23)

- 目标：
  - 修复目标飞书文档 `JYtPdpNuCoQAyzxJWgRcy8bQnrg` 中插图上传成功但显示比例不正确的问题。
- 结果：
  - `DocxService._replace_image_block()` 支持传入本地图片路径，并在 `replace_image` payload 中写入等比显示尺寸。
  - 新增图片尺寸读取逻辑：优先用 Pillow 读取 PNG/JPEG/WebP 等位图尺寸，SVG 则回退读取 `width/height` 或 `viewBox`。
  - 显示宽度最大限制为 820px，小图保持原宽，大图按比例缩放高度。
  - 现场回填目标文档 37 个图片块尺寸，回查确认 `fig-2-1=820x410`、`fig-3-1=820x547`、其余 16:9 图为 `820x461` 等。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_media_uploader.py apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py -q`

## v0.5.62 release (2026-04-23)

- 目标：
  - 发布 `v0.5.62` 稳定版，交付飞书图片块已创建但前端显示“无法导入该图片”的修复。
- 结果：
  - 根目录 `package.json`、前端 `apps/frontend/package.json` 与后端 `apps/backend/pyproject.toml` 版本统一提升到 `v0.5.62 / 0.5.62`。
  - 发布内容基于 `v0.5.62-dev.1`：Markdown 图片素材上传时显式携带 MIME，并通过 `#local-images-v2` 触发旧 `v1` 修复标记文档重新上传图片 token。

## v0.5.62-dev.1 (2026-04-23)

- 目标：
  - 修复目标飞书文档 `JYtPdpNuCoQAyzxJWgRcy8bQnrg` 中图片块已有 token 但前端无法渲染的问题。
  - 确保《软件设计说明书-V1.4》后续自动上传时，插图素材以飞书可识别的图片 MIME 写入。
- 结果：
  - `MediaUploader.upload_image()` 上传 multipart file 时改为传入三元组 `(filename, bytes, content_type)`，PNG 等图片会显式携带 `image/png`。
  - `sync_runner.py` 将本地图片一次性修复标记从 `#local-images-v1` 升级到 `#local-images-v2`，避免已写入旧标记的同 hash 文档跳过重传。
  - 现场对飞书目标文档 `JYtPdpNuCoQAyzxJWgRcy8bQnrg` 的 37 个图片块重新上传本地 PNG 并回填 token，回查确认 `image_blocks=37`、`with_tokens=37`。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_media_uploader.py apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py -q`

## v0.5.61 release (2026-04-23)

- 目标：
  - 发布 `v0.5.61` 稳定版，交付原目录《软件设计说明书-V1.4》插图上传修复。
- 结果：
  - 根目录 `package.json`、前端 `apps/frontend/package.json` 与后端 `apps/backend/pyproject.toml` 版本统一提升到 `v0.5.61 / 0.5.61`。
  - 发布内容基于 `v0.5.61-dev.1`：含本地图片的 Markdown 不再因超限表格走原生导入丢图，历史同 hash 缺图文档会执行一次块级修复。

## v0.5.61-dev.1 (2026-04-23)

- 目标：
  - 修复原目录《软件设计说明书-V1.4》首次上传或重传后插图仍失败的问题。
  - 处理“超限表格需要导入重建”和“本地相对图片必须块级上传”之间的策略冲突。
- 结果：
  - `sync_runner.py` 新增本地图片检测：Markdown 含可上传本地图片时，即使存在超限表格也不走飞书原生 Markdown 导入重建，改走块级覆盖链路，确保图片通过 `MediaUploader` 上传并回填图片块。
  - 首次创建 Markdown 云端文档仍用导入任务创建空壳/初始文档，但检测到本地图片后会立即执行 `replace_document_content(..., update_mode="full")` 做块级覆盖。
  - 对历史已导入但缺图的同 hash 文档，增加一次性修复标记 `#local-images-v1`：没有该标记时不因 hash 相同跳过，会强制执行一次块级图片修复；成功后写入标记避免后续重复上传。
  - 本地探针确认原目录 `软件设计说明书-V1.4.md` 判定 `has_uploadable_images=True`、`should_reimport=False`。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py -q`

## v0.5.60 release (2026-04-23)

- 目标：
  - 发布 `v0.5.60` 稳定版，交付 Markdown 迁移缺图兜底与《软件设计说明书-V1.4》图片目录补齐。
- 结果：
  - 根目录 `package.json`、前端 `apps/frontend/package.json` 与后端 `apps/backend/pyproject.toml` 版本统一提升到 `v0.5.60 / 0.5.60`。
  - 当前业务文档目录已补齐 `figures/V1.4-GPT-image-2` 37 张 PNG；本地探针确认 `image_paths=37`、`missing_markers=0`。
  - 稳定版基于 `v0.5.60-dev.1` 修复提交发布。

## v0.5.60-dev.1 (2026-04-23)

- 目标：
  - 修复《软件设计说明书-V1.4》迁移目录后，Markdown 图片引用仍指向 `figures/V1.4-GPT-image-2/fig-*.png`，但当前目录缺少该图片子目录，导致飞书上行缺图的问题。
  - 增强 Markdown 普通图片路径解析，避免同类 `fig-数字` 源图迁移后被降级为缺图文本。
- 结果：
  - `docx_service.py` 新增普通 Markdown 图片路径兜底：原始相对路径不存在时，从文件名提取 `fig-2-1` 等图号，并在文档同级 `figures/`、`插图/`、`assets/` 中查找 `fig-2-1.drawio.png` / `fig-2-1.png` 等真实源图。
  - 将历史同步目录中的 `figures/V1.4-GPT-image-2` 37 张 PNG 补回当前《软件设计说明书》目录，保证 `软件设计说明书-V1.4.md` 的原始引用路径也完整可用。
  - 本地探针确认 `软件设计说明书-V1.4.md` 可解析 `image_paths=37`，`missing_markers=0`。
- 测试：
  - `PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_docx_service.py apps/backend/tests/test_sync_runner.py apps/backend/tests/test_sync_runner_upload_new_doc.py -q`

## v0.5.59 release (2026-04-19)

- 目标：
  - 发布 `v0.5.59` 稳定版，交付 Markdown 上行大表格改走飞书原生导入、HTML 内嵌图片上传与同名旧文档清理能力。
- 结果：
  - 根目录 `package.json`、前端 `apps/frontend/package.json` 与后端 `apps/backend/pyproject.toml` 版本统一提升到 `v0.5.59 / 0.5.59`。
  - 发布前已完成真实云端回归，确认需求规格说明书保留原生表格，设计说明书保留原生表格与图片块。
  - 云端同名旧文档已清理，仅保留最新稳定测试文档。

## v0.5.59-dev.4 (2026-04-19)

- 目标：
  - 修复 `算电融合项目软件需求规格说明书-V1.1.md` 这类标准 pipe-table 文档在块级上行时仍被飞书 `1770001 invalid param` 拦截并降级为代码块的问题。
  - 修复大文档改走导入链路后，导入轮询仅等待 10 秒导致程序误判失败的问题。
  - 验证真实业务文档在新策略下既能保留原生表格，也能保留图片块。
- 结果：
  - `docx_service.py` 新增 Markdown 表格超限检测，基于本地实测阈值将 `row_size > 8` 的表格标记为不适合飞书块级建表。
  - `sync_runner.py` 新增“超限表格自动导入重建”策略：检测到此类 Markdown 后，不再调用块级 `replace_document_content()`，而是通过飞书原生 Markdown 导入创建新文档、替换本地映射并删除旧云端文档。
  - 将 `SyncTaskRunner` 的 Markdown 导入轮询默认时长从 10 秒提升到 60 秒，覆盖《软件设计说明书-V1.1》这类大文档的真实导入耗时。
  - `test_docx_service.py` 补充“表格超限检测”单测；`test_sync_runner_upload_new_doc.py` 补充“已存在云端文档时，超限表格自动导入重建并迁移映射”的回归测试。
- 测试：
  - `python -m pytest tests/test_docx_service.py tests/test_sync_runner_upload_new_doc.py tests/test_sync_runner.py tests/test_sync_runner_block_update.py -q`
  - 真实云端验证：
    - `算电融合项目软件需求规格说明书-V1.1.md` 重新导入后生成新文档 `BBPwdaSXSoOkZ8xmf15cjudXnCb`，云端块统计 `table_blocks=1`、`code_blocks=0`。
    - `软件设计说明书-V1.1.md` 重新导入后生成新文档 `ISqmdgXWdoUj18xzhehcCtoBnPb`，云端块统计 `table_blocks=136`、`image_blocks=23`、`code_blocks=0`。

## v0.5.59-dev.3 (2026-04-19)

- 目标：
  - 修复 `算电融合项目软件需求规格说明书-V1.1.md` 上行时仍被飞书 `1770001 invalid param` 拦截的问题。
  - 让带 `FIGURE:x-y` 标记的 HTML 内嵌 `data:image/svg+xml;base64,...` 图片能进入真实图片上传链路，而不是作为普通 HTML 原样传给飞书。
  - 避免 `figures/`、`插图/` 里的源图再次被同步器当作独立附件重复上传并报 `unknown error`。
- 结果：
  - `docx_service.py` 移除表格创建时自动补写的 `table.property.column_width`，保留 `row_size/column_size` 与 `cells` 规整逻辑，避免继续向飞书发送触发 `1770001` 的表格参数。
  - 新增 HTML `<img src=\"data:image/...\">` 预处理：优先按 `FIGURE:x-y` 在本地 `figures/`、`插图/`、`assets/` 中寻找对应 `fig-x-y.drawio.png` 等图片资源；找不到时再把 data URI 落为临时图片文件，并统一走既有图片 placeholder + 飞书图片上传链路。
  - `sync_runner.py` 新增对 `figures/` 与 `插图/` 目录的忽略规则，避免嵌入源图被当普通附件重复上传。
  - `test_docx_service.py` 补充回归测试，覆盖“HTML 内嵌图优先复用本地 PNG”“HTML 内嵌图真实进入图片回填链路”“表格属性不再注入 column_width”。
  - `test_sync_runner.py` 补充回归测试，覆盖 `figures/` / `插图/` 的忽略逻辑。
- 测试：
  - `python -m pytest tests/test_docx_service.py -q`
  - `python -m pytest tests/test_sync_runner.py -q`
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -q`
  - `python -m pytest tests/test_sync_runner_block_update.py -q`
  - 真实云端验证：
    - 直接覆盖上传 `算电融合项目软件需求规格说明书-V1.1.md` 到 `Adw5d3qfJodkA4xvSIxctWAgn2u` 成功；飞书对表格 create 仍返回 `1770001` 时，已自动降级为代码块继续完成整篇替换。
    - 探针文档 `LarkSync图片上传探针-20260419.md` 成功创建并上传到 `DP1Sdgo3IoyXhDx1p9xcOhzYnPd`，云端块统计为 `table_blocks=1`、`image_blocks=1`，证明 HTML 内嵌图已进入真实图片上传链路；探针文档已在验证后删除。

## v0.5.59-dev.2 (2026-04-14)

- 目标：
  - 修复真实 Markdown 文档上行时，大表格在飞书 `create children` 接口返回 `1770001 invalid param` 后会导致整篇替换中止的问题。
- 结果：
  - 回退 `docx_service.py` 中“创建表格时回传 `table.cells`”的尝试，确认飞书并不接受该字段。
  - 保持 table create 请求仅发送 `table.property`，继续清理 `merge_info` 等只读字段。
  - 当单个 table block 创建失败时，新增降级逻辑：把原表格重新渲染为 Markdown，并包装为 fenced code block 后再次创建，避免单个大表格拖垮整篇文档上传。
  - `test_docx_service.py` 补充回归测试，覆盖“表格创建失败后自动降级为代码块”的链路。
  - 使用真实文件 `软件设计说明书.md` 做隔离云端复测：抽样 20x5 表格与整篇文档均上传成功，测试文档分别位于 `_Codex_TableSmoke_20260414-112935` 和 `_Codex_FullRetest_20260414-113156` 目录下。
- 测试：
  - `python -m pytest apps/backend/tests/test_docx_service.py -q`
  - 真实文件隔离复测：
    - 表格烟测文档 `WrgEdywMXocDgvx47UncX9a7nA3`
    - 整篇复测文档 `QHFJdAUySoPzs7xbyQXciwUenvd`

## v0.5.59-dev.1 (2026-04-14)

- 目标：
  - 修复 Markdown 上行到飞书时，遇到表格块创建失败并返回 `1770001 invalid param` 的问题。
- 结果：
  - `docx_service.py` 调整表格块清洗逻辑：创建 table block 时不再移除 `table.cells`。
  - 当转换结果仅包含表格 `children` 与 `row_size/column_size` 时，会按行列自动补出 `table.cells` 矩阵后再请求飞书接口。
  - 保留运行时字段清理逻辑，继续去除 `block_id`、`parent_id`、`children` 与 `merge_info`，避免把服务端返回的只读字段原样回传。
  - `test_docx_service.py` 新增/更新回归测试，覆盖表格块清洗与创建请求 payload。
- 测试：
  - `python -m pytest apps/backend/tests/test_docx_service.py -q`

## v0.5.58 (2026-04-09)

- 发布目标：
  - 修复 Windows 在线升级时“程序已退出，但安装包未被成功拉起”的残留问题，并发布新的稳定版。
- 发布内容：
  - 托盘处理安装请求时，Windows 端改为优先使用 `os.startfile`（ShellExecute）直接启动安装包。
  - 若 ShellExecute 失败，再回退到现有的 PowerShell `Start-Process -LiteralPath` 方案，避免单一路径失效。
  - 安装启动日志现在会记录是否走了 ShellExecute 或 PowerShell 回退路径，便于后续排查现场。
- 发布验证：
  - `python -m pytest tests/test_tray_update_install.py tests/test_system_update_api.py -q`
  - `python scripts/build_installer.py --nsis`
- 发布说明：
  - 稳定版标签为 `v0.5.58`，GitHub Release 资产由 tag 触发的 `Release Build` 工作流自动生成并上传。

## v0.5.58-dev.1 (2026-04-09)

- 目标：
  - 修复自动升级安装包已下载但托盘退出后安装器仍未被成功拉起的问题。
- 结果：
  - `tray_app.py` 新增 Windows 原生安装启动路径，优先通过 `os.startfile` 交给 ShellExecute 直接拉起安装包。
  - 保留 PowerShell `-EncodedCommand` + `Start-Process -LiteralPath` 作为失败兜底。
  - 补充 pytest，覆盖“优先使用 startfile”和“startfile 失败时回退 PowerShell”两类场景。
- 测试：
  - `python -m pytest tests/test_tray_update_install.py tests/test_system_update_api.py -q`

## v0.5.57 (2026-04-09)

- 发布目标：
  - 将 `v0.5.57-dev.1` 和 `v0.5.57-dev.2` 收口为正式稳定版，交付 `download_only` 任务的云端镜像修复与同步模式感知配置优化。
- 发布内容：
  - `download_only` 模式下彻底禁用云端 `_LarkSync_MD_Mirror` 的创建与回写，避免历史 `md_sync_mode` 脏配置触发 forbidden。
  - 设置页、新建任务与任务管理页按同步模式收起不适用的上传/下载配置，减少仅下载和仅上传场景中的误操作。
- 发布验证：
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py -q`
  - `npm run build --prefix apps/frontend`
  - `python scripts/build_installer.py --nsis`
- 发布说明：
  - 稳定版标签为 `v0.5.57`，GitHub Release 资产由 tag 触发的 `Release Build` 工作流自动生成并上传。

## v0.5.57-dev.2 (2026-04-09)

- 目标：
  - 收起 `download_only` / `upload_only` 场景下不适用的前端配置项，避免用户在仅下载任务里继续看到 MD 上传选项。
- 结果：
  - `SettingsPage` 按同步模式区分“本地上行”和“云端下行”配置，禁用方向改为说明文案而非继续显示无效输入控件。
  - `NewTaskModal` 在 `download_only` 下隐藏 MD 上传模式选择，并在创建任务时强制提交 `md_sync_mode=download_only`。
  - `TasksPage` 在 `download_only` 任务中将 MD 模式摘要显示为“不适用（仅下载）”，管理区不再提供 MD 上传模式配置。
- 测试：
  - `npm run build --prefix apps/frontend`

## v0.5.57-dev.1 (2026-04-09)

- 目标：
  - 修复 `download_only` 任务在历史/脏 `md_sync_mode` 配置下仍尝试创建云端 `_LarkSync_MD_Mirror` 的问题。
- 结果：
  - `SyncTaskRunner` 的 Markdown 上传与云端 MD 镜像判定新增 `sync_mode` 保护。
  - 当任务为 `download_only` 时，无论 `md_sync_mode` 是 `enhanced`、空值还是遗留配置，都不会创建或写入云端 MD 镜像目录。
  - 补充回归测试，覆盖 `download_only + md_sync_mode=enhanced` 时仍必须只下载、不回写云端。
- 测试：
  - `python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py -q`

## v0.5.56 (2026-04-09)

- 发布目标：
  - 将 `v0.5.56-dev.1` 的 Windows 在线升级修复收口为正式稳定版，解决“更新包已下载、确认安装后程序退出但安装器未成功启动”。
- 发布内容：
  - Windows 托盘安装器启动链路改为 `powershell.exe -EncodedCommand`。
  - 安装命令改用 `Start-Process -LiteralPath`，兼容中文路径、单引号与特殊字符路径。
  - 新增 `data/logs/update-install.log`，记录安装器启动关键节点，便于复盘现场。
- 发布验证：
  - `python -m pytest tests/test_tray_update_install.py tests/test_system_update_api.py tests/test_larksync_cli.py -q`
  - `python scripts/build_installer.py --nsis`
- 发布说明：
  - 稳定版标签为 `v0.5.56`，GitHub Release Windows 安装包将由 `Release Build` 工作流基于 tag 自动构建并上传。

## v0.5.56-dev.1 (2026-04-08)

- 目标：
  - 修复“更新包已下载，点击确认安装后主程序退出，但安装器没有成功启动”的 Windows 在线升级问题。
- 结果：
  - 托盘侧 Windows 安装器启动链路从明文 `powershell -Command` 切换为 `powershell.exe -EncodedCommand`。
  - 启动命令改用 `Start-Process -LiteralPath`，避免中文路径、单引号或特殊字符路径导致的 PowerShell 解析失败。
  - 新增 `data/logs/update-install.log`，记录“准备启动安装包 / 已调度启动 / 启动失败”，便于后续定位现场问题。
  - 补充托盘回归测试，覆盖编码命令构造和 Windows 启动参数。
- 测试：
  - `python -m pytest tests/test_tray_update_install.py tests/test_system_update_api.py tests/test_larksync_cli.py -q`
- 问题：
  - 当前仅修正 Windows 托盘拉起安装器链路；若仍出现失败，需要结合 `data/logs/update-install.log` 和系统安全软件拦截情况继续排查。

## v0.5.55 (2026-04-08)

- 发布目标：
  - 将 `v0.5.55-dev.1` 到 `v0.5.55-dev.8` 的 CLI/Agent/OpenClaw 增量能力收口为正式稳定版。
- 发布内容：
  - 正式 CLI 已覆盖授权、配置、任务、日志、更新、冲突与目录树等核心能力，并支持 `bootstrap-cache`、`workflow-template*`、`workflow-plan`、`workflow-execute`。
  - 工作流执行器支持步骤区间、失败后继续、JSON 落盘、稳定 `run_id`、恢复执行、跳过已成功步骤，以及 `data/workflows/<run_id>.json` 标准运行记录归档。
  - 新增 `workflow-run-list` / `workflow-run-show` / `workflow-run-prune`，便于 Agent 查询历史执行、读取单次结果和清理旧记录。
  - OpenClaw helper / WSL helper 已与正式 CLI 命令面对齐，可直接复用相同工作流契约。
- 发布验证：
  - `python -m pytest apps/backend/tests/test_larksync_cli.py apps/backend/tests/test_larksync_skill_helper.py apps/backend/tests/test_larksync_wsl_helper.py -q`
  - `python scripts/build_installer.py --nsis`
  - `python scripts/larksync_cli.py workflow-run-list --limit 3`
- 发布说明：
  - 稳定版标签为 `v0.5.55`，GitHub Release Windows 安装包将由 `Release Build` 工作流基于 tag 自动构建并上传。

## v0.5.55-dev.8 (2026-04-08)

- 完成工作流运行记录索引化：`workflow-execute` 每次真实执行都会自动写入 `data/workflows/<run_id>.json`。
- 新增 `workflow-run-list`、`workflow-run-show`、`workflow-run-prune`，便于 Agent 查询执行历史、读取单次结果和清理旧记录。
- 恢复执行逻辑支持仅凭 `--run-id` 自动从标准运行目录恢复，`--resume-from-file` 退化为可选覆盖源。
- 更新 README、CLI 契约、OpenClaw Skill 文档与使用示例，统一推荐运行记录目录方案。
- 验证通过：
  - `python -m pytest apps/backend/tests/test_larksync_cli.py apps/backend/tests/test_larksync_skill_helper.py apps/backend/tests/test_larksync_wsl_helper.py -q`
  - `python scripts/larksync_cli.py workflow-run-list --limit 3`
  - `python scripts/larksync_cli.py workflow-execute --help`

## v0.5.55-dev.7 (2026-04-08)

- 目标：
  - 为工作流执行器补充运行 ID、结果恢复与跳过已成功步骤能力。
- 结果：
  - `workflow-execute` 新增 `run_id`，可为同一条执行链提供稳定标识。
  - 新增 `resume_from_file`，可从上一次 `workflow-execute` 的 JSON 结果恢复 `results/errors`。
  - 新增 `skip_completed`，恢复执行时可直接跳过已成功步骤，避免重复触发已完成动作。
- 测试：
  - `python -m pytest tests/test_larksync_cli.py tests/test_larksync_skill_helper.py tests/test_larksync_wsl_helper.py -q`
  - `python scripts/larksync_cli.py workflow-execute --template daily-cache --run-id demo-run --resume-from-file data\\workflow.json --skip-completed --set "local_path=D:\\Knowledge\\FeishuMirror" --set cloud_folder_token=fld_test`
- 问题：
  - 当前恢复逻辑以单个结果文件为事实来源，还没有做多次 run 的索引管理；后续若要批量审计，需要单独加 run 目录或状态仓库。

## v0.5.55-dev.6 (2026-04-08)

- 目标：
  - 为工作流执行器补充局部重跑、容错执行与结果落盘控制。
- 结果：
  - `workflow-execute` 新增 `from_step` / `to_step`，支持只执行指定步骤区间。
  - 新增 `continue_on_error`，单步失败后可继续执行并在 `errors` 中汇总失败信息。
  - 新增 `output_json_file`，可将整份执行结果落盘为 JSON 供 Agent 审计或二次消费。
- 测试：
  - `python -m pytest tests/test_larksync_cli.py tests/test_larksync_skill_helper.py tests/test_larksync_wsl_helper.py -q`
  - `python scripts/larksync_cli.py workflow-execute --template daily-cache --dry-run --from-step bootstrap --to-step inspect-task --output-json-file data\\workflow.json --set "local_path=D:\\Knowledge\\FeishuMirror" --set cloud_folder_token=fld_test`
- 问题：
  - 当前 `continue_on_error` 仍按线性顺序执行，不会自动跳过对前置失败结果存在强依赖的复杂分支；后续若模板关系图更复杂，需要补显式依赖图。

## v0.5.55-dev.5 (2026-04-08)

- 目标：
  - 让 CLI 不只生成工作流计划，还能顺序执行模板步骤并自动衔接动态输入。
- 结果：
  - `scripts/larksync_cli.py` 新增 `workflow-execute`，支持按模板执行步骤、从上一步 JSON 结果提取动态字段，并提供 `dry_run` 预演模式。
  - 执行结果新增 `execution_log` 与 `results`，便于 Agent 继续编排后续动作。
  - OpenClaw helper / WSL helper 与相关文档同步支持 `workflow-execute`。
- 测试：
  - `python -m pytest tests/test_larksync_cli.py tests/test_larksync_skill_helper.py tests/test_larksync_wsl_helper.py -q`
  - `python scripts/larksync_cli.py workflow-execute --template daily-cache --dry-run --set "local_path=D:\\Knowledge\\FeishuMirror" --set cloud_folder_token=fld_test`
- 问题：
  - 当前 JSON 路径提取实现面向现有模板字段，若后续模板引入更复杂的嵌套或过滤表达式，需要再扩展路径语法。

## v0.5.55-dev.4 (2026-04-08)

- 目标：
  - 让 Agent 在拿到模板定义后，能直接生成带参数的执行计划，而不是自己拼命令。
- 结果：
  - `scripts/larksync_cli.py` 新增 `workflow-plan`，支持按模板名、入口类型和 `--set key=value` 参数渲染执行计划。
  - 计划输出包含 `values`、`missing_inputs`、`plan.steps[*].argv`、`command_line`、`dynamic_inputs`，可区分“现在可执行”和“需等待上一步结果”的步骤。
  - OpenClaw helper / WSL helper 同步支持 `workflow-plan`，README、CLI 契约文档和 Agent runbook 补充模板实例化示例。
- 测试：
  - `python -m pytest tests/test_larksync_cli.py tests/test_larksync_skill_helper.py tests/test_larksync_wsl_helper.py -q`
  - `python scripts/larksync_cli.py workflow-plan --template daily-cache --entrypoint helper --set "local_path=D:\\Knowledge\\FeishuMirror" --set cloud_folder_token=fld_test --set download_time=02:30`
- 问题：
  - 无阻塞问题。

## v0.5.55-dev.3 (2026-04-08)

- 目标：
  - 为 Agent 增加“先发现模板、再执行命令”的标准工作流模板能力。
- 结果：
  - `scripts/larksync_cli.py` 新增 `workflow-template-list` 与 `workflow-template`，内置 `daily-cache`、`refresh-cache`、`conflict-audit` 三类模板，输出包含 `entrypoints`、`inputs`、`steps`、`branching`。
  - OpenClaw helper / WSL helper 同步支持模板命令，便于在 WSL 或 Skill 场景先取模板再执行。
  - README、CLI 契约文档、OpenClaw Skill 文档改为补充模板发现流程。
- 测试：
  - `python -m pytest tests/test_larksync_cli.py tests/test_larksync_skill_helper.py tests/test_larksync_wsl_helper.py -q`
  - `python scripts/larksync_cli.py workflow-template-list`
  - `python scripts/larksync_cli.py workflow-template --template daily-cache`
- 问题：
  - 无阻塞问题。

## v0.5.55-dev.2 (2026-04-07)

- 目标：
  - 为 Agent/Skill 增加可重入的首次缓存初始化命令，并沉淀正式 CLI 契约文档。
- 结果：
  - `scripts/larksync_cli.py` 新增 `bootstrap-cache`，可区分 `blocked_backend_unreachable`、`needs_oauth`、`needs_drive_permission`、`configured` 四类阶段，并返回 `next_step` 供 Agent 直接分支。
  - OpenClaw helper / WSL helper 同步支持 `bootstrap-cache`。
  - 新增 `docs/CLI_AGENT_CONTRACT.md`，统一 JSON 包装、退出码、推荐工作流与 `bootstrap-cache` 字段契约；OpenClaw 相关文档改为优先推荐该命令。
- 测试：
  - `python -m pytest tests/test_larksync_cli.py tests/test_larksync_skill_helper.py tests/test_larksync_wsl_helper.py -q`
  - `python scripts/larksync_cli.py bootstrap-cache --help`
  - `python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py bootstrap-cache --help`
- 问题：
  - 无阻塞问题。

## v0.5.55-dev.1 (2026-04-07)

- 目标：
  - 将 LarkSync 核心能力统一封装为可供 Agent 调用的正式 CLI，并让 OpenClaw Skill 复用同一命令面。
- 结果：
  - 新增 `scripts/larksync_cli.py`，统一提供 `check`、`auth-status`、`config-get/config-set`、`task-*`、`drive-tree`、`update-*`、`conflict-*`、`logs-*`、`bootstrap-daily` 等命令。
  - OpenClaw `larksync_skill_helper.py` 改为兼容包装层，底层直接复用正式 CLI；保留 `create-task` / `run-task` 旧命令别名。
  - `larksync_wsl_helper.py` 同步扩展命令识别列表，兼容新的 CLI 子命令。
  - README 与 OpenClaw 相关文档补充正式 CLI 入口和调用示例。
- 测试：
  - `python -m pytest tests/test_larksync_cli.py tests/test_larksync_skill_helper.py tests/test_larksync_wsl_helper.py -q`
  - `python scripts/larksync_cli.py --help`
  - `python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py --help`
- 问题：
  - 无阻塞问题。

## v0.5.54-release (2026-04-07)

- 目标：
  - 发布 `v0.5.54` 稳定版本，修复“下载完成后点击安装更新报 Failed to fetch”。
- 包含内容：
  - `v0.5.54-dev.1`：托盘处理安装请求新增最小成熟期，避免后端过早退出导致前端安装请求中断。
- 发布动作：
  - 版本号收敛为稳定版 `v0.5.54`（root/frontend/backend）。
  - `CHANGELOG.md` 新增 `release: v0.5.54` 记录。
  - 构建 Windows NSIS 安装包并推送 `v0.5.54` tag 触发 GitHub Release。

## v0.5.54-dev.1-safe-update-install-race (2026-04-07)

- 目标：
  - 修复“已下载更新后点击安装”时前端出现 `Failed to fetch` 的竞态问题。
- 变更：
  - 托盘读取安装请求时保留 `created_at`，兼容旧请求文件缺省该字段。
  - 托盘仅在安装请求创建超过 2 秒后才真正退出并启动安装包，确保 `/system/update/install` 能先返回成功响应。
  - 新增回归测试覆盖“新请求先跳过、成熟请求再执行”。
- 测试：
  - `python -m pytest tests/test_system_update_api.py tests/test_tray_update_install.py tests/test_update_service.py tests/test_update_scheduler.py -q`
- 问题：
  - 无阻塞问题。

## v0.5.52-release (2026-03-11)

- 目标：
  - 发布 `v0.5.52` 稳定版本并产出新的 Windows 安装包。
- 包含内容：
  - `v0.5.52-dev.1`：自动更新下载完成后新增“确认安装”安全流程，由托盘退出当前应用并启动安装程序。
- 发布动作：
  - 版本号收敛为稳定版 `v0.5.52`（root/frontend/backend）。
  - `CHANGELOG.md` 新增 `release: v0.5.52` 记录。
  - 计划构建 Windows NSIS 安装包并推送 `v0.5.52` tag 触发 GitHub Release。

## v0.5.52-dev.1-safe-update-install (2026-03-11)

- 目标：
  - 为自动更新增加“确认后安装”的安全流程，避免下载完成后仍需手动去文件夹双击安装包。
- 变更：
  - 后端新增安装请求接口：下载完成后可写入待安装请求。
  - 托盘轮询新增安装请求处理：检测到请求后退出自身与后端，并拉起安装包。
  - 设置页新增“安装已下载更新”入口；下载完成后会弹确认框，可直接进入安装流程。
- 验证：
  - 待本轮后端 pytest 与前端构建验证。

## v0.5.51-release (2026-03-11)

- 目标：
  - 发布 `v0.5.51` 稳定版本，修复旧客户端自动更新报“缺少 sha256 校验信息”。
- 包含内容：
  - `v0.5.51-dev.1`：Release 正文追加安装包 sha256 表，并上传 `.sha256` 校验资产，兼容 `v0.5.49` 等旧版更新器。
- 发布动作：
  - 版本号收敛为稳定版 `v0.5.51`（root/frontend/backend）。
  - `CHANGELOG.md` 新增 `release: v0.5.51` 记录。
  - 计划构建 Windows NSIS 安装包并推送 `v0.5.51` tag 触发 GitHub Release。

## v0.5.51-dev.1-release-checksum-compat (2026-03-11)

- 目标：
  - 修复旧客户端自动更新无法识别 GitHub `asset.digest`，导致升级到 `v0.5.50` 时提示“缺少 sha256 校验信息”。
- 根因：
  - `v0.5.49` 及更老客户端不读取 GitHub Release asset 的 `digest` 字段，只支持 `.sha256` 资产或 Release 正文中的哈希文本。
  - `v0.5.50` Release 仅上传了安装包本体，没有额外 `.sha256` 文件，正文也未包含安装包 sha256，因此旧客户端无法完成校验。
- 变更：
  - `scripts/release_notes.py`
    - 新增 `--asset` 参数，可对发布产物计算 sha256 并追加到 Release 正文“安装包校验”表。
  - `.github/workflows/release-build.yml`
    - Windows/macOS 发布任务在构建后自动生成 `.sha256` 资产；
    - 上传 Release 资产时一并附带 `.sha256`；
    - 生成 Release Notes 时带入安装包路径，把 sha256 写进正文。
  - `apps/backend/tests/test_release_notes.py`
    - 新增 Release 正文 checksum 表与资产哈希收集回归测试。
- 验证：
  - `python -m pytest tests/test_release_notes.py tests/test_release.py -q`（工作目录：`apps/backend`，12 passed）

## v0.5.50-release (2026-03-11)

- 目标：
  - 发布 `v0.5.50` 稳定版本并产出新的 Windows 安装包。
- 包含内容：
  - `v0.5.50-dev.1`：自动更新校验链路补齐三层来源，修复缺少 sha256 时下载被阻断。
  - `v0.5.50-dev.2`：发布说明生成器支持无 `release:` 标记回退归档。
  - `v0.5.50-dev.3`：修复非 Markdown 文件多次上传后飞书侧持续累积同名重复文件。
- 发布动作：
  - 版本号收敛为稳定版 `v0.5.50`（root/frontend/backend）。
  - `CHANGELOG.md` 新增 `release: v0.5.50` 记录。
  - 计划构建 Windows NSIS 安装包并推送 `v0.5.50` tag 触发 GitHub Release。

## v0.5.50-dev.3-sync-upload-dedup (2026-03-11)

- 目标：
  - 修复本地反复生成/修改同一 PDF 等非 Markdown 文件时，飞书目录不断新增同名副本的问题。
- 根因：
  - 非 MD 文件上传链路始终调用 `files/upload_all` / 分片上传创建新云端文件，但上传成功后只更新本地 `sync_links` 到新 token，没有回收旧 token 对应文件。
  - 因此同一路径每次内容变化都会在飞书侧留下历史副本，看起来像“重复上传未生效去重”。
- 变更：
  - `apps/backend/src/services/sync_runner.py`
    - 非 MD 文件上传成功后新增旧云端副本清理逻辑；
    - 优先删除该本地路径上一次映射的旧 `cloud_token`；
    - 并在目标云端目录中按同名文件补扫，清理历史残留重复副本，仅保留最新上传结果。
  - `apps/backend/tests/test_sync_runner_upload_new_doc.py`
    - 新增回归测试，覆盖“再次上传 PDF 后应清理旧 token 与同名历史副本”。
- 验证：
  - `python -m pytest tests/test_sync_runner_upload_new_doc.py -q`（工作目录：`apps/backend`，11 passed）
  - `python -m pytest tests/test_sync_runner.py -q`（工作目录：`apps/backend`，24 passed）

## v0.5.48-release (2026-03-06)

- 目标：
  - 发布 `v0.5.48` 稳定版本并输出可下载安装包。
- 包含内容：
  - `v0.5.48-dev.1`：修复 CI 中 PyInstaller 入口脚本缺失导致的 Release 构建失败。
- 发布动作：
  - 版本收敛为稳定版 `v0.5.48`（root/frontend/backend）。
  - `CHANGELOG.md` 新增 `release: v0.5.48` 记录。
- 验证：
  - `python scripts/build_installer.py --nsis`（通过，生成 `dist/LarkSync-Setup-v0.5.48.exe`）

## v0.5.48-dev.1-build-entrypoint-fix (2026-03-06)

- 目标：
  - 修复 GitHub Actions Windows Release 构建失败：`ERROR: script .../LarkSync.pyw not found`。
- 根因：
  - `scripts/larksync.spec` 将 PyInstaller 入口硬编码为根目录 `LarkSync.pyw`，但该文件未被 Git 跟踪，CI checkout 后缺失。
- 变更：
  - 新增受版本控制入口：`apps/tray/launcher.py`（保留 `--backend` 子进程逻辑，兼容 `BackendManager` 的 frozen 启动方式）。
  - 更新 `scripts/larksync.spec`：
    - 优先使用 `apps/tray/launcher.py`；
    - 若不存在则回退 `LarkSync.pyw`（兼容本地旧环境）。
  - 更新 `scripts/build_installer.py`：
    - 新增 `_resolve_entry_script()`，统一入口解析逻辑；
    - `_generate_spec()` 改为使用解析后的入口路径。
  - 测试补充：`apps/backend/tests/test_build_installer.py`
    - 新增入口解析优先级、回退、缺失报错三个用例。
- 验证：
  - `python -m pytest tests/test_build_installer.py`（工作目录：`apps/backend`，6 passed）
  - `python scripts/build_installer.py --nsis --skip-frontend`（通过，生成 `dist/LarkSync-Setup-v0.5.47.exe`）

## v0.5.47-release (2026-03-06)

- 目标：
  - 发布 `v0.5.47` 稳定版本，并同步产出 Windows 安装包用于 GitHub Release。
- 包含内容：
  - `v0.5.47-dev.1`：权限不足提示高对比度修复（主页面 + 新建任务弹窗）。
  - `v0.5.47-dev.2`：Docx blocks 列表分页参数从 `500` 调整到 `200`，修复飞书 400 报错并补回归测试。
- 发布动作：
  - 版本号收敛为稳定版 `v0.5.47`（root/frontend/backend）。
  - `CHANGELOG.md` 增加 `release: v0.5.47` 记录。
- 验证：
  - `python scripts/build_installer.py --nsis`（通过，生成 `dist/LarkSync-Setup-v0.5.47.exe`）

## v0.5.47-dev.2-docx-list-blocks-page-size-fix (2026-03-06)

- 目标：
  - 修复用户侧同步时报错：`GET /docx/v1/documents/{id}/blocks?page_size=500` 返回 `400 Bad Request`。
- 根因：
  - `DocxService.list_blocks()` 使用了过大的分页参数 `page_size=500`，超出飞书接口可接受范围。
- 变更：
  - `apps/backend/src/services/docx_service.py`
    - 将块列表分页参数从 `500` 下调为 `200`（安全值）。
  - `apps/backend/tests/test_docx_service.py`
    - 新增 `test_list_blocks_uses_safe_page_size_and_paginates`，校验分页参数与翻页行为。
- 验证：
  - `python -m pytest tests/test_docx_service.py`（工作目录：`apps/backend`，35 passed）

## v0.5.47-dev.1-permission-alert-contrast (2026-03-06)

- 目标：
  - 修复“权限不足”提示在浅色主题下文字对比度不足、可读性差的问题。
- 变更：
  - `apps/frontend/src/App.tsx`
    - 调整主页面 Drive 权限告警卡片的背景、边框与文字配色，正文改为高对比度文本。
    - 强化“重新授权飞书”按钮样式，避免与背景色混在一起。
  - `apps/frontend/src/components/NewTaskModal.tsx`
    - 调整任务弹窗内权限不足提示块的标题/正文/链接颜色，对比度与层级更清晰。
- 验证：
  - `npm run build`（工作目录：`apps/frontend`，通过）

## v0.5.46-onboarding-auth-back-navigation (2026-03-06)

- 目标：
  - 修复首次授权场景中 OAuth 参数填写错误后，界面停留在“连接飞书”步骤且无法返回重配的问题。
- 根因：
  - `OnboardingWizard` 的步骤由 `oauthConfigured` 直接推导，Step 2 的“返回上一步”仅执行页面刷新，状态仍会回到 Step 2。
- 变更：
  - `apps/frontend/src/components/OnboardingWizard.tsx`
    - 引入可控步骤状态（`currentStep`），支持用户从 Step 2 直接回退到 Step 1 修改 OAuth 配置。
    - 保存 OAuth 配置成功后自动前进到 Step 2，减少重复操作。
    - Step 1 自动回填已保存的 `auth_client_id`，便于排错重试。
    - Step 2 增加“参数填错可回退重配”提示文案。
- 验证：
  - `npm run build`（工作目录：`apps/frontend`，通过）
  - `python scripts/build_installer.py --nsis`（通过，生成 `dist/LarkSync-Setup-v0.5.46.exe`）

## v0.5.45-openclaw-skill-scan-hardening (2026-02-28)

- 目标：
  - 降低 OpenClaw Skill 被 ClawHub Security 误判为 suspicious 的概率，去掉高风险“自安装/自启动”模式。
- 变更：
  - `integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py`
    - 移除依赖自动安装、WSL 本地后端自动拉起、`PYTHONPATH` 净化子进程链路。
    - 改为纯 Python 实现：读取 `/proc/net/route` 与 `/etc/resolv.conf` 做地址诊断。
    - 直接加载 `larksync_skill_helper.py` 执行，避免额外子进程转发。
  - `apps/backend/tests/test_larksync_wsl_helper.py`
    - 删除旧的自动兜底相关测试，补充 `/proc/net/route` 解析测试。
  - OpenClaw 文档：
    - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/OPENCLAW_AGENT_GUIDE.md`
    - `docs/OPENCLAW_SKILL.md`
    - `docs/USAGE.md`
    - `README.md`
    - 统一改为“只诊断 + 安全转发，不自动安装依赖、不自动拉起后端”。
- 验证：
  - `python -m pytest apps/backend/tests/test_larksync_skill_helper.py apps/backend/tests/test_larksync_wsl_helper.py`（17 passed）
- 发布：
  - 下次 ClawHub 发布示例版本提升为 `0.1.6`。

## v0.5.44-openclaw-wsl-pythonpath-sanitization (2026-02-24)

- 目标：
  - 修复 OpenClaw 在 WSL 场景下自动拉起本地后端失败（`pydantic_core` 导入异常）的问题。
- 根因：
  - WSL helper 启动链路未净化 `PYTHONPATH`，混入了其他 Python 版本的 `site-packages`，导致后端子进程导入二进制扩展失败。
- 变更：
  - `integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py`
    - 新增 `_sanitize_pythonpath()` 与 `_build_runtime_env()`。
    - 依赖安装 `_install_backend_requirements()` 改为使用净化后的环境。
    - 本地后端启动 `_build_local_backend_env()` 改为基于净化环境构建。
  - `apps/backend/tests/test_larksync_wsl_helper.py`
    - 新增 `PYTHONPATH` 净化与运行时环境净化测试。
- 验证：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/backend/tests/test_larksync_wsl_helper.py -q`（11 passed）
  - `python integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py check`（模拟 WSL，自动拉起后端成功，返回 `ok=true`）
  - `python -m py_compile integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py`（通过）
- 发布：
  - 首次发布尝试命中 ClawHub 限流（`Rate limit exceeded`），退避后重试成功。
  - `clawhub publish . --slug larksync-feishu-local-cache --name "LarkSync Feishu Local Cache" --version 0.1.5 --changelog "fix(wsl-runtime): sanitize pythonpath for autonomous local backend startup"`
  - 发布成功：`larksync-feishu-local-cache@0.1.5`，versionId=`k97a3800mtwf74j1ra8ejkf63x81rhmp`
  - 平台状态：安全扫描进行中（短暂 hidden），扫描完成后自动恢复可见。

## v0.5.44-openclaw-agent-runbook (2026-02-23)

- 目标：
  - 给 OpenClaw 代理提供“可直接执行”的使用说明，避免仅有人类视角文档导致代理流程不一致。
- 变更：
  - 新增 `integrations/openclaw/skills/larksync_feishu_local_cache/OPENCLAW_AGENT_GUIDE.md`
    - 覆盖代理默认 SOP（check -> bootstrap -> run）、首次 OAuth 边界、WSL 无人值守兜底、错误处理、用户反馈模板。
  - 入口链接补充：
    - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - `docs/OPENCLAW_SKILL.md`
    - `docs/USAGE.md`
- 验证：
  - 文档路径与链接均在仓库内可解析；
  - 与现有 helper 行为保持一致（未引入新命令分支）。
- 发布：
  - `clawhub publish . --slug larksync-feishu-local-cache --name "LarkSync Feishu Local Cache" --version 0.1.4 --changelog "feat(wsl-agent): autonomous WSL fallback runtime + agent runbook"`
  - 发布成功：`larksync-feishu-local-cache@0.1.4`，versionId=`k97ab35791c2vkmpdfpvfavmxd81pxbh`
  - 平台状态：安全扫描进行中（短暂 hidden），扫描完成后自动恢复可见。

## v0.5.44-openclaw-wsl-autonomous-runtime (2026-02-23)

- 目标：
  - 支持 OpenClaw 在 WSL 下“拉代码后自动运行”场景，尽量减少人工介入（后端启动、依赖与凭证持久化）。
- 变更：
  - `integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py`
    - 新增运行时参数解析：`--no-auto-start-local-backend`、`--no-auto-install-backend-deps`。
    - WSL 未探测到可达 `:8000` 时，默认自动在当前 WSL 启动本地后端（`localhost:8000`）。
    - 本地缺少后端依赖时，默认自动执行 `pip install -r apps/backend/requirements.txt`。
    - 自动启动本地后端时，默认注入：
      - `LARKSYNC_TOKEN_STORE=file`
      - `LARKSYNC_TOKEN_FILE=data/token_store_wsl.json`
      - `LARKSYNC_AUTH_REDIRECT_URI=http://localhost:8000/auth/callback`
  - `apps/backend/src/core/security.py`
    - 新增 `FileTokenStore`，支持 `token_store=file`（文件持久化 token，`chmod 600` 尝试加固权限）。
    - `get_token_store()` 新增 `file` 分支。
  - 新增/更新测试：
    - `apps/backend/tests/test_larksync_wsl_helper.py`：补充运行时选项解析与本地后端环境构造测试。
    - `apps/backend/tests/test_security.py`：新增 `FileTokenStore` 读写、清理与 `get_token_store(file)` 测试。
  - 文档更新：
    - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - `docs/OPENCLAW_SKILL.md`
    - `docs/USAGE.md`
    - 明确 WSL 无人值守兜底行为与可关闭开关。
- 验证：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/backend/tests/test_larksync_wsl_helper.py -q`（9 passed）
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/backend/tests/test_larksync_skill_helper.py -q`（10 passed）
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_security.py -q`（5 passed，工作目录 `apps/backend`，并清空 `PYTHONPATH`）
  - `python -m py_compile integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py apps/backend/src/core/security.py`（通过）

## v0.5.44-wsl-bridge-default-bind-fix (2026-02-23)

- 目标：
  - 修复“OpenClaw 在 WSL 中仍无法访问 Windows 侧 LarkSync :8000”的默认可用性问题，避免依赖手动设置环境变量。
- 变更：
  - `apps/tray/config.py`
    - Windows 默认后端绑定地址改为 `0.0.0.0`（原为 `127.0.0.1`），保证 WSL 可通过宿主机地址连接。
    - 托盘本机访问地址继续使用 `127.0.0.1`（`BACKEND_CLIENT_HOST`），避免本机调用落到不可路由地址。
    - 保留 `LARKSYNC_BACKEND_BIND_HOST` / `LARKSYNC_BACKEND_CLIENT_HOST` 覆盖能力。
  - `integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py`
    - 全部地址不可达时的排查提示更新为：优先检查是否手动把 `LARKSYNC_BACKEND_BIND_HOST` 设回了 `127.0.0.1`。
  - 文档同步：
    - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - `docs/OPENCLAW_SKILL.md`
    - `docs/USAGE.md`
    - 统一说明“Windows 默认已支持 WSL 访问；仅在手动改回 loopback 时需调整配置”。
  - 新增测试：
    - `apps/backend/tests/test_tray_config.py`
    - 覆盖 Windows/非 Windows 默认绑定、bind/client env 覆盖逻辑。
- 验证：
  - `python scripts/sync_feishu_docs.py`（通过；入口页未发现 zip，仅更新清单）
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/backend/tests/test_tray_config.py -q`（4 passed）
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/backend/tests/test_backend_manager.py -q`（3 passed）
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/backend/tests/test_larksync_wsl_helper.py -q`（6 passed）

## v0.5.44-openclaw-skill-wsl-helper (2026-02-23)

- 目标：
  - 解决 OpenClaw 在 WSL 中调用 LarkSync 时的宿主地址探测不稳定问题，明确区分“脚本逻辑”与“服务未监听”。
- 变更：
  - 新增 `integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_wsl_helper.py`
    - 同时探测 `localhost`、`host.docker.internal`、default gateway、`/etc/resolv.conf` nameserver。
    - 输出逐项诊断（连接状态/health 状态/延迟/错误详情）。
    - WSL 下未指定 `--base-url` 时自动选择可达地址；若全部不可达，明确提示先启动 Windows 侧 LarkSync。
    - 手动远程 `--base-url` 自动补 `--allow-remote-base-url`，兼容安全策略。
  - 新增测试 `apps/backend/tests/test_larksync_wsl_helper.py`
    - 覆盖 gateway/resolv 解析、远程 allow flag 注入与可达地址选择逻辑。
  - 文档更新：
    - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - `docs/OPENCLAW_SKILL.md`
    - `docs/USAGE.md`
    - 增加 WSL 诊断与执行示例，发布示例版本升级至 `0.1.3`。

## v0.5.44-openclaw-skill-bilingual-intro (2026-02-23)

- 目标：
  - 修复 OpenClaw Skill 介绍“仅中文”的可读性问题，补充英文介绍以适配 ClawHub 国际用户与英文 Agent。
- 变更：
  - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - frontmatter `description` 调整为中英双语。
    - 新增 `English Overview` 与英文示例意图。
  - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - 新增 `English Overview` 区块。
  - 文档发布示例同步：
    - `docs/OPENCLAW_SKILL.md`
    - `docs/USAGE.md`
    - ClawHub 发布示例版本升级为 `0.1.2`。

## v0.5.44-openclaw-skill-security-hardening (2026-02-23)

- 目标：
  - 修复 ClawHub/VirusTotal 将 `larksync-feishu-local-cache` 标记为 suspicious 的主要触发点（helper 可被引导请求任意远程 `base-url`）。
  - 保留远程联调能力，但改为显式高风险开关，默认走本机地址。
- 变更：
  - `integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py`
    - 新增 `validate_base_url()` 与 loopback 校验逻辑。
    - 默认仅允许 `localhost/127.0.0.1/::1`。
    - 新增 `--allow-remote-base-url` 显式开关，远程地址需用户主动启用。
  - `apps/backend/tests/test_larksync_skill_helper.py`
    - 新增 base-url 安全校验用例（默认拒绝远程、显式开关放行、非法 scheme 拒绝）。
  - 文档同步：
    - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - `docs/OPENCLAW_SKILL.md`
    - `docs/USAGE.md`
    - 补充安全说明与远程场景命令示例；发布命令示例升级为 Skill `0.1.1`。
- 验证：
  - `python scripts/sync_feishu_docs.py`（已执行，入口页面未发现 zip，清单已更新）
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/backend/tests/test_larksync_skill_helper.py -q` 通过（10 passed）

## v0.5.44-openclaw-clawhub-compliance (2026-02-23)

- 目标：
  - 按 ClawHub 官方要求校正 Skill frontmatter 与上架命令格式，避免发布时因格式问题被拒。
- 变更：
  - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - `metadata` 从 YAML 多行结构改为单行 JSON 对象（符合官方 parser 约束）。
  - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
  - `docs/OPENCLAW_SKILL.md`
  - `docs/USAGE.md`
    - 上架流程统一为：`clawhub login` -> `clawhub sync --root . --dry-run` -> `clawhub publish . --slug --name --version --changelog`。
    - 术语统一为 `ClawHub`。
- 验证：
  - 已安装 `clawhub` CLI（v0.7.0）。
  - 本机发布被登录态阻塞：`clawhub whoami/sync/publish` 均返回 `Not logged in`。

## v0.5.44-openclaw-skill-copywriting-polish (2026-02-23)

- 目标：
  - 提升 OpenClaw Skill 对外介绍的吸引力，让用户和其他 Agent 更容易理解“为什么要装、装了有什么收益”。
- 变更：
  - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - 新增价值主张、Before/After、适用人群、30 秒上手入口。
  - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - frontmatter 描述改为更聚焦“降调用频率/降 token 成本”。
    - 新增“价值主张”区块，明确对用户/Agent 的直接收益。
  - `docs/OPENCLAW_SKILL.md`
    - 增加开场“为什么有吸引力”的说明，强化上架页叙事。

## v0.5.44-openclaw-skill-local-cache (2026-02-23)

- 目标：
  - 基于 LarkSync 现有能力，产出可上架 clwuhub 的 OpenClaw Skill，默认走低频下行同步，降低飞书 API/token 消耗。
  - 输出一份本地规范规划文档，并按规划完成交付。
- 本地规划文档（不入 Git）：
  - `docs/local_specs/openclaw_skill_plan_larksync.md`
- 变更：
  - 新增 Skill 包：
    - `integrations/openclaw/skills/larksync_feishu_local_cache/SKILL.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/README.md`
    - `integrations/openclaw/skills/larksync_feishu_local_cache/scripts/larksync_skill_helper.py`
  - 新增公共文档：
    - `docs/OPENCLAW_SKILL.md`（定位、默认策略、命令、上架步骤）
  - 更新现有文档：
    - `README.md` 增加 OpenClaw 集成说明与文档入口
    - `docs/USAGE.md` 增加 OpenClaw Skill 专章
  - 新增测试：
    - `apps/backend/tests/test_larksync_skill_helper.py`
    - 覆盖时间校验、下载配置 payload、任务 payload、模式映射与非法参数处理

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

## v0.5.53-dev.1 (2026-04-07)

- 目标：修复本地对云端同步时误上传 Office 临时文件与系统噪音文件的问题。
- 结果：`SyncTaskRunner` 新增本地临时文件判定，上传事件与启动补扫都会跳过 `~$` 前缀、`.tmp/.temp/.swp/.part/.crdownload` 后缀、`Thumbs.db` / `desktop.ini` / `.DS_Store` 等文件；补充 watcher 与补扫路径的回归测试。
- 测试：`python -m pytest tests/test_sync_runner.py tests/test_sync_runner_upload_new_doc.py tests/test_watcher.py tests/test_watcher_filters.py`（apps/backend，41 passed）。
- 问题：`scripts/sync_feishu_docs.py` 已执行，但入口页当前未解析到 zip 文档链接，仅刷新了 `docs/feishu/_manifest.json` 的检查结果，后续如需依赖最新 zip 文档需单独跟进页面结构变更。

## v0.5.53 (2026-04-07)

- 目标：发布稳定版，交付“忽略本地临时文件误上传”的修复用于在线升级。
- 结果：稳定版收敛 `v0.5.53-dev.1` 的上传过滤修复，发布版本号统一为 `v0.5.53`，用于触发 Windows Release 构建与自动更新分发。
- 测试：沿用 `v0.5.53-dev.1` 回归结果；发布前额外执行安装包本地构建验证。
- 问题：等待 GitHub Actions 完成 Release Build 后，安装包与 `.sha256` 才会正式出现在 Release 资产中。

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

## v0.5.49 (2026-03-07)

- 目标：修复“本地持续编辑同一文档时重复上传到云端”问题。
- 结果：`SyncTaskRunner` 的本地上传队列由路径集合升级为“路径+最后变更时间”，周期上传仅消费超过静默窗口（2s）的文件；持续编辑期间会合并为一次稳定后上传。
- 测试：`python -m pytest tests/test_watcher.py tests/test_watcher_filters.py tests/test_sync_runner.py`（apps/backend，28 passed）。
- 问题：暂无阻塞问题。

## v0.5.50-dev.1 (2026-03-07)

- 目标：修复自动更新下载阶段误报“缺少 sha256 校验信息”。
- 结果：`UpdateService` 新增 GitHub Release 资产 `digest` 字段解析（`sha256:...`），并补充“从 Release 正文按目标安装包名解析 sha256”的回退路径；缺少 `.sha256` 附件时仍可安全校验下载包。
- 测试：`python -m pytest tests/test_update_service.py tests/test_system_update_api.py tests/test_update_scheduler.py -q`（apps/backend，14 passed）。
- 问题：暂无阻塞问题。

## v0.5.50-dev.2 (2026-03-08)

- 目标：修复“发布页更新明细为空”与 changelog 最新变更可读性差的问题。

- 结果：`scripts/release_notes.py` 增加回退策略：当目标版本缺失 `release:` 标记时，按该版本首条记录作为锚点继续归档；并将 `CHANGELOG.md` 最新条目统一置顶，避免版本顺序错位导致发布说明误判。

- 测试：`python -m pytest apps/backend/tests/test_release_notes.py -q`。

- 问题：暂无阻塞问题。
  
  ## v0.6.4-dev.1 (2026-04-29)

- 目标：
  
  - 修复本地新建 Markdown 首次创建飞书文档后，被同一轮双向上传误判为“云端已更新”冲突的问题。

- 结果：
  
  - `SyncTaskRunner` 在创建或导入重建云端文档成功后，会立即把 `local_hash`、`local_mtime`、`local_size`、`cloud_mtime`、`cloud_revision` 和 `updated_at` 写回 `sync_links`。
  - `imported_doc` 分支不再被“内容未变化 / 本地未变更”提前短路，避免首次创建后的自冲突。

- 测试：
  
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_runner_upload_new_doc.py apps/backend/tests/test_sync_runner.py -p pytest_asyncio.plugin -q`

- 问题：
  
  - 当前安装目录里的正式版仍是 `v0.6.2`，要实际带上这次修复还需要后续重新安装或发布新版本。

## v0.6.5-dev.1 (2026-04-30)

- 目标：
  
  - 修复 Windows 静默更新在已下载完成后卡在“安装程序未返回接管确认”的问题。

- 结果：
  
  - `LarkSyncTray._schedule_installer_launch()` 启动静默安装 helper 时去掉了 `DETACHED_PROCESS`，保留 `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`。
  - 回归测试明确约束静默 helper 不能再带 `DETACHED_PROCESS`，避免 PowerShell helper 无法写出 `install-handoff.json` 导致 15 秒接管超时。

- 测试：
  
  - `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONPATH='apps/backend'; python -m pytest apps/backend/tests/test_tray_update_install.py -p pytest_asyncio.plugin -q`

- 问题：
  
  - 当前安装目录里的正式版仍是 `v0.6.3`，要实际带上这次修复仍需重新安装或发布新版本。
    
    ## v0.6.5-dev.2 (2026-04-30)

- 目标：把日志中心从任务级聚合改为运行级查看，解决历史错误长期挂在同一任务下、无法区分每次执行的问题。

- 结果：
  
  - 后端诊断接口新增运行摘要聚合，按 `run_id` 返回最近运行列表和指定运行诊断。
  - 任务概览改为默认只反映最近一次运行，不再把历史失败累计成当前任务问题。
  - 前端日志中心新增“运行记录”列表，支持按运行切换问题摘要和事件时间线。

- 验证：
  
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_tray_status.py apps/backend/tests/test_sync_event_store.py -p pytest_asyncio.plugin -q`
  - `npm run build --prefix apps/frontend`
    
    ## v0.6.5-dev.3 (2026-04-30)

- 目标：为运行级诊断增加稳定持久化层，不再完全依赖事件流临时反推运行摘要。

- 结果：
  
  - 新增 `sync_runs` 表和 `SyncRunService`，持久化每次同步运行的开始/结束时间、触发来源、结果和核心计数。
  - `SyncTaskRunner` 在运行开始与结束时写入 `sync_runs`，日志中心接口优先读取该表生成运行列表和任务概览。
  - 历史版本没有 `sync_runs` 数据时，后端仍会回退到 `sync-events.jsonl` 分组，兼容旧数据。

- 验证：
  
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_run_service.py apps/backend/tests/test_tray_status.py apps/backend/tests/test_sync_event_store.py -p pytest_asyncio.plugin -q`
  - `python -m compileall apps/backend/src`
    
    ## v0.6.5 release (2026-04-30)

- 目标：
  
  - 发布 `v0.6.5` 稳定版，收口 Windows 静默更新修复、运行级日志中心改造，以及 `sync_runs` 运行摘要持久化。

- 结果：
  
  - 稳定版基于 `v0.6.5-dev.1` 至 `v0.6.5-dev.3`：Windows 静默更新去掉 `DETACHED_PROCESS`，修复 helper 无法接管导致的静默安装超时退出问题。
  - 日志中心升级为真正的“任务 -> 运行 -> 事件”模型，每次同步独立成条，任务概览默认只反映最近一次运行，历史失败不再持续污染后续成功执行。
  - 后端新增 `sync_runs` 表持久化每次运行的开始/结束时间、触发来源、上传/下载/失败/冲突计数与最近错误；日志中心优先读取该表，`sync-events.jsonl` 继续保留为细粒度事件时间线。

- 测试：
  
  - 沿用 `v0.6.5-dev.1` 至 `v0.6.5-dev.3` 的自动更新、日志中心、运行摘要持久化相关后端测试与前端构建验证。

## v0.7.14-dev.1 (2026-05-16)

- 目标：
  
  - 修复 Windows 静默安装只收到 bootstrap 的 `worker_pid` 回执就退出，导致 worker 尚未真正接管时被误判成功的问题。

- 结果：
  
  - bootstrap 与 worker 的 handoff 阶段拆分为 `bootstrap_started` 和 `helper_started`，托盘只在收到 worker 真正回执或 `installer_started` 后才退出，不再把 bootstrap 的暂存回执当成“安装已接管”。
  - `_wait_for_ready_install_handoff()` 会跳过 `bootstrap_started`，超时后若仍停在该阶段会明确报“静默安装 worker 未确认接管”，并带上最后一条 `worker_pid` 细节。
  - Windows 静默安装 helper 的创建参数补上 `CREATE_BREAKAWAY_FROM_JOB`，降低托盘退出后 helper 被父 job 提前回收的概率。

- 测试：
  
  - `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONPATH='apps/backend'; python -m pytest apps/backend/tests/test_tray_update_install.py -p pytest_asyncio.plugin -q`
  - `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONPATH='apps/backend'; python -m pytest apps/backend/tests/test_tray_update_install.py apps/backend/tests/test_system_update_api.py apps/backend/tests/test_update_service.py -p pytest_asyncio.plugin -q`

- 问题：
  
  - 现有安装目录中的 `v0.7.13` 不会自动获得这次修复，需要重新安装包含 `v0.7.14-dev.1` 的构建后再验证静默更新链路。

## v0.7.14 release (2026-05-16)

- 目标：
  
  - 发布 `v0.7.14` 稳定版，收口 Windows 静默安装 handoff 时序修复。

- 结果：
  
  - 稳定版纳入 `v0.7.14-dev.1`：Windows 静默安装不再把 bootstrap 的 `worker_pid` 暂存回执误判成“已接管”，托盘只会在 worker 真正开始执行或安装器已启动后退出。
  - 若 handoff 一直停在 `bootstrap_started`，当前版本会继续保留并明确报“worker 未确认接管”，便于区分“已下载但尚未真正开始安装”和“安装器已接管”的状态。
  - 静默安装 helper 补上 `CREATE_BREAKAWAY_FROM_JOB`，降低托盘退出后 helper 被父 job 提前回收、导致安装中途失联的概率。

- 测试：
  
  - 沿用 `v0.7.14-dev.1` 的静默安装、系统更新 API 与更新状态服务相关回归测试。

- 问题：
  
  - 需要在已安装 `v0.7.14` 的环境上，再向后升级一个更高版本，才能完整验证“自动静默升级”端到端链路。

## v0.7.15-dev.1 (2026-05-22)

- 目标：
  
  - 继续收口日志中心载入慢的问题，把事件时间线从“JSONL 顺序扫描”推进到“SQLite 优先查询”，降低打开日志中心和切换任务时的卡顿。

- 结果：
  
  - 新增 `sync_run_events` 与 `sync_meta` 表，以及 `SyncRunEventService`；同步事件现在会双写到 SQLite 和 `sync-events.jsonl`，并用稳定事件 ID 保证历史回填与重复写入幂等。
  - 后端启动时会自动把旧 `sync-events.jsonl` 预热回填到 SQLite；`/sync/logs/sync` 与任务诊断中的事件/问题明细改为优先读取数据库，仅在当前作用域没有持久化事件时才受控回退 JSONL。
  - `SyncTaskRunner` 新增异步批量事件落库队列，避免把每条日志的数据库写入阻塞在同步热路径；运行结束前会主动 flush，缩短“摘要已结束但事件尚未入库”的不一致窗口。
  - 数据库初始化补齐模型注册保障，避免未来再出现新表/新列定义了但 `create_all()` 时未实际注册的隐性缺表风险。
  - 前端日志中心将冲突列表改为按 `conflicts` Tab 懒加载；切换任务时不再先清空 `selectedRunId`，并为 diagnostics / events 查询保留旧数据，减少详情区闪空与无意义首屏请求。
  - 新增 `docs/local_specs/log_center_performance_remediation_plan_v0.7.15-dev.2.md`，沉淀本轮日志中心性能治理方案、自审结论与后续阶段拆解；该文档保持在本地规格目录，不进入 Git 交付面。

- 测试：
  
  - `python -m pytest tests/test_sync_run_event_service.py tests/test_sync_task_api.py tests/test_db_session.py tests/test_tray_status.py`（工作目录：`apps/backend/`）
  - `npm --prefix apps/frontend run build`

- 问题：
  
  - 当前仍保留 `sync-events.jsonl` 作为归档和回退路径，系统日志 `larksync.log` 也尚未做数据库化；更大规模日志下若需要进一步压榨尾延迟，后续可继续把回填 checkpoint 与事件表定时清理任务独立成显式后台作业。

## v0.7.15-dev.2 (2026-05-22)

- 目标：
  
  - 补齐日志中心性能治理剩余闭环：让旧日志回填支持断点恢复和持续追平，同时把清理与修复工作从接口请求链路中彻底移到后台维护任务。

- 结果：
  
  - `SyncEventStore` 新增基于 byte offset 的 JSONL 断点读取能力，`SyncRunEventService` 改为按 `sync_meta` 持久化 `status / offset / log_size / log_mtime_ns`，支持分批回填、断点恢复、文件截断后游标重置，以及在 DB 写失败时保持游标不前移。
  - 新增 `SyncLogMaintenanceService` 后台维护服务：应用启动后立即异步启动，持续把 `sync-events.jsonl` 追平到 `sync_run_events`，并按 `sync_log_retention_days` 低频清理 SQLite 事件与 JSONL 归档，不再要求用户打开日志页才能触发维护。
  - `/sync/logs/sync` 与任务诊断的 DB-first 逻辑改为只读取回填状态，不再在请求里执行回填或清理；当回填完成且 DB 查询为空时，接口会直接返回空结果，不再无意义回退整份 JSONL。
  - 数据库初始化补上 `sync_runs` 与 `sync_run_events` 的复合索引保障；`SyncRunService.list_latest_by_tasks()` 改为窗口函数查询，避免为每个任务把全部历史运行拉回 Python 再取第一条。

- 测试：
  
  - `python -m pytest tests/test_sync_run_event_service.py tests/test_sync_log_maintenance_service.py tests/test_sync_task_api.py tests/test_sync_run_service.py tests/test_db_session.py tests/test_tray_status.py`（工作目录：`apps/backend/`）

- 问题：
  
  - 当前仅治理了同步事件链路，系统日志 `larksync.log` 仍是文件读取模式；若后续需要统一观测面板，可再评估是否将系统日志摘要化或引入单独检索层。

## v0.7.15 release (2026-05-22)

- 目标：
  
  - 发布 `v0.7.15` 稳定版，收口日志中心性能治理，将 DB-first 事件读取、后台 checkpoint 回填和后台维护清理作为正式能力对外发布。

- 结果：
  
  - 稳定版纳入 `v0.7.15-dev.1` 与 `v0.7.15-dev.2`：日志中心事件链路已经从“JSONL 顺序扫描优先”切到“`sync_runs` + `sync_run_events` SQLite 优先”，旧 `sync-events.jsonl` 改为后台持续追平与受控降级来源。
  - 后端新增后台日志维护服务，启动不再阻塞等待旧日志全量回填；事件回填支持 checkpoint、断点恢复、文件截断后游标重置，以及按保留天数低频清理 SQLite 事件与 JSONL 归档。
  - 日志中心首屏无效冲突请求、切任务详情闪空、`list_latest_by_tasks()` 全量拉历史运行等放大器已一并收口，正式版具备发布条件。

- 测试：
  
  - `python -m pytest tests/test_sync_run_event_service.py tests/test_sync_log_maintenance_service.py tests/test_sync_task_api.py tests/test_sync_run_service.py tests/test_db_session.py tests/test_tray_status.py`（工作目录：`apps/backend/`）
  - `python -m pytest tests/test_sync_event_store.py`（工作目录：`apps/backend/`）
  - `npm --prefix apps/frontend run build`
  - `python scripts/build_installer.py --nsis`

- 问题：
  
  - macOS 安装包仍由 GitHub Actions 的手动 `workflow_dispatch` 构建，当前正式版发布默认只自动生成并上传 Windows 安装包与校验文件。

## v0.7.16-dev.1 (2026-05-22)

- 目标：
  
  - 彻底修复 Windows 静默安装在 `v0.7.15` 上再次失败、handoff 长时间停在 `bootstrap_started` 的问题，并补齐能真实执行 `powershell.exe -File` 的回归测试，避免后续再漏掉脚本编码/解析层面的失败。

- 结果：
  
  - 通过检查本机 `C:\Users\85406\AppData\Roaming\LarkSync\logs\update-install.log` 和 `install-handoff.json`，确认当前失败并非安装器退出码或重启阶段问题，而是 worker 从未写出 `helper_started`；静默安装现场始终停留在 `worker_pid=...` 的 `bootstrap_started`。
  - 进一步用真实 `powershell.exe -File` 手工执行生成的 worker 脚本后，定位到 Windows PowerShell 5.1 读取“无 BOM UTF-8 `.ps1` + 中文日志文本”时会发生误解码，并在脚本末尾触发 `ParserError: The string is missing the terminator`；因此 worker 尚未运行到 `Write-Handoff 'helper_started'` 就已在解析阶段崩溃。
  - 托盘现在通过 `_write_powershell_script()` 统一将静默安装生成的 `bootstrap.ps1` / `worker.ps1` 以 `utf-8-sig` 写入，保证 Windows PowerShell 5.1 能稳定解析含中文文本的脚本文件；同时保留 handoff JSON 无 BOM 写入，避免回退到旧的 UTF-8 BOM 读取问题。
  - 新增两层回归测试：一层验证生成脚本文件在 Windows 上确实带 BOM，另一层直接用真实 `powershell.exe -File` 执行生成的 worker 脚本，确认它不再因 ParserError 失败，而是按预期写出 `launch_failed` handoff。

- 测试：
  
  - `python -m pytest tests/test_tray_update_install.py -q`（工作目录：`apps/backend/`）
  - 后续联动回归会继续覆盖 `test_system_update_api.py`、`test_update_service.py`、`test_update_scheduler.py`

- 问题：
  
  - 当前修复聚焦于 Windows PowerShell 5.1 的脚本文件解码问题；如后续仍出现静默安装失败，下一优先级应直接比对 `update-install.log` 与新生成脚本内容，而不是再把问题默认归因到 handoff 时序。

## v0.7.16 release (2026-05-22)

- 目标：
  
  - 发布 `v0.7.16` 稳定版，将 Windows 静默安装脚本编码修复和真实 PowerShell 回归测试作为正式能力对外发布，结束 `v0.7.15` 上静默安装卡死在 `bootstrap_started` 的回归问题。

- 结果：
  
  - 正式版纳入 `v0.7.16-dev.1` 的全部修复：托盘生成的 `bootstrap.ps1` / `worker.ps1` 现统一以 BOM UTF-8 写入，兼容 Windows PowerShell 5.1 对含中文脚本的解码行为，避免 helper 在解析阶段直接抛出 `ParserError`。
  - 新增真实 `powershell.exe -File` 回归测试后，这类“脚本已生成但 PowerShell 尚未真正执行”的问题已被纳入自动化覆盖，后续再次回归时能在测试阶段而不是正式版安装阶段暴露。
  - 当前稳定版的自动更新链路至此覆盖：下载校验、确认安装、bootstrap/worker handoff、安装器拉起、安装后重启与过期安装请求防抖，Windows 静默升级主链路完成本轮修复收口。

- 测试：
  
  - `python -m pytest tests/test_tray_update_install.py tests/test_system_update_api.py tests/test_update_service.py tests/test_update_scheduler.py -q`（工作目录：`apps/backend/`）
  - `npm --prefix apps/frontend run build`
  - `python scripts/build_installer.py --nsis`

- 问题：
  
  - GitHub Release 默认仍自动发布 Windows 安装包；如需同时提供 macOS 安装包，仍需后续手动触发对应工作流。

## v0.7.27-dev.1 (2026-06-12)

- 目标：
  
  - 排查并修复安装版在同步 `软件设计说明书-V1.4-插图规划说明.md` 时反复出现的“创建块失败，已中止替换”，明确是否为文档内容触发的飞书块创建参数错误。

- 结果：
  
  - 已定位并修复一个会中止整篇 Docx 替换的 Markdown 上行问题：当 fenced code 中只包含 `![...]()` / `[...](...)` 这类资源语法示例时，旧链路会把示例误当成真实本地资源上传，再在回填阶段把代码块清空，最终触发飞书 `invalid param` 并报出“创建块失败，已中止替换”。
  - 进一步确认失败根因是飞书代码块 payload 被构造成空 `elements`；受影响的场景不只限于这次复现文档，任何把 code block 清空的边角链路都可能触发同类整篇替换失败。
  - 在 `DocxMarkdownAssetService` 中补充 fenced code 跳过逻辑：图片/附件占位扫描不再进入代码块，避免代码示例里的本地资源语法被误上传为真实飞书图片或附件。
  - 同时在 `DocxService._sanitize_block()` 中新增空代码块兜底：若 `code.elements` 为空，会自动补一个零宽占位文本元素后再发往飞书，避免历史链路或其他边角场景再次因为空 code block 被飞书判定为非法参数并中止整篇文档替换。
  - 同步补充回归测试，覆盖“fenced code 中的图片示例不会被替换成占位资源”“空 fenced code 保持原样进入 convert 前规范化”和“空 code block 在创建前被补为合法 payload”三类场景，防止后续再次回归。

- 测试：
  
  - `python -m pytest tests/test_docx_service.py tests/test_docx_content_write_service.py`（工作目录：`apps/backend/`）

- 问题：
  
  - 当前修复针对的是飞书 `block_type=14` 空 `elements` 这一类明确非法 payload；若后续仍出现 `1770001 invalid param`，应继续优先查看 `无效块已跳过` 日志中的 `block_type` 与 payload，而不是只看上层的“创建块失败”汇总文案。
