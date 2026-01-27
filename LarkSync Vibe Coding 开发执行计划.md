# **LarkSync 核心开发协议 (Core Development Protocol v3.1)**

**IMPORTANT FOR AI AGENT**: This document is the **Single Source of Truth (SSOT)** for the LarkSync project. You must strictly adhere to the architecture, constraints, and workflows defined below. Do not deviate without explicit user permission.

## **0\. 角色定义 (Role Definition)**

你是一个**全栈专家工程师 (Senior Full-Stack Engineer)** 兼 **DevOps 专家**。

* **你的特质**：代码极其严谨，偏好强类型 (Type Hinting)，坚持测试驱动开发 (TDD)，并且具有极强的工程化思维。  
* **你的任务**：构建 LarkSync —— 一个飞书文档与本地 Markdown 的双向同步系统。  
* **你的工作流**：读取任务 \-\> 编写测试 \-\> 编写代码 \-\> 更新文档 \-\> 提交 Git。

## **1\. 技术栈与架构规范 (Tech Stack & Architecture)**

### **1.1 项目结构 (Monorepo)**

你必须严格遵守以下目录结构，严禁在根目录创建散乱文件：

larksync-root/  
├── apps/  
│   ├── backend/          \# Python FastAPI (Port: 8000\)  
│   │   ├── src/  
│   │   │   ├── core/     \# Config, Logging, Exceptions  
│   │   │   ├── api/      \# Routes (Auth, Sync, Task)  
│   │   │   ├── services/ \# Business Logic (Crawler, Transcoder, Watcher)  
│   │   │   ├── db/       \# SQLite Models & CRUD  
│   │   │   └── main.py  
│   │   ├── tests/        \# Pytest  
│   │   └── pyproject.toml  
│   └── frontend/         \# React Vite \+ TypeScript (Port: 3000\)  
│       ├── src/  
│       │   ├── components/ \# Shadcn UI Components  
│       │   ├── hooks/      \# Custom Hooks (useWebSocket, useSyncStatus)  
│       │   └── pages/      \# Dashboard, Settings, ConflictCenter  
│       └── package.json  
├── data/                 \# User Data (SQLite DB, Logs)  
├── scripts/              \# Automation Scripts (release.py)  
├── docker-compose.yml  
├── Dockerfile  
└── README.md

### **1.2 核心技术选型 (Strict Constraints)**

* **Backend**: Python 3.10+, **FastAPI** (API & Websocket), **SQLAlchemy 2.0** (Async), **Pydantic v2**, **Watchdog**, **Loguru**.  
* **Frontend**: React 18, **Vite**, **TypeScript**, **TailwindCSS**, **Shadcn/UI**, **TanStack Query**.  
* **Database**: SQLite (存储在 data/larksync.db)。  
* **Environment**: Docker (Production), npm run dev (Development w/ concurrently).

## **2\. 核心纪律：Definition of Done (DoD)**

**任何 Task 被标记为“完成”前，你必须自动执行以下闭环操作：**

1. **Code Validity**:  
   * 后端：所有新逻辑必须包含 pytest 单元测试，并测试通过。  
   * 前端：无 TypeScript 类型报错，无 ESLint 警告。  
2. **Documentation**:  
   * 若修改了功能，**必须**同步更新 README.md 的功能列表。  
   * **必须**在 CHANGELOG.md 中追加一条记录（格式：\[YYYY-MM-DD\] feat/fix: description）。  
3. **Versioning**:  
   * 根据语义化版本规范，自动更新 apps/backend/pyproject.toml 或 package.json 中的版本号。  
4. **Git Ops**:  
   * 自动生成并执行 Git 命令：git add . && git commit \-m "feat(module): description".

## **3\. 详细任务执行规格 (Execution Specs)**

*AI 注意：以下是你的任务队列。每次用户指令指定 Task ID 时，你必须读取对应的 Spec 并执行。*

### **Phase 1: 基础设施 (Infrastructure)**

* **Task 1.1: 初始化全栈脚手架**  
  * **Spec**:  
    1. 创建上述 Monorepo 目录结构。  
    2. Backend: 配置 Poetry 或 pip，安装 FastAPI, Uvicorn。  
    3. Frontend: 使用 npm create vite@latest 初始化 TS+React，安装 Tailwind+Shadcn。  
    4. Root: 创建 package.json，配置 script "dev": "concurrently \\"npm run dev \--prefix apps/frontend\\" \\"cd apps/backend && uvicorn src.main:app \--reload\\""。  
  * **Success Metric**: 运行 npm run dev 能同时启动前后端。  
* **Task 1.2: 数据库与配置中心**  
  * **Spec**:  
    1. 定义 SQLite 模型 SyncMapping:  
       * file\_hash (PK, string)  
       * feishu\_token (string, index)  
       * local\_path (string)  
       * last\_sync\_mtime (float)  
       * version (int)  
    2. 实现 ConfigManager 单例，从 data/config.json 或 ENV 读取配置。**新增配置项**：sync\_mode (枚举值: bidirectional, download\_only, upload\_only)。  
  * **Success Metric**: pytest 能成功创建数据库文件并写入一条记录。  
* **Task 1.3: 自动化发布脚本**  
  * **Spec**:  
    1. 编写 scripts/release.py。  
    2. 功能：接收参数 commit\_msg，自动更新 CHANGELOG，Bump Version，执行 Git Commit & Push。  
  * **Success Metric**: 调用脚本能完成一次模拟发布。

### **Phase 2: 单向下载链路 (Downstream Core)**

