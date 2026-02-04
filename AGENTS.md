# LarkSync AGENTS 指南

本文件用于指导后续 AI/开发者在本仓库中的协作与交付。请严格遵循。

## 0. 交流与执行原则
- 全程使用中文交流与输出。
- 所有开发文档先行：在动手前必须先阅读并理解以下文档（优先级从高到低）：
  1) `docs/local_specs/LarkSync Vibe Coding 开发执行计划.md`（SSOT，最高优先级）
  2) `docs/local_specs/LarkSync 产品需求文档.md`
  3) `docs/local_specs/LarkSync 产品开发计划书.md`
  4) `docs/local_specs/LarkSync飞书云文档本地同步方案深度调研.md`
  5) `README.md`
- 产品定义文档存放规范：
  - 上述 4 份产品/方案文档统一放在 `docs/local_specs/`。
  - `docs/local_specs/` 为本地开发资料目录，禁止提交到 Git。
  - 后续所有开发任务仍必须持续参考该目录中的文档，不得因为目录迁移而跳过文档先行。
  - 提交前必须执行 `git status -- docs/local_specs`，确认该目录无待提交变更。
  - 若根目录再次出现产品定义文档，必须先迁回 `docs/local_specs/` 再继续开发。
- 飞书开发文档维护规范：
  - 统一从 `https://project.feishu.cn/b/helpcenter/1p8d7djs/qcw96ljx` 获取最新下载入口。
  - 开发前必须先执行：`python scripts/sync_feishu_docs.py`。
  - 脚本会将最新 zip 文档下载到 `docs/feishu/`，并生成 `docs/feishu/_manifest.json`（记录检查时间、来源、文档列表）。
  - 若页面结构变化导致脚本无法解析，必须优先修复脚本，再继续业务开发。
- 发现信息缺失或冲突时：以 SSOT 为准；若需要具体 API 字段定义但文档未给出，必须向用户索取 JSON 样例，严禁猜测。
- 角色定位：高级全栈工程师 + DevOps；强类型、工程化、测试优先。
- 标准工作流：读取任务 → 写测试 → 写代码 → 更新文档 → Git 提交与同步。

## 1. 技术栈与项目结构（必须遵守）
- Monorepo 结构（禁止在根目录创建散乱文件）：
  - `apps/backend/`：Python 3.10+、FastAPI、SQLAlchemy 2.0 Async、Pydantic v2、Watchdog、Loguru
  - `apps/frontend/`：React 18、Vite、TypeScript、TailwindCSS、Shadcn/UI、TanStack Query
  - `data/`：SQLite 数据库、日志等运行数据（`data/larksync.db`）
  - `scripts/`：自动化脚本（如 `release.py`）
  - `docker-compose.yml`、`Dockerfile`
- 任何新增文件必须放在合理目录内。

## 2. 工作流与交付标准（DoD）
- TDD 优先：先写测试，再写实现。
- 后端：新增逻辑必须有 pytest；前端：无 TS 类型报错、无 ESLint 警告。
- 文档同步：功能变更必须更新 `README.md` 功能列表。
- 变更记录：必须在 `CHANGELOG.md` 追加 `[YYYY-MM-DD] vX.Y.Z-dev.N feat/fix: description`。
- 版本更新：按语义化版本更新 `apps/backend/pyproject.toml` 或 `apps/frontend/package.json`。
- Git 同步（必须执行）：
  - 开发前：`git status` 检查工作区；如存在远端，先 `git pull --rebase` 保持同步。
  - 开发后：`git add . && git commit -m "feat(module): description"`。
  - 若配置了远端：`git push`，确保本地与远端同步。
- 版本归档：每个版本完成后，必须更新 `DEVELOPMENT_LOG.md` 记录开发结果与问题。

## 3. 核心同步逻辑要点
- 云端为单一事实来源（SSOT），本地通过 SQLite 状态库判断变更方向。
- 下行（云→本地）：Docx → Markdown，图片下载到 `assets/` 并以相对路径引用；写入后强制设置本地 mtime 为云端时间。
- 上行（本地→云）：Markdown 解析为 Docx Block；非 MD 文件走导入/上传逻辑。
- 冲突处理：云端优先，保全数据，创建冲突副本。
- 速率限制：必须有令牌桶或等价限流 + 指数退避重试；429 必须处理。

## 4. 安全与合规
- access_token / refresh_token 必须加密存储（Windows 用 DPAPI，macOS 用 Keychain），严禁明文写入 config。
- 所有网络通信强制 HTTPS。

## 5. 任务执行规范
- 若用户指定 Task ID，必须按 SSOT 中对应 Spec 执行。
- 若需要第三方 API 的字段样例而文档未提供，必须向用户索取样例 JSON。
- 发生依赖冲突或安装失败时，优先检查版本兼容并修复配置。

## 6. 禁止项
- 禁止偏离项目目录结构。
- 禁止在缺少上下文时臆测 API 字段或业务规则。
- 未经用户允许，不得更改 SSOT 规定的架构与技术栈。
