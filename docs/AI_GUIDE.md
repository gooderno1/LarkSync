# 通过 Codex / WorkBuddy 使用 LarkSync

适用版本：v1.0.0 及后续版本。正式安装包包含 AI 任务管理接口和原生 CLI，通用技能包随版本一同发布。当前版本：v1.1.0。更新时间：2026-10-24。

## 从一个 Git 链接开始

LarkSync 负责把飞书 / Lark 云文档持续同步到本地 Markdown 和文件。AI 负责理解你的意图、配置任务并按需读取本地资料。已有本地知识库时，无需让模型反复遍历云端。

可以把以下内容发给 AI：

> 请阅读 https://github.com/gooderno1/LarkSync 的 README、docs/AI_GUIDE.md 和通用 Skill。帮我安装适合本机的版本，连接我的飞书账号，并把我提供的文件夹同步到指定本地目录。先仅下载，关闭删除联动；预览具体配置，按我的授权创建任务，再检查同步是否完成。

AI 需要能访问仓库、执行本地命令，且应用在同一台机器运行。仅能聊天、不能操作本机的客户端可解释和生成配置，但无法实际安装或控制任务。

## 1. 安装应用

- [V1.1 发布页](https://github.com/gooderno1/LarkSync/releases/tag/v1.1.0)：Windows 选择 EXE；macOS 根据 Apple Silicon（arm64）/ Intel（x86_64）选择 DMG；技能使用 `LarkSync-Agent-Skill-1.1.0.zip`。
- 读取具体 Release 的说明与 SHA256，不能只根据文件名假设兼容性。使用本指南命令需要 v1.0.0 或更新版本；从 v0.10.x 升级的用户先安装新版应用，再配置技能。
- 启动应用后，默认 API 地址为 `http://localhost:18765`。CLI 不会自动启动另一个后端。
- 只有源码开发才需要 Python / Node.js 依赖，步骤见 [使用教程](USAGE.md)。安装版附带 `LarkSyncCLI`，无需另装 Python。

Windows 默认 CLI 路径为 `C:\Program Files\LarkSync\LarkSyncCLI.exe`，自定义安装时以实际目录为准。macOS 为 `/Applications/LarkSync.app/Contents/MacOS/LarkSyncCLI`。它依赖安装目录内的运行库，不能只复制单个 EXE。

## 2. 安装通用技能

技能源目录为 [`integrations/skills/larksync`](../integrations/skills/larksync)。目录内包含 SKILL.md、参考文档和标准库 CLI，可完整复制到仓库外。发布资产 `LarkSync-Agent-Skill-版本.zip` 与 `.sha256` 由构建自动生成。

### Codex

可直接对 Codex 说：

> 请从 gooderno1/LarkSync 仓库安装 integrations/skills/larksync 技能。

也可以将完整目录复制到 `~/.agents/skills/larksync`（用户范围），或项目的 `.agents/skills/larksync`（项目范围）。已有同名技能时先检查和备份本地修改，再更新；不要覆盖不相关技能。重新打开会话或重新加载技能后，要求使用 `larksync` 管理同步任务。

Codex 打开仓库时会读取 `AGENTS.md`；只把链接发给模型不等于技能已经安装。让 AI 明确报告实际安装位置和 `capabilities` 调用结果。

### WorkBuddy

将完整技能目录放到所选项目的 `.codebuddy/skills/larksync`，重新打开项目。也可在技能管理界面使用本地 ZIP 导入，选择发布的 `LarkSync-Agent-Skill-*.zip`。导入后确认识别出 `larksync`，再开始任务。

项目技能随项目生效；切换项目后需确认当前上下文已加载。这里提供本地导入兼容包，未宣称已在技能市场上架或通过市场审核。

### 没有技能管理界面

让 AI 阅读 SKILL.md 并调用技能中的 `scripts/larksync_cli.py`，需要 Python 3.10+，不需要 pip 安装依赖。仓库内也保留 `python scripts/larksync_cli.py` 兼容入口。

```text
python scripts/larksync_cli.py capabilities
python scripts/larksync_cli.py check
```

原生 CLI 与 Python CLI 使用相同参数和 JSON 输出。

## 3. 对话创建任务

用户需要表达：**哪个账号、哪个云文件夹、存到哪里、同步方向**。单账号可以自动选择；多账号且意图不明确时，AI 列出账号供选择。忽略目录和文档方向规则按需添加。

标准流程：

1. `account-list` / `app-list` 检查账号与应用。
2. 首次连接通过 `auth-start` 发起注册或授权；用户在返回的官方验证链接扫码；AI 用 `auth-poll` 按返回间隔读取结果。无需把账号密码、密钥或 token 交给 AI。
3. `--account-id ID auth-verify` 检查 Drive 读取；`drive-list` 分页确认云目录。验证读取不代表已验证写权限。
4. `task-plan --spec-file task.json` 生成无写入预览，返回缺少的信息、默认值和影响范围。
5. AI 概述具体配置，并在用户授权范围内执行 `task-create`。启用任务保存后可能立即开始同步。
6. `task-wait` 等待结果。只在 `sync_complete: true` 时报告同步完成；未完成时保留任务 ID / run_id 并说明状态。

例如：

> 将“团队知识库”这个飞书文件夹同步到 D:/Knowledge/Team，只下载，排除“私人资料”。以后我会让你读取这个本地目录。

AI 生成的 JSON 可以是：

```json
{
  "name": "团队知识库",
  "local_path": "D:/Knowledge/Team",
  "cloud_folder_token": "https://你的组织.feishu.cn/drive/folder/真实TOKEN",
  "sync_mode": "download_only",
  "delete_policy": "off",
  "ignored_subpaths": ["私人资料"],
  "enabled": true
}
```

示例链接需替换为实际文件夹链接；macOS 使用 `/Users/用户名/...` 绝对路径。预览不会请求网络、建目录或更改应用设置，服务端仍会校验实际路径冲突与账号权限。

## 4. 日常维护

| 你对 AI 说 | 对应操作 |
| --- | --- |
| 列出我的同步任务 | task-list |
| 修改某个任务的排除目录 / 方向 | task-get → task-update --dry-run → task-update |
| 暂停 / 恢复该任务 | task-pause / task-resume |
| 现在刷新，并告诉我是否完成 | task-run --wait |
| 看看哪些文件失败 | task-diagnostics，可传 run_id |
| 看本地缓存有哪些文件 | task-entries，分页读取 |
| 删除这条同步任务 | task-delete；保留云端与本地文件 |

当前同步频率是全局设置。要求“只让一个任务每天同步一次”时，AI 应说明尚不支持任务级时间表，不能悄悄更改全部任务的频率。

命令参数、JSON 字段、错误码和结果语义见 [CLI 契约](CLI_AGENT_CONTRACT.md) 及 [技能命令参考](../integrations/skills/larksync/references/commands.md)。

## 验证范围

本仓库验证 CLI、HTTP 任务接口、账号隔离、技能独立复制及打包分发。单测使用模拟响应或隔离数据，不等于真实账号已完成扫码或全量同步。macOS 原生运行与 WorkBuddy 技能界面仍需要对应设备上的实机验收。

客户端约定依据：[Codex Skills](https://learn.chatgpt.com/docs/build-skills)、[Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[WorkBuddy 项目规则与技能](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project)、[WorkBuddy 技能管理](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。客户端界面变化时，以对应官方说明为准。
