# LarkSync FAQ

更新时间：2026-05-28

## LarkSync 是什么

LarkSync 是一个本地优先的飞书文档同步工具。它把飞书云文档、Markdown、本地文件系统、NAS 和 AI Agent 工作流连接起来，让你可以继续在飞书中协作，同时把文档稳定落到本地目录中。

## 第一次试用应该选什么模式

建议先选 `download_only`。这个模式只从飞书下载到本地，不会把本地修改回写云端，适合首次验证 OAuth、目录映射和 Docx 转 Markdown 效果。

确认流程稳定后，再用小型测试目录验证双向同步。

## LarkSync 会不会把我的文档上传到第三方服务器

当前 LarkSync 不依赖自有云端中转服务。核心数据流是本地客户端读写本机文件系统，并通过 HTTPS 调用飞书开放平台 API。

详见 [安全与隐私说明](SECURITY_AND_PRIVACY.md)。

## 为什么需要配置飞书 OAuth

LarkSync 需要以你的用户身份读取和写入你有权限访问的飞书云空间文件。飞书开放平台要求通过 OAuth 获取用户访问凭证，因此首次使用需要创建企业自建应用并配置 App ID、App Secret、回调地址和权限。

详见 [OAuth 配置指南](OAUTH_GUIDE.md)。

## 需要哪些飞书权限

常用权限：

- `drive:drive`
- `docx:document`
- `docx:document:readonly`
- `docx:document.block:convert`
- `drive:drive.metadata:readonly`
- `contact:contact.base:readonly`

这些权限分别用于云空间文件读写、文档内容读写、Markdown 转文档块、元数据读取和当前用户信息展示。

## Access denied 怎么办

优先检查：

1. 飞书控制台是否添加了所需权限。
2. 权限是否是用户身份权限。
3. 权限是否已经审核通过。
4. 添加权限后是否重新授权。
5. OAuth 回调地址是否与 LarkSync 设置页完全一致。

## 可以直接同步重要目录吗

不建议第一次就同步重要目录。首次试用建议：

1. 新建一个飞书测试文件夹。
2. 放 2-5 份文档。
3. 新建一个本地空目录。
4. 创建 `download_only` 任务。
5. 确认日志中心成功后再扩大范围。

## 双向同步有什么风险

双向同步会根据任务策略修改云端或本地内容。如果本地和云端同时修改，系统会进入冲突处理；如果启用删除联动，删除动作也可能传播到另一端。

正式启用双向同步前，请先理解删除策略 `off` / `safe` / `strict`，并用测试目录试运行。

## 复杂表格和附件能否完全保真

不能承诺 100% 保真。飞书 Docx 块结构和 Markdown 表达能力存在差异，复杂表格、内嵌 sheet、附件块等场景可能存在有损转换或占位输出。

如果遇到无法解析的块结构，请提供脱敏后的 docx blocks JSON 样例。

## OpenClaw / AI Agent 场景怎么用

推荐使用 `download_only` + 每日低频同步。流程是：

1. LarkSync 低频同步飞书目录到本地。
2. OpenClaw 或其他 Agent 优先读取本地目录。
3. 高频问答不再反复打飞书 API。

详见 [OpenClaw Skill 使用与上架指南](OPENCLAW_SKILL.md)。

## 遇到问题应该如何反馈

请按 [反馈与排障指南](FEEDBACK.md) 提供：

- LarkSync 版本。
- 操作系统。
- 安装方式。
- 同步模式。
- 复现步骤。
- 脱敏后的日志摘要。
- 是否涉及数据风险。

如果疑似误删、误覆盖或数据丢失，请先暂停任务，不要反复点击“立即同步”。
