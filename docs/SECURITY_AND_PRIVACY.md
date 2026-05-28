# LarkSync 安全与隐私说明

更新时间：2026-05-28

LarkSync 是本地运行的飞书文档同步工具。它需要访问你的飞书云空间，因此首次试用前应先理解授权范围、token 存储方式和日志边界。

## 1. 数据流向

LarkSync 的核心数据流为：

- 本地客户端读取/写入本机文件系统。
- 本地客户端通过 HTTPS 调用飞书开放平台 API。
- 本地 SQLite 数据库记录同步状态、任务配置、运行摘要和诊断信息。

当前项目不依赖 LarkSync 自有云端中转服务；同步数据不会主动上传到第三方服务器。

## 2. 飞书权限用途

常用权限如下：

| 权限 | 用途 |
| --- | --- |
| `drive:drive` | 读取、下载、上传、管理云空间文件和文件夹 |
| `drive:drive.metadata:readonly` | 获取云端文件元数据与修改时间 |
| `docx:document` | 读取和写入飞书新版文档内容 |
| `docx:document:readonly` | 只读访问新版文档内容 |
| `docx:document.block:convert` | 将 Markdown 内容转换为飞书文档块 |
| `contact:contact.base:readonly` | 获取当前授权用户基础信息，用于任务归属展示 |

如果飞书控制台提示需要审核，请等待权限生效后重新授权。

## 3. Token 与配置存储

- App ID / App Secret 会保存到本地配置文件或环境变量中。
- access token / refresh token 默认通过系统安全存储能力保存。
- Windows 环境优先使用系统凭据/DPAPI 能力。
- macOS 环境优先使用 Keychain。
- 无桌面 keyring 的特殊环境可使用文件型 token store，但不推荐普通用户启用。

请不要把 `data/config.json`、日志文件、数据库文件提交到公开仓库或发给陌生人。

## 4. 本地数据位置

常见本地数据包括：

- `data/larksync.db`：同步状态库。
- `data/logs/`：运行日志。
- `data/config.json`：本地配置。
- 用户选择的同步目录：实际文档和资源文件。

这些目录默认已被 `.gitignore` 忽略。

## 5. 日志反馈前的脱敏建议

提交 issue 或反馈日志前，请先检查并遮盖：

- App Secret、access token、refresh token。
- 飞书文件夹 token、文档 token、云空间分享链接。
- 公司、客户、项目名等敏感路径。
- 本地用户名、完整绝对路径中不希望公开的部分。

如果问题涉及权限或 API 返回，请优先保留错误码、HTTP 状态和 request id，这些信息有助于定位。

## 6. 安全使用建议

- 首次试用使用 `download_only` 和测试目录。
- 对重要目录启用双向同步前先备份。
- 不要把同一个本地父子目录分别创建为两个同步任务。
- 团队共享目录应先小范围验证冲突处理和删除策略。
- 定期查看日志中心，确认最近一次同步没有隐藏失败。

## 7. 已知安全边界

- 双向同步会根据任务策略修改云端或本地文件。
- 删除联动策略为 `safe` 或 `strict` 时，删除动作可能传播到另一端。
- 复杂文档格式可能存在有损转换；重要文档建议先用测试副本验证。
- 如果飞书 API 字段结构变化，LarkSync 需要基于实际 JSON 样例补充适配。
