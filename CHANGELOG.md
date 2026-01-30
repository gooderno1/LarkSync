# CHANGELOG

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
