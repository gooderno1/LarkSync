# **LarkSync飞书云文档与本地文件系统双向同步系统：技术可行性深度调研与产品需求规格说明书**

## **1\. 执行摘要**

本报告旨在详尽阐述构建一套连接飞书（Feishu/Lark）云端文档生态与本地文件系统的双向同步程序的技术方案、架构设计及产品需求。该系统的核心目标是打破云端协作平台与本地工作流之间的数据孤壁，通过智能化的格式转换引擎和健壮的同步算法，实现飞书云文档（Docx）与本地Markdown文件的无缝互通，同时支持多设备间的一致性维护及元数据同步。

针对用户提出的核心需求——即多设备双向同步、最终修改时间同步、灵活的同步模式（仅下载/双向）以及非MD文件的格式自动转换——本报告进行了深入的技术调研。分析显示，利用飞书开放平台提供的 Drive v1 和 Docx v1 API，结合本地 SQLite 状态数据库和文件系统监听机制，该方案在技术上具备高度可行性。然而，实现过程中需重点解决云端与本地文件系统在元数据定义上的差异（特别是修改时间戳的不可变性）、API 速率限制（Rate Limiting）带来的吞吐量瓶颈，以及Markdown语法与飞书丰富富文本块（Blocks）之间的有损/无损转换难题。

本报告包含完整的技术架构设计、核心算法逻辑、详细的功能列表（Feature List）以及参考PRD文档，为开发团队提供从设计到实施的全链路指导。

## **2\. 背景与需求分析**

### **2.1 项目背景**

在现代企业的数字化办公场景中，飞书文档凭借其强大的实时协作能力和丰富的块（Block）生态，已成为知识沉淀的核心载体。然而，对于开发者、技术文档撰写者以及习惯使用本地IDE（如 Obsidian, VS Code）的用户而言，纯云端的存储方式存在一定的局限性。用户希望拥有数据的本地所有权，利用本地工具链进行编辑，同时又能利用飞书的协作能力。目前市场上缺乏一款能够完美映射“飞书云文档”与“本地Markdown”的双向同步工具，这构成了本项目的核心价值主张。

### **2.2 核心业务需求拆解**

根据用户陈述，本项目需满足以下关键业务场景：

1. **双向数据流通（Bi-directional Sync）：** 数据流并非单向备份，而是双向互通。本地的修改需实时（或近实时）反馈至云端，云端的协作修改也需同步回本地 1。  
2. **异构格式桥接（Format Bridging）：**  
   * **Docx to Markdown：** 飞书原生的新版文档（Docx）需在下载过程中实时转码为标准 Markdown 格式 3。  
   * **Markdown to Docx：** 本地 Markdown 文件上传时，需解析为飞书文档结构，而非作为普通附件存储。  
   * **其他格式转换：** 用户特别指定，非 MD 格式文件（如 Word, Excel）在上传时应尽可能转换为飞书在线文档格式（Doc/Sheet），以利用云端协作功能 5。  
3. **多端拓扑支持（Multi-Device Support）：** 系统需支持在不同设备（如公司台式机、个人笔记本）上运行，并将云端作为中心节点（Hub），实现多设备间的文件一致性。这意味着本地状态数据库必须独立于设备存在，且能正确处理并发冲突。  
4. **元数据高保真（Metadata Fidelity）：** 系统需同步“最终修改时间”，确保用户在查看文件列表时能准确判断文件的新旧程度 7。  
5. **灵活的同步策略（Sync Modes）：**  
   * **仅下载模式（Download Only）：** 适用于归档、备份场景，单向从云端拉取，防止本地误操作覆盖云端数据。  
   * **双向同步模式（Two-way Sync）：** 适用于高频协作场景。

## **3\. 飞书开放平台技术调研与可行性分析**

为实现上述目标，必须深度依赖飞书开放平台提供的服务端 API。以下是对关键能力模块的深度调研分析。

### **3.1 鉴权与权限体系（Authentication & Scopes）**

要实现对用户个人云空间的访问，程序必须以正确的身份接入。

