# LarkSync 快速开始

更新时间：2026-05-28

本文面向第一次试用 LarkSync 的用户。推荐先用小型测试目录和 `download_only` 模式完成一次闭环，再决定是否启用双向同步。

## 1. 下载安装包

1. 打开发布页：<https://github.com/gooderno1/LarkSync/releases>
2. Windows 下载 `LarkSync-Setup-*.exe`。
3. macOS 下载与你机器架构匹配的 `LarkSync-*.dmg`。
4. 安装后启动 LarkSync，系统托盘会出现 LarkSync 图标。

如果你从源码运行，请参考 [使用教程](USAGE.md) 中的本地开发流程。

## 2. 准备飞书 OAuth

LarkSync 需要通过飞书开放平台访问你的云空间。首次使用前需要创建一个企业自建应用，并填写 App ID / App Secret。

最小路径：

1. 打开飞书开放平台控制台。
2. 创建企业自建应用。
3. 配置 OAuth 回调地址：`http://localhost:8000/auth/callback`。
4. 添加用户身份权限：
   - `drive:drive`
   - `docx:document`
   - `docx:document:readonly`
   - `docx:document.block:convert`
   - `drive:drive.metadata:readonly`
   - `contact:contact.base:readonly`
5. 回到 LarkSync 设置页，填写 App ID、App Secret、Redirect URI。
6. 点击“连接飞书”完成授权。

详细截图级步骤见 [OAuth 配置指南](OAUTH_GUIDE.md)。

## 3. 创建第一个同步任务

首次建议使用一个新建的飞书测试文件夹，里面放 2-5 份文档即可。

1. 打开 LarkSync 管理面板。
2. 进入“同步任务”。
3. 点击“新建任务”。
4. 选择本地测试目录，例如 `D:\LarkSyncTrial\FeishuMirror`。
5. 选择或填写飞书测试文件夹 token。
6. 同步模式选择 `download_only`。
7. 保存任务，并等待首次同步完成。

同步完成后，请检查：

- 本地目录是否出现飞书文档对应的 Markdown 文件。
- 图片是否落在文档旁边的资源目录中。
- 日志中心最近一次运行是否为成功。
- 文件修改时间是否接近云端修改时间。

## 4. 什么时候启用双向同步

满足以下条件后，再考虑双向同步：

- 已经用 `download_only` 验证过 OAuth、目录树、文档转 Markdown。
- 已经理解删除联动策略：`off` / `safe` / `strict`。
- 已经用测试目录验证过本地 Markdown 修改能正确回写云端。
- 确认这不是唯一副本，重要资料已有备份。

双向同步会修改云端或本地内容。正式使用前建议先对一个小目录做至少 1 天试运行。

## 5. 遇到问题先看这里

- 授权失败：检查回调地址是否完全一致，App ID / App Secret 是否正确。
- Access denied：检查飞书控制台是否添加了用户身份权限，并重新授权。
- 同步后看不到文件：先打开日志中心，查看最近一次运行是否有跳过、失败或权限错误。
- 安装后打不开：查看 [反馈与排障指南](FEEDBACK.md)，按模板提交系统版本、安装包版本和日志。

## 6. 后续阅读

- [使用教程](USAGE.md)
- [同步逻辑说明](SYNC_LOGIC.md)
- [安全与隐私说明](SECURITY_AND_PRIVACY.md)
- [反馈与排障指南](FEEDBACK.md)
