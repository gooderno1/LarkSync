# LarkSync 使用教程

适用：当前稳定版 v0.10.1；AI 新任务接口适用 v0.11.0-dev.1 及后续版本。更新时间：2026-10-20。

## 安装与账号连接

普通用户下载 [桌面安装包](https://github.com/gooderno1/LarkSync/releases)，不需要安装 Python、Node.js 或 `lark-cli`。Windows 运行安装程序；macOS 选择正确 CPU 架构，将应用拖入 Applications。

启动后点击“开始扫码连接”，按页面提示完成个人应用注册与账号授权。首次可能有两次扫码，后续直接选择已有应用添加账号。组织禁止自动注册时，在高级入口添加自建应用后扫码；旧 OAuth 回调方式是兼容路径，详见 [授权指南](OAUTH_GUIDE.md)。不要在配置文件中手写 App Secret 或令牌。

多个账号会同时执行各自任务；切换左侧账号仅改变管理界面的范围，不停止其他账号。

## 创建与维护任务

1. 在“同步任务”中新建任务，选择本地目录和可访问的云文件夹。
2. 首次建议选择“仅下载”，并关闭删除联动。
3. 根据需要添加忽略子路径，或给某个文档 / 子文件夹单独设置方向。
4. 保存后启用的任务可能立即执行。在活动管理查看运行，在问题中心处理失败和冲突。
5. 等待同步完成后检查本地 Markdown、图片和附件，再扩大同步范围。

修改任务会应用新配置；暂停会取消正在运行的任务并停止后续调度，恢复可能立即开始同步。删除任务会移除任务和映射，保留本地与云端文件。文件移动、重命名后，按相对路径设置的规则可能需要调整。

方向包括 `download_only`、`upload_only` 和 `bidirectional`。忽略路径优先于方向规则；文件规则优先于文件夹规则，子文件夹覆盖父文件夹，其他对象继承任务默认方向。详见 [同步逻辑](SYNC_LOGIC.md)。

## 通过 AI 操作

使用 Codex / WorkBuddy 可通过对话创建、修改、暂停、恢复和诊断任务。请按 [AI 使用指南](AI_GUIDE.md) 安装通用技能，并使用 v0.11.0+ 配套应用。

源码环境下可执行：

```text
python scripts/larksync_cli.py capabilities
python scripts/larksync_cli.py account-list
python scripts/larksync_cli.py task-plan --spec-file task.json
python scripts/larksync_cli.py --account-id ACCOUNT task-create --spec-file task.json
python scripts/larksync_cli.py --account-id ACCOUNT task-wait --task-id TASK --timeout 60
```

JSON 示例、扫码步骤和错误处理见 [CLI 契约](CLI_AGENT_CONTRACT.md)。`ok: true` 表示请求成功；必须检查 `sync_complete` 才能判断同步完成。

## 设置与数据

- 上传 / 下载频率在设置页统一配置，影响全部任务；目前不是任务级时间表。
- 删除策略有 `off`、`safe`、`strict`；双向同步和删除策略应先在测试目录验证。
- 开机自启动在“设置 → 当前设备”或托盘菜单中设置，系统启动项会即时更新。
- 开发环境默认数据存储在仓库 `data/`；桌面安装版的数据位置以当前运行实例的设置和日志为准。不要混用开发与正式环境数据目录。
- 凭据由应用按系统机制保存。不要将 token、密钥、个人数据或本地规格提交到 Git。

## 源码开发与验证

开发 / 打包基线：Python 3.14.x、Node.js 25.x。后端声明最低 Python 3.10；当前前端 Vite 需要现代 Node.js，不能沿用旧的 Node 18 环境。

```text
npm install
npm --prefix apps/frontend ci
python -m pip install -r apps/backend/requirements.txt
python -m pip install -r apps/backend/requirements-dev.txt
npm run dev
```

默认前端 `http://localhost:3666`，后端 `http://localhost:18765`。与正式版并行测试使用 `npm run dev:test`；该入口分离端口、数据与测试凭据。测试范围和真实账号限制见 [真实数据测试指南](REAL_DATA_TESTING.md)。

```text
npm --prefix apps/frontend run lint
npm --prefix apps/frontend run test
npm --prefix apps/frontend run build
```

在 `apps/backend` 目录运行 `python -m pytest`。安装包构建：Windows `python scripts/build_installer.py --nsis`，macOS `python scripts/build_installer.py --dmg`。构建同时生成通用 Skill ZIP 和 SHA256 校验文件。

## 排障

- 后端不可达：先确认应用运行和所用端口；AI CLI 使用 `check`。
- 扫码授权过期：重新开始会话；pending / slow_down 按返回间隔等待。
- 没有目录权限：检查目标是否对当前账号可见，必要时重新授权；本地存在令牌不等于云权限有效。
- 同步未完成：读取活动、问题中心或 `task-diagnostics`；超时不代表任务已经失败或完成。
- 需要反馈：按 [反馈模板](FEEDBACK.md) 提供版本、系统、错误 ID 和脱敏日志。

继续阅读：[快速开始](QUICK_START.md)、[FAQ](FAQ.md)、[安全与隐私](SECURITY_AND_PRIVACY.md)、[版本记录](../CHANGELOG.md)。
