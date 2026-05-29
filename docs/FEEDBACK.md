# LarkSync 反馈与排障指南

更新时间：2026-05-28

如果你在安装、授权或同步中遇到问题，请尽量按本文格式反馈。信息越完整，越容易复现和修复。

## 1. 优先级判断

请优先反馈以下问题：

- 疑似数据丢失、误删、误覆盖。
- 安装包无法启动或启动后立即退出。
- OAuth 无法完成授权。
- 首次 `download_only` 同步失败。
- 同步任务反复失败且日志没有明确原因。
- 自动更新下载或安装失败。

## 2. 提交前先检查

1. 是否使用最新稳定版安装包。
2. 是否已阅读 [快速开始](QUICK_START.md) 和 [OAuth 配置指南](OAUTH_GUIDE.md)。
3. 飞书控制台是否已添加所需用户身份权限。
4. 是否重新授权过。
5. 日志中心最近一次运行是否显示具体错误码。

## 3. 反馈模板

建议包含以下信息：

```text
问题类型：安装 / OAuth / 同步 / 转码 / 冲突 / 自动更新 / 其他
LarkSync 版本：
操作系统：Windows 10/11 / macOS Intel / macOS Apple Silicon
安装方式：安装包 / 源码运行
同步模式：download_only / bidirectional / upload_only
本地目录类型：测试目录 / Obsidian vault / Git 仓库 / NAS / 其他
飞书目录规模：大约多少文件、多少在线文档、是否包含大量图片或表格
复现步骤：
期望结果：
实际结果：
日志摘要：
是否愿意提供脱敏后的日志或 docx blocks JSON 样例：
```

## 4. 日志位置

常见日志位置：

- 后端运行日志：`data/logs/larksync.log`
- 后端 stderr：`data/logs/backend-stderr.log`
- Vite 开发日志：`data/logs/vite-dev.log`
- Windows 静默安装日志：用户数据目录中的 `update-install.log`

如果通过安装包运行，日志通常位于 LarkSync 用户数据目录；如果通过源码运行，优先检查仓库下的 `data/logs/`。

## 5. 需要脱敏的信息

提交日志前请遮盖：

- App Secret。
- access token / refresh token。
- 飞书文件 token、文档 token、文件夹 token。
- 分享链接。
- 公司、客户、项目名。
- 不希望公开的本地绝对路径。

可以保留：

- 错误码。
- HTTP 状态码。
- request id。
- LarkSync 版本。
- 同步模式。
- 文件扩展名和大致文件规模。

## 6. 高价值样例

以下样例对修复很有帮助：

- 权限错误对应的完整错误码和 request id。
- 无法转码的 docx blocks JSON 脱敏样例。
- 复杂 Markdown 片段。
- 同步前后的目录结构摘要。
- 冲突发生前后的本地文件 mtime 与云端修改时间。

## 7. 数据风险处理规则

如果你怀疑发生误删、误覆盖或数据丢失：

1. 先暂停对应同步任务。
2. 不要继续反复点击“立即同步”。
3. 复制保留本地目录、`.larksync_trash/`、`data/larksync.db` 和相关日志。
4. 按反馈模板提交问题，并标注“数据风险”。

这类问题优先级最高。