* **身份选择：** 必须使用 user\_access\_token（用户访问凭证）而非 tenant\_access\_token（租户/应用访问凭证）。这是因为同步操作是代表特定用户进行的，涉及该用户“我的空间”（My Space）下的私人文件及具有特定权限的共享文件。使用 tenant\_access\_token 虽权限更广，但无法精准映射用户的个人视角，且存在安全隐患 9。  
* **权限范围（Scopes）：** 根据最小权限原则与功能需求，必须申请以下权限 9：  
  * drive:drive：查看、评论、编辑和管理云空间的所有文件（核心读写权限）。  
  * docs:doc：查看、评论、编辑和管理文档（用于 Docx 内容读写）。  
  * drive:meta：查看云空间文件的元数据（用于获取修改时间戳）。  
  * contact:contact.base:readonly：获取用户基本信息（用于记录最后修改者身份）。

### **3.2 Drive API：文件系统的骨架**

Drive API 是管理文件夹结构和文件实体的基础。

#### **3.2.1 文件夹结构的递归与映射**

飞书云盘采用基于 token 的节点索引机制，而非传统文件系统的路径（Path）索引 14。

* **根节点获取：** 通过 GET /open-apis/drive/explorer/v2/root\_folder/meta 获取用户“我的空间”根目录的 folder\_token 15。  
* **子节点遍历：** 使用 GET /open-apis/drive/v1/files 列出指定文件夹下的子节点。  
  * **技术挑战：** 该接口仅返回单层结构，且存在分页限制（默认 50，最大 200）。  
  * **解决方案：** 系统必须实现一个**递归爬虫（Recursive Crawler）**。对于每个文件夹，通过 page\_token 循环获取所有子文件，建立内存中的目录树结构，并将其映射到本地文件系统的物理路径。  
  * **限制因素：** 单层文件夹节点上限为 1500 个 16，全空间节点总数限制（虽极高但需注意）。爬虫需具备深度优先或广度优先的遍历策略，并建立本地缓存以加速后续扫描。

#### **3.2.2 元数据同步：修改时间的难题**

用户明确要求“同步最终修改时间”。这在技术实现上存在显著的不对称性。

* **云端 \-\> 本地：** 可行。通过 GET /open-apis/drive/v1/metas/batch\_query 接口可以获取文件的 latest\_modify\_time（Unix时间戳） 7。同步程序在写入本地文件后，可调用操作系统 API（如 Python 的 os.utime）强制修改本地文件的 mtime 和 atime 以匹配云端时间。  
* **本地 \-\> 云端：** **存在阻碍**。根据调研，飞书以及大多数云盘 API（如 Google Drive API）在上传文件或更新内容时，会自动将 latest\_modify\_time 设置为服务器接收请求的当前时间，通常**不支持**客户端自定义该字段 8。  
  * **影响：** 如果本地有一个旧文件（修改于 2023-01-01）被上传，云端会显示修改于“刚刚”。这可能导致其他设备误判为新文件而重新下载。  
  * **解决方案：** 必须构建一个**中间状态数据库（State Database）**。同步判断逻辑不能仅依赖云端返回的时间戳，而应依赖“最后一次同步时的云端时间戳快照”。当本地上传触发时，数据库记录下“上传完成时的服务器时间”作为基准，以此屏蔽时间戳重置带来的逻辑干扰。

#### **3.2.3 文件下载与上传**

* **普通文件（PDF/Image/Zip）：**  
  * 下载：GET /open-apis/drive/v1/files/:file\_token/download 11。  
  * 上传：小文件使用 files/upload\_all 19，大文件（\>20MB）使用分片上传接口 20。  
* **飞书文档（Docx）：** 无法直接下载为二进制文件，需调用特定内容接口（见 3.3 节）。

### **3.3 Docx API：内容转码的核心**

这是本项目的技术深水区。用户要求 Docx 默认为 MD，这要求程序充当即时翻译器。

#### **3.3.1 Docx 转 Markdown（下载方向）**

