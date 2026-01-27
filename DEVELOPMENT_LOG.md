# DEVELOPMENT LOG

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
