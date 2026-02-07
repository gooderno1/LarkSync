# CHANGELOG

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