飞书并未提供直接导出为 Markdown 的官方 API（仅支持导出为 PDF/Word/Excel 9）。因此，必须基于 **Block（块）** 结构进行自行解析。

* **获取内容：** 使用 GET /open-apis/docx/v1/documents/:document\_id/blocks 获取文档的所有块结构 22。  
* **解析逻辑：**  
  * **文本块（Text）：** 需解析 text\_run 中的 style 属性（加粗、斜体、下划线），转换为 Markdown 的 \*\*bold\*\*, \*italic\* 语法。  
  * **标题块（Heading 1-9）：** 转换为 \# Heading。  
  * **代码块（Code）：** 转换为 \`\`\`language... \`\`\`。  
  * **列表（List）：** 处理嵌套层级，转换为 \- 或 1\. 。  
  * **图片（Image）：** 图片在 Block 中仅体现为 image\_token。程序必须额外调用 drive/v1/media/:file\_token/download 接口下载图片实体 11，将其保存到本地的 assets/ 文件夹，并在 Markdown 中生成相对路径引用 \!\[alt\](assets/image\_token.png) 4。  
  * **表格（Table）：** 飞书表格支持合并单元格，而标准 Markdown 表格不支持。这是一个**有损转换**点。策略是尽最大努力转换为 HTML 表格或简化的 MD 表格，或者在 PRD 中明确告知用户复杂表格可能显示异常。

#### **3.3.2 Markdown 转 Docx（上传方向）**

用户要求“其他格式文件可以的话都转为飞书文档上传”。

* **新建文档：** 使用 POST /open-apis/drive/v1/import\_tasks 接口。该接口极其强大，支持将本地的 .md, .docx, .xlsx, .csv, .txt 直接导入并转换为飞书在线文档（Docx, Sheet, Bitable） 5。  
  * *优势：* 服务端负责渲染，兼容性好。  
  * *劣势：* 这是一个异步接口，需轮询任务结果获取新的 token。  
* **更新文档：** 这是一个复杂点。import\_tasks 每次都会生成一个新的 token（即新文件）。若要实现“修改同一份文档”，不能简单使用导入接口。  
  * **方案 A（推荐）：** 若本地 Markdown 发生变更，读取其内容，解析为飞书 Block 结构，通过 docx/v1/documents/:document\_id/blocks 接口进行**增量更新**或**全量替换**（先清空旧 Block 再插入新 Block） 27。这能保持云端文档 Token 不变，保留评论和分享链接。  
  * **方案 B（妥协）：** 如果全量替换技术难度过高，可选择删除旧文档，导入新文档（Token 会变）。这会丢失历史记录和协作评论，仅适用于“个人备份”场景，不推荐用于“双向协作”。**本方案设计采用方案 A。**

### **3.4 实时性与事件监听（Webhooks）**

仅依靠轮询（Polling）无法做到实时同步且容易触发 API 频率限制。飞书提供基于 Webhook 的事件订阅机制 29。

* **关键事件：**  
  * drive.file.created\_in\_folder\_v1：感知云端新建文件。  
  * drive.file.edit\_v1：感知云端文档内容被修改。  
  * drive.file.title\_updated\_v1：感知重命名。  
  * drive.file.deleted\_v1：感知删除。  
* **本地客户端挑战：** 本地电脑通常没有公网 IP，无法直接接收飞书服务器的 Webhook 推送。  
* **技术对策：**  
  1. **长轮询（Long Polling）：** 如果飞书 SDK 支持长连接模式（如部分 IM 场景），可采用此法。  
  2. **高频轮询（High-frequency Polling）：** 对于 Drive API，通常采用增量同步策略。虽然不是纯实时，但每隔 1-5 分钟扫描一次变更集是行业标准做法。  
  3. **WebSocket 网关：** 高级方案，搭建一个公网中转服务，将 Webhook 转发为 WebSocket 消息推送到本地客户端。考虑到本程序的设计初衷是“独立程序”，建议优先采用**智能轮询**策略（结合 last\_modified\_time 过滤），避免过度依赖外部中转架构。

## **4\. 系统详细架构设计**

### **4.1 总体架构图 (Conceptual Architecture)**

系统采用模块化分层设计，确保各功能组件解耦。

代码段

graph TD  
    User\[用户\] \--\> UI\[用户交互层 (CLI/GUI)\]  
    UI \--\> Controller\[同步控制器\]  
      
    subgraph Core\_Engine \[核心引擎\]  
        Controller \--\> Watcher\[本地文件监听器\]  
        Controller \--\> Poller\[云端变更轮询器\]  
        Controller \--\> ConflictMgr\[冲突解决管理器\]  
        Controller \--\> Transcoder\[格式转码引擎\]  
    end  
      
    subgraph Data\_Layer \[数据持久层\]  
        StateDB  
        Config\[配置文件\]  
    end  
      
    subgraph Network\_Layer \[网络交互层\]  
        API\_Client\[飞书 API 客户端\]  
        RateLimiter\[速率限制器\]  
        AuthMgr\[令牌管理器\]  
    end  
      
    Core\_Engine \--\> Data\_Layer  
    Core\_Engine \--\> Network\_Layer  
      
    Watcher \-- 文件系统事件 \--\> Local\_FS\[本地文件系统\]  
    API\_Client \-- HTTPS \--\> Lark\_Cloud\[飞书开放平台\]

### **4.2 核心模块详解**

#### **4.2.1 状态数据库（State Database）**

为了实现“多设备同步”和“元数据对齐”，不能仅依赖文件系统本身。必须引入一个轻量级的 SQLite 数据库来记录同步状态。

**表结构设计：sync\_mapping**

| 字段名 | 类型 | 描述 | 关键用途 |
| :---- | :---- | :---- | :---- |
| id | INT | 主键 |  |
| cloud\_token | TEXT | 飞书文件的唯一标识 | 关联云端实体，即使重命名也能追踪 |
| local\_path | TEXT | 本地相对路径 | 关联本地实体 |
| last\_sync\_time | BIGINT | 最后一次同步的时间戳 | 用于冲突检测基准 |
| file\_hash | TEXT | 文件内容哈希 (MD5/SHA256) | 用于检测本地文件内容是否发生实质变化 |
| cloud\_version | INT | 云端版本号/Revision ID | 用于乐观锁控制，防止覆盖新版本 |
| sync\_mode | TEXT | 'download\_only' / 'bidirectional' | 文件夹级别的策略控制 |
| file\_type | TEXT | 'docx', 'sheet', 'file' | 决定调用哪个转码器 |

#### **4.2.2 格式转码引擎（Transcoder Engine）**

该模块包含两套流水线：

1. **Downstream (Cloud \-\> Local):**  
   * 输入：Docx Block JSON  
   * 处理：遍历 AST（抽象语法树），匹配 Markdown 语法规则。  
   * 特殊处理：提取所有 image block，生成下载任务放入队列，下载完成后替换 AST 中的占位符为本地相对路径。  
   * 输出：.md 文件 \+ assets/ 图片文件。  
2. **Upstream (Local \-\> Cloud):**  
   * 输入：.md 文件  
   * 处理：使用 Markdown Parser（如 Python 的 mistune 或 JS 的 remark）生成 AST。  
   * 转换：将 Markdown AST 映射为 Feishu Block Spec。  
   * 特殊处理：识别本地图片引用，先调用 Media Upload API 上传图片获得 image\_token，再构建 Image Block。  
   * 输出：Feishu Block JSON 列表，发送给 API。

#### **4.2.3 速率限制器（Rate Limiter）**

飞书 API 有严格的频率限制（如 Drive API 写操作通常限制为 5 QPS 19）。

* **令牌桶算法（Token Bucket）：** 实现一个本地限流器，严格控制请求发送速率。  
* **指数退避（Exponential Backoff）：** 遇到 1061045 (Frequency Limit) 错误时，自动休眠 2^n 秒后重试。  
* **优先级队列：** 用户发起的保存操作优先级高于后台的自动轮询。

#### **4.2.4 冲突解决管理器（Conflict Manager）**

在双向同步中，冲突不可避免（例如：断网期间本地和云端都修改了同一文件）。

* **策略：** 只有当 local\_hash\!= db.last\_hash 且 cloud\_version \> db.last\_version 时，才判定为冲突。  
* **默认行为（保全数据）：**  
  1. 将本地文件重命名为 filename (Conflicted copy YYYY-MM-DD).md。  
  2. 下载云端最新版本覆盖原文件名。  
  3. 通知用户手动合并。  
* **逻辑依据：** 云端协作通常涉及多人，权重高于本地单人修改。

## **5\. 关键技术难点与解决方案**

### **5.1 循环同步陷阱 (The Loop Trap)**

**问题：** 本地上传文件 \-\> 触发本地 Watcher \-\> 再次上传；或者，本地上传后云端版本号变更 \-\> 触发云端 Poller \-\> 误判为云端更新 \-\> 重新下载覆盖本地。

**解决：**

1. **上传静默期：** 程序在执行上传操作时，将该文件路径加入 ignore\_list，本地 Watcher 在 5 秒内忽略该文件的变更事件。  
2. **版本锚点：** 上传成功后，API 会返回最新的 cloud\_version。程序必须**立即**原子性地更新本地 DB 的 cloud\_version 和 file\_hash。在下一次轮询时，如果 API 返回的版本号与 DB 中记录的一致，即使时间戳更新，也视为“已同步”，不触发下载。

### **5.2 文件夹层级递归性能**

**问题：** 飞书限制单层 1500 节点，且总文件数可能数万。递归查询会导致启动极慢。

**解决：**

1. **增量扫描：** 首次运行进行全量扫描。后续运行利用 changes 接口（如果存在类似 Google Drive 的 Changes API，飞书暂未完全开放此类全局变更流，需依赖各文件夹的 edit\_time）。  
2. **本地缓存优先：** 启动时信任本地 DB 结构，后台异步线程与云端进行比对（Reconciliation），UI 先展示本地状态。

### **5.3 异构文件上传转换**

**问题：** 用户希望将 Word/Excel 转为在线文档。

**解决：** 利用 import\_tasks API。

* 当 Watcher 监测到新增 .xlsx 文件：  
  1. 调用 drive/v1/import\_tasks，指定 file\_extension='xlsx', type='sheet'。  
  2. 轮询任务状态。  
  3. 任务成功后，获得新的 spreadsheet\_token。  
  4. **关键步骤：** 删除云端的原 .xlsx 源文件（通常导入后源文件会保留），或者将其移动到“源文件备份”目录，以避免云端同时存在一个 Sheet 和一个 Excel 文件导致混乱。

## **6\. 功能列表 (Feature List)**

根据调研结果，以下是按优先级排序的功能清单，符合软件工程交付标准。

### **6.1 核心同步模块 (Core Sync)**

| ID | 功能名称 | 优先级 | 描述 | 技术依赖 |
| :---- | :---- | :---- | :---- | :---- |
| **F-SYNC-01** | **账户授权登录** | P0 | 支持 OAuth 2.0 流程，获取并安全存储 user\_access\_token 及 refresh\_token。 | Auth API |
| **F-SYNC-02** | **同步任务配置** | P0 | 用户可创建多个同步任务，每个任务绑定一对 \[本地文件夹 \<-\> 云端文件夹\]。 | Config Mgr |
| **F-SYNC-03** | **模式选择** | P0 | 每个同步任务可独立配置为“仅下载（备份）”或“双向同步”。 | Sync Logic |
| **F-SYNC-04** | **目录树镜像** | P0 | 递归创建本地/云端文件夹，保持层级结构完全一致。 | Drive API |
| **F-SYNC-05** | **文件删除同步** | P1 | 本地删除 \-\> 云端放入回收站；云端删除 \-\> 本地移动到系统回收站（防误删）。 | Delete API |
| **F-SYNC-06** | **冲突处理** | P1 | 检测版本冲突，自动创建副本并重命名，保证数据不丢失。 | Conflict Logic |
| **F-SYNC-07** | **多设备状态隔离** | P1 | 基于 DeviceID 区分不同设备的同步状态，允许多机协作。 | DB Schema |

### **6.2 格式转换模块 (Format Transcoder)**

| ID | 功能名称 | 优先级 | 描述 | 技术依赖 |
| :---- | :---- | :---- | :---- | :---- |
| **F-FMT-01** | **Docx 转 Markdown** | P0 | 下载时将 Docx 解析为.md 文件，支持标题、粗体、列表、代码块。 | Block Parser |
| **F-FMT-02** | **图片资源本地化** | P0 | 自动下载文档内的图片至 assets 目录，并修正 Markdown 图片链接。 | Media API |
| **F-FMT-03** | **Markdown 转 Docx** | P1 | 上传.md 文件时，解析为 Block 结构写入云端文档，而非作为附件上传。 | Import/Block API |
| **F-FMT-04** | **Office 格式导入** | P1 | 上传 Word/Excel/CSV 时，自动调用导入接口转换为 Docx/Sheet/Bitable。 | Import API |
| **F-FMT-05** | **原生文件透传** | P0 | 对不支持转换的格式（PDF, ZIP, MP4），直接以二进制流形式同步。 | Stream Upload |

### **6.3 辅助功能 (Auxiliary)**

| ID | 功能名称 | 优先级 | 描述 | 技术依赖 |
| :---- | :---- | :---- | :---- | :---- |
| **F-AUX-01** | **系统托盘运行** | P2 | 程序最小化至托盘，后台静默同步。 | GUI Lib |
| **F-AUX-02** | **同步日志** | P2 | 记录详细的文件操作日志（上传/下载/冲突/错误），便于排查。 | Logging |
| **F-AUX-03** | **速率控制** | P1 | 遵守飞书 QPS 限制，实现请求队列和自动重试。 | Rate Limiter |
| **F-AUX-04** | **元数据修正** | P1 | 下载后强制修改本地文件 mtime 以匹配云端最后修改时间。 | OS API |

## **7\. 产品需求文档 (PRD)**

### **7.1 产品概述**

**产品名称：** LarkSync (飞书同步助手)

**版本：** V1.0

**愿景：** 为飞书用户提供极致流畅的本地化文档管理体验，让知识在云端与本地间自由流动。

### **7.2 用户画像 (User Personas)**

* **开发者 (Alex)：** 习惯使用 VS Code 编写技术文档，希望本地 Markdown 代码库能自动同步到公司飞书 Wiki，供团队查阅。  
* **项目经理 (Sarah)：** 需要备份团队的所有项目文档（Docx/Sheet）到本地硬盘，以便离线时查阅或归档，防止云端误删。  
* **设计师 (Mike)：** 经常产生大量素材图片和 PDF，希望拖入本地文件夹后，自动出现在飞书项目云盘中供全员下载。

### **7.3 功能性需求 (Functional Requirements)**

#### **7.3.1 初始化与配置**

* **REQ-01:** 用户首次启动需通过浏览器完成飞书 OAuth 授权。  
* **REQ-02:** 用户点击“新建同步”时，需弹窗选择：  
  * 云端源（展示云盘目录树供选择）。  
  * 本地目标（调用系统文件夹选择器）。  
  * 同步模式（单选框：仅下载 / 双向同步）。  
  * 转换选项（复选框：自动将 Office 文件转换为在线文档）。

#### **7.3.2 运行态逻辑**

* **REQ-03 (下载流):**  
  * 系统应定时（默认每5分钟）检查云端变更。  
  * 若发现云端 Docx 更新，需下载并转换为 Markdown。  
  * 若 Docx 包含图片，图片需下载至同级 assets/ 目录。  
  * 下载完成后，本地文件修改时间需更新为云端 latest\_modify\_time。  
* **REQ-04 (上传流):**  
  * 系统应监听本地文件系统事件（Create, Modify, Move, Delete）。  
  * 新增 .md 文件应作为新建 Docx 上传。  
  * 新增 .docx/.xlsx 文件，若开启转换选项，应调用导入接口；否则作为附件上传。  
  * 本地重命名文件，云端应对应重命名（不删除重建），以保留文件 Token。

#### **7.3.3 异常处理**

* **REQ-05:** 当 API 返回 429 (Too Many Requests) 时，系统必须停止请求并显示“正在等待服务器限流恢复”，不得崩溃。  
* **REQ-06:** 当遇到无法转换的 Markdown 语法（如复杂 HTML 标签），系统应保留原始内容文本，并在日志中记录警告，不应中断同步。

### **7.4 非功能性需求 (Non-functional Requirements)**

* **性能：** 支持管理包含 10,000+ 个文件的目录树，内存占用不超过 500MB。  
* **兼容性：** 支持 Windows 10/11 及 macOS (Intel/M-series)。  
* **安全性：** access\_token 必须加密存储（使用 OS KeyChain 或类似机制）。所有通信必须强制 HTTPS。

## **8\. 结论与建议**

构建该双向同步程序在技术上是完全可行的，飞书开放平台提供了必要的 API 积木。然而，项目的成败关键在于细节处理：

1. **投入重兵研发“转码器”：** Markdown 与 Docx 的互转不是简单的正则替换，需要构建健壮的 AST 转换层，这是用户体验的核心。  
2. **拥抱“最终一致性”：** 由于 API 限制和网络延迟，不要追求毫秒级的实时同步，而应追求数据的最终一致性和安全性（不丢数据）。  
3. **利用 SQLite 作为单一事实来源：** 在云端时间戳不可控的情况下，本地数据库的状态记录是判断同步方向的唯一可靠依据。

建议第一阶段（MVP）先实现“仅下载模式”及“Markdown 导出”功能，验证转码效果及性能，随后在第二阶段引入双向同步及冲突解决机制。

---

**附录：数据表设计参考**

SQL

CREATE TABLE sync\_state (  
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    cloud\_token TEXT NOT NULL,       \-- 飞书文件 Token  
    local\_path TEXT NOT NULL,        \-- 本地相对路径  
    last\_sync\_time INTEGER,          \-- 最后同步时的 Unix 时间戳  
    cloud\_version TEXT,              \-- 云端版本标识  
    file\_hash TEXT,                  \-- 本地文件内容 Hash  
    is\_dir BOOLEAN DEFAULT 0,        \-- 是否文件夹  
    sync\_root\_id INTEGER,            \-- 所属同步任务 ID  
    UNIQUE(cloud\_token, sync\_root\_id),  
    UNIQUE(local\_path, sync\_root\_id)  
);

#### **引用的著作**

1. Bi-Directional Sync Explained: 3 Real-World Examples \- Stacksync, 访问时间为 一月 26, 2026， [https://www.stacksync.com/blog/bi-directional-sync-explained-3-real-world-examples](https://www.stacksync.com/blog/bi-directional-sync-explained-3-real-world-examples)  
2. Building bi-directional sync between two system \- Marcel Krčah, 访问时间为 一月 26, 2026， [https://marcel.is/bidirectional-sync/](https://marcel.is/bidirectional-sync/)  
3. Get docs content \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/docs-v1/content/get](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/docs-v1/content/get)  
4. I open-sourced feishu-docx: A tool to bridge Feishu/Lark cloud documents with AI Agents, 访问时间为 一月 26, 2026， [https://www.reddit.com/r/opensource/comments/1qap5pg/i\_opensourced\_feishudocx\_a\_tool\_to\_bridge/](https://www.reddit.com/r/opensource/comments/1qap5pg/i_opensourced_feishudocx_a_tool_to_bridge/)  
5. Upload or import local files and folders, 访问时间为 一月 26, 2026， [https://www.feishu.cn/hc/en-US/articles/360033241654-upload-or-import-local-files-and-folders](https://www.feishu.cn/hc/en-US/articles/360033241654-upload-or-import-local-files-and-folders)  
6. Create an import task \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/server-docs/docs/drive-v1/import\_task/create](https://open.feishu.cn/document/server-docs/docs/drive-v1/import_task/create)  
7. Obtain Metadata \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uMjN3UjLzYzN14yM2cTN](https://open.feishu.cn/document/ukTMukTMukTM/uMjN3UjLzYzN14yM2cTN)  
8. Preserve original file timestamps when uploading to Google Drive API Android, 访问时间为 一月 26, 2026， [https://community.latenode.com/t/preserve-original-file-timestamps-when-uploading-to-google-drive-api-android/32859](https://community.latenode.com/t/preserve-original-file-timestamps-when-uploading-to-google-drive-api-android/32859)  
9. Create an export task \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/server-docs/docs/drive-v1/export\_task/create](https://open.feishu.cn/document/server-docs/docs/drive-v1/export_task/create)  
10. API Explorer Guide \- Developer Guides \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/api-explorer](https://open.feishu.cn/api-explorer)  
11. Introduction \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.larkoffice.com/document/server-docs/docs/drive-v1/media/introduction](https://open.larkoffice.com/document/server-docs/docs/drive-v1/media/introduction)  
12. Obtain Metadata \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/meta/batch\_query](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/meta/batch_query)  
13. Apply for API permissions \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/server-docs/application-scope/introduction](https://open.feishu.cn/document/server-docs/application-scope/introduction)  
14. List items in folder \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/server-docs/docs/drive-v1/folder/list](https://open.feishu.cn/document/server-docs/docs/drive-v1/folder/list)  
15. Folder overview \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/docs/drive-v1/folder/folder-overview](https://open.feishu.cn/document/docs/drive-v1/folder/folder-overview)  
16. Cloud space overview \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/files/guide/introduction](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/files/guide/introduction)  
17. Keep modified time of file upon insert into Google Drive API on Android \- Stack Overflow, 访问时间为 一月 26, 2026， [https://stackoverflow.com/questions/12256055/keep-modified-time-of-file-upon-insert-into-google-drive-api-on-android](https://stackoverflow.com/questions/12256055/keep-modified-time-of-file-upon-insert-into-google-drive-api-on-android)  
18. Download a file \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/download](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/download)  
19. Upload a file \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uUjM5YjL1ITO24SNykjN](https://open.feishu.cn/document/ukTMukTMukTM/uUjM5YjL1ITO24SNykjN)  
20. Upload a file in blocks-Preuploading \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/upload\_prepare](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/upload_prepare)  
21. Upload a file in blocks-Uploading \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/server-docs/docs/drive-v1/upload/multipart-upload-file-/upload\_part](https://open.feishu.cn/document/server-docs/docs/drive-v1/upload/multipart-upload-file-/upload_part)  
22. Block data structure \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/data-structure/block](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/data-structure/block)  
23. Document overview \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/docx-overview](https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/docx-overview)  
24. Introduction \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/media/introduction](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/media/introduction)  
25. leemysw/feishu-docx: Feishu/Lark Docs、Sheet、Bitable → Markdown | AI Agent-friendly knowledge base exporter with OAuth 2.0, CLI, TUI & Claude Skills support \- GitHub, 访问时间为 一月 26, 2026， [https://github.com/leemysw/feishu-docx](https://github.com/leemysw/feishu-docx)  
26. Import file overview \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/import\_task/import-user-guide](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/import_task/import-user-guide)  
27. Document FAQs \- Server API \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/faq](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/faq)  
28. Convert Markdown/HTML content into blocks \- Server API \- Documentation, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/document/convert](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/document/convert)  
29. Event list \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-list](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-list)  
30. File title updated \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/event/file-title-update](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/event/file-title-update)  
31. File created in folder \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/docs/drive-v1/event/list/created\_in\_folder](https://open.feishu.cn/document/docs/drive-v1/event/list/created_in_folder)  
32. Upload a file \- Server API \- Documentation \- Feishu Open Platform, 访问时间为 一月 26, 2026， [https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/upload\_all](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/upload_all)