# 推广文章草稿：我做了一个把飞书文档同步成本地 Markdown 的工具

创建时间：2026-05-28

> 本文是 LarkSync 公开 Beta 软启动的中文推广草稿，可按发布渠道裁剪为 V2EX、掘金、知乎、公众号或社群帖子。

## 标题备选

- 我做了一个把飞书文档同步成本地 Markdown 的工具：LarkSync
- 飞书 + Obsidian / VS Code / NAS：本地优先的文档同步方案
- 让 AI Agent 少打飞书 API：用 LarkSync 做本地知识缓存

## 正文草稿

我最近在做一个小工具，叫 LarkSync。

它解决的是一个很具体的问题：飞书文档很适合团队协作，但很多人的个人工作流仍然在本地，比如 Obsidian、VS Code、NAS、Git 仓库，或者最近越来越常见的 AI Agent 本地知识库。云端协作和本地知识管理之间，经常需要手工复制、导出、上传、重新整理格式。

LarkSync 的目标不是替代飞书，而是把飞书文档纳入本地工作流：

- 飞书 Docx 可以同步为本地 Markdown。
- 文档里的图片会下载到本地资源目录，并在 Markdown 中用相对路径引用。
- 本地 Markdown 可以回写为飞书云文档。
- 普通文件可以在本地目录和飞书云空间之间同步。
- 支持系统托盘常驻、任务级同步策略、日志中心、冲突处理和自动更新。

我目前最推荐的使用方式是 `download_only`：

1. 在飞书里选一个文档文件夹。
2. 在本地选一个空目录。
3. 让 LarkSync 每天低频同步一次。
4. 本地的 Obsidian、VS Code、NAS 或 AI Agent 直接读这个目录。

这样可以把“每次读取都打飞书 API”变成“低频同步到本地，高频本地读取”。对于 OpenClaw 或其他 AI Agent 场景，这个路径会更稳定，也更省 API 调用。

当前项目已经覆盖的能力包括：

- 飞书 Docx 与 Markdown 双向同步。
- 图片、附件和普通文件同步。
- 任务级同步模式：仅下载、双向、仅上传。
- 删除联动策略：关闭、安全、严格。
- 冲突管理：本地优先 / 云端优先。
- 日志中心：按任务、运行和事件查看同步问题。
- Windows / macOS 安装包与自动更新。
- OpenClaw Skill / CLI 工作流。

不过它仍然是公开 Beta，我不建议第一次就拿重要目录直接双向同步。推荐路径是：

1. 下载最新安装包。
2. 按文档配置飞书 OAuth。
3. 新建一个飞书测试文件夹。
4. 创建 `download_only` 任务。
5. 同步成功后再扩大范围。

已知限制也提前说清楚：

- 复杂表格、内嵌 sheet、附件块不一定能 100% 保真。
- 非 Markdown 文件的覆盖更新还在继续完善。
- 双向同步会修改云端或本地内容，重要目录请先备份和小范围试运行。
- 飞书开放平台权限配置有一定门槛，需要创建企业自建应用并配置 scopes。

项目地址：

<https://github.com/gooderno1/LarkSync>

快速开始：

<https://github.com/gooderno1/LarkSync/blob/main/docs/QUICK_START.md>

如果你正好有这些场景，欢迎试用并反馈：

- 想把飞书知识库同步到本地 NAS。
- 想用 Obsidian / VS Code 管理飞书文档内容。
- 想让 AI Agent 读取本地飞书文档缓存。
- 想减少手工导出、复制粘贴和重复上传。

如果遇到问题，尤其是安装、OAuth、首次同步、转码或数据风险相关问题，请按反馈模板提交 issue。我会优先处理影响首次试用和数据安全的问题。

## 短帖版本

我做了一个本地优先的飞书文档同步工具 LarkSync。

它可以把飞书 Docx 同步成本地 Markdown，也支持本地 Markdown 回写飞书文档。更推荐的初始用法是 `download_only`：每天低频把飞书文档同步到本地，然后让 Obsidian、VS Code、NAS 或 AI Agent 直接读本地目录，减少反复调用飞书 API。

当前支持 Windows / macOS 安装包、托盘常驻、任务级同步策略、日志中心、冲突管理和 OpenClaw Skill。

项目还在公开 Beta，首次试用建议用测试目录和 `download_only`，不要直接拿重要目录做双向同步。

项目地址：<https://github.com/gooderno1/LarkSync>
