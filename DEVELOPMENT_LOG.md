# DEVELOPMENT LOG

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