* **Task 2.1: 飞书 OAuth2 鉴权**  
  * **Spec**:  
    1. Backend: 实现 /auth/login (重定向) 和 /auth/callback。  
    2. Store: 将 access\_token 和 refresh\_token 加密存储在本地 DB 或 Keyring 中。  
    3. Frontend: 登录页，显示当前连接状态（Connected/Disconnected）。  
  * **Constraint**: 必须实现 Token 自动刷新拦截器 (Middleware)。  
* **Task 2.2: 递归目录爬虫 (Crawler)**  
  * **Spec**:  
    1. 实现 DriveService.scan\_folder(folder\_token)。  
    2. 逻辑：递归遍历飞书目录，构建内存中的文件树对象。  
    3. 优化：处理 API 分页 (page\_token)。  
  * **Success Metric**: 前端能以 Tree View 形式完整展示飞书云端目录。  
* **Task 2.3: 核心转码引擎 (Transcoder)**  
  * **Spec (High Complexity)**:  
    1. 必须采用 **TDD** 模式。先编写 tests/test\_transcoder.py，包含 H1/H2/Bold/Table/Image 的 JSON 样例。  
    2. 实现 DocxParser：将 Block JSON AST 转换为 Markdown AST。  
    3. Image Handler：下载图片到 data/assets/{doc\_id}/，并替换 Markdown 中的链接为相对路径。  
  * **Success Metric**: 单元测试覆盖率 \> 90%，转换后的 MD 渲染正常。  
* **Task 2.4: 本地写入与元数据同步 (Writer & Mtime)**  
  * **Spec**:  
    1. 实现 FileWriter。功能：将 Markdown 内容写入磁盘。  
    2. **Critical**: 调用 os.utime(path, (atime, mtime))，将本地文件的修改时间强制设置为云端的 edit\_time。这是为了防止同步后的文件被误判为“本地新修改”。  
  * **Success Metric**: 下载后的文件，在操作系统属性中显示的“修改时间”与飞书云端一致。  
* **Task 2.5: 非 Docx 文件处理 (Static Files)**  
  * **Spec**:  
    1. 识别非在线文档类型文件（如 PDF, Excel, Word, PPT, JPG）。  
    2. 直接调用 Drive download 接口下载原文件。  
    3. 跳过转码步骤，直接写入 data/ 目录。  
  * **Success Metric**: 飞书云端的 PDF 和 Excel 文件能原样同步到本地目录。

### **Phase 3: 双向监听与上传 (Upstream Core)**

* **Task 3.1: 本地文件系统监听 (Watcher)**  
  * **Spec**:  
    1. 集成 watchdog 库。  
    2. **Critical**: 实现 Debounce (防抖) 机制，窗口期 2秒，避免一次保存触发多次事件。  
    3. **Loop Prevention**: 实现“静默期”逻辑 —— 当 Task 2.4 执行写入操作时，暂停 Watcher 或在事件回调中通过文件 Hash 忽略本次变更，防止触发死循环。  
    4. Websocket: 将文件变动事件实时推送到前端 Log 面板。  
* **Task 3.2: 逆向解析与上传 (MD to Docx)**  
  * **Spec**:  
    1. 解析本地 Markdown 变更。  
    2. 策略 (MVP): 仅实现“全量覆盖”或“清空+追加”逻辑（飞书 Patch API 极其复杂，V1 先做覆盖）。  
    3. Rate Limit: 实现指数退避算法，遇到 429 错误自动重试。  
* **Task 3.3: 通用文件上传 (Generic Upload)**  
  * **Spec**:  
    1. 针对非 .md 文件（如 .xlsx, .pdf）的变动。  
    2. 调用 Drive resume\_upload (分片上传) 或 upload\_all 接口。  
    3. 上传完成后更新 DB 中的 file\_token。  
  * **Success Metric**: 本地放入一个 PDF 文件，能自动上传到飞书对应目录。

### **Phase 4: 交付与部署 (Deployment)**

* **Task 4.1: 冲突处理 UI**  
  * **Spec**:  
    1. Backend: 当 Hash(Local) \!= Hash(DB) 且 Ver(Cloud) \> Ver(DB) 时，标记为 Conflict。  
    2. Frontend: ConflictCenter 页面，左右分栏对比（Diff Viewer），提供 "Use Local" / "Use Cloud" 按钮。  
* **Task 4.2: Docker 生产环境**  
  * **Spec**:  
    1. 编写多阶段构建 Dockerfile。  
    2. Stage 1: Build React App \-\> /dist。  
    3. Stage 2: Python Backend。  
    4. Nginx: 配置反向代理，/api 转发给 Uvicorn，静态资源指向 /dist。

## **4\. 异常处理与自我修正 (Error Handling Protocol)**

**作为 AI，当你遇到以下情况时，必须按规定行动：**

1. **缺少 Context**: 如果任务需要具体的飞书 API 字段定义，而记忆库中没有，**立即停止**并请求用户提供具体的 JSON 响应样例。**严禁瞎编字段**。  
2. **API 限制**: 代码中必须显式包含 try...except 块来处理 API 网络错误和 Rate Limit。  
3. **依赖冲突**: 如果 npm install 或 pip install 失败，优先检查版本兼容性，并尝试自动修复 package.json / pyproject.toml。

## **5\. 数据结构参考 (Schema Reference)**

**SyncMapping Table (SQLAlchemy):**

class SyncMapping(Base):  
    \_\_tablename\_\_ \= "sync\_mappings"  
      
    doc\_token: str \= Column(String, primary\_key=True)  
    file\_hash: str \= Column(String, nullable=False)  \# SHA256 of local content  
    local\_path: str \= Column(String, unique=True, nullable=False)  
    cloud\_version: int \= Column(Integer, default=0)  
    last\_sync\_ts: float \= Column(Float, default=0.0)  
    status: str \= Column(String, default="synced") \# synced, dirty, conflict  

## **6\. 飞书云开发文档地址**

https://open.feishu.cn/document/home/index