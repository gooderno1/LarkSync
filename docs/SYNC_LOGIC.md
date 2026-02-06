# LarkSync 同步逻辑说明

本文档描述 **当前实现** 的同步逻辑（与代码一致），用于排查“本地/云端谁更新”判断、接口调用次数与本地状态落库策略。

## 1. 触发方式与时间戳确认频率

- **云端 -> 本地**：每天 **01:00** 触发一次下载（本地时区），也支持手动“立即同步”。
- **本地 -> 云端**：每 **2 秒**触发一次上传周期（仅处理本地变更队列），并由 Watcher 负责捕获变更。
- **触发频率可配置**：
  - `upload_interval_seconds`：默认 2 秒。
  - `download_daily_time`：默认 `01:00`（24 小时制）。
- **时间戳确认频率**：
  - 每次下载/上传周期都会对本地/云端 mtime 进行一次比较。
  - Watcher 捕获到变动后，将路径加入“待上传队列”，待下一个周期处理。

## 2. 本地状态存档（数据库）

### 2.1 SyncLink（sync_links）
用于“本地路径 <-> 云端文件”的映射与**最近同步时间**记录。

- `local_path`：本地文件路径（主键）
- `cloud_token` / `cloud_type`
- `updated_at`：
  - **下载后**：写入云端 `modified_time`（用于判断“本地是否更新”）
  - **上传后**：写入本地文件 `mtime`（用于判断“是否重复上传”）

### 2.2 SyncBlockState（sync_block_states）
用于 Markdown 局部更新（partial）时的**块级状态**。

- 每个 Markdown 会拆分为块（paragraph/list/table/code 等）
- 存储：`block_hash`、`block_count`、`updated_at`、`file_hash`
- 作用：
  - 判断“内容是否变化”（当前文件 hash 是否与块状态一致）
  - 计算块级 diff，按块更新云端文档

## 3. 云端 -> 本地（下载流程）

### 3.1 流程概述

1. 递归扫描云端目录树（Drive API）。
2. 对每个文件计算云端 `modified_time`。
3. 若本地文件存在且 **本地 mtime > 云端 mtime + 1s**，判定“本地较新”，跳过下载。
4. Docx 走转码引擎生成 Markdown；普通文件直接下载。
5. 写入本地后，强制设置 mtime = 云端 `modified_time`。
6. 更新 `sync_links.updated_at = 云端 mtime`。
7. 若为双向/仅上传模式且 `update_mode != full`，重建块级状态（SyncBlockState）。

### 3.2 主要接口调用与次数（单次任务）

**目录扫描**
- `GET /open-apis/drive/explorer/v2/root_folder/meta`：1 次（获取根目录）
- `GET /open-apis/drive/v1/files`：每个文件夹分页 1 次（page_size=200）

**Docx 下载**
- `GET /open-apis/docx/v1/documents/{document_id}/blocks`：按 500 分页（= `ceil(blocks/500)`）
- 图片下载：
  - `GET /open-apis/drive/v1/medias/{file_token}/download`（优先）
  - 失败时回退 `GET /open-apis/drive/v1/files/{file_token}/download`
  - **每张图片 1 次**
- 附件下载：
  - `GET /open-apis/drive/v1/files/{file_token}/download`（优先）
  - 失败时回退 media download
  - **每个附件 1 次**

**普通文件下载**
- `GET /open-apis/drive/v1/files/{file_token}/download`：每个文件 1 次

## 4. 本地 -> 云端（上传流程）

### 4.1 Watcher 触发逻辑

- Debounce：**2 秒窗口**，同一路径重复事件只触发一次。
- 忽略机制（防循环）：当程序自己写入文件时，路径加入 **5 秒静默期**。
- 修复：对于“原子保存”（临时文件 -> rename）的场景，去抖和忽略**以 dest_path 为准**，避免漏掉真实变更。
- Watcher 只负责把变更路径加入“待上传队列”，真正的上传由 **2 秒周期调度**统一触发。

### 4.2 Markdown 文件上传

#### 4.2.1 新建场景（本地无映射）
1. 上传 Markdown 原文件到云端（普通文件上传）。
2. 创建 import_task（将 .md 转为 Docx）。
3. 轮询云端目录，获取新文档 token。
4. 建立 `sync_links` 映射。

**接口调用**
- `POST /open-apis/drive/v1/files/upload_all`（小文件）或分片上传三步：
  - `POST /open-apis/drive/v1/files/upload_prepare`
  - `POST /open-apis/drive/v1/files/upload_part`（按分片次数）
  - `POST /open-apis/drive/v1/files/upload_finish`
- `POST /open-apis/drive/v1/import_tasks`：1 次
- `GET /open-apis/drive/v1/files`：最多 10 次（轮询查找新 doc，间隔 1s）

#### 4.2.2 更新场景（已有映射）
支持 `update_mode = auto / partial / full`。

**partial / auto（块级更新）**
- 按 Markdown block 计算 diff，仅更新变化块。
- 若块级映射不一致，自动 bootstrap 重建基线后再尝试。

**接口调用（按变化块数量）**
- 每个变化块：
  - `POST /open-apis/docx/v1/documents/blocks/convert`：1 次（把 Markdown block 转为 blocks）
  - `POST /open-apis/docx/v1/documents/{document_id}/blocks/{root_block_id}/children`：1 次（创建新块，可能分 chunk）
  - 删除旧块：`DELETE /open-apis/docx/v1/documents/{document_id}/blocks/{root_block_id}/children/batch_delete`（按 50 一批）
- 图片/附件：
  - 图片：`POST /open-apis/drive/v1/medias/upload_all` + `PATCH /open-apis/docx/v1/documents/{document_id}/blocks/{block_id}`
  - 附件：`POST /open-apis/drive/v1/files/upload_all`（或分片） + `PATCH /open-apis/docx/v1/documents/{document_id}/blocks/{block_id}`

**full（全量覆盖）**
1. 读取当前文档 blocks。
2. 全量 convert -> create 新块。
3. 删除旧块。

**接口调用**
- `GET /open-apis/docx/v1/documents/{document_id}/blocks`：按 500 分页
- `POST /open-apis/docx/v1/documents/blocks/convert`：1 次（整篇）
- `POST /open-apis/docx/v1/documents/{document_id}/blocks/{root_block_id}/children`：按块 chunk 数量
- `DELETE /open-apis/docx/v1/documents/{document_id}/blocks/{root_block_id}/children/batch_delete`：按 50 一批
- 图片/附件上传与 patch 同上

### 4.3 非 Markdown 文件上传

- 直接按文件上传（upload_all 或分片上传）
- 写入 `sync_links.updated_at = 本地 mtime`

## 5. “谁更新谁”的判断规则

- **下载阶段**：若 `local_mtime > cloud_mtime + 1s`，视为本地较新，跳过下载。
- **上传阶段**：
  - 若有块级状态，优先比对 `file_hash` 与 block_state；
  - 若无块级状态，则使用 `mtime <= updated_at + 1s` 作为“未修改”的判断阈值。

## 6. 关键参数（当前实现）

- Watcher debounce：2 秒
- Watcher ignore（静默期）：5 秒
- import_task 轮询：最多 10 次，每次 1 秒
- Docx list_blocks page_size：500
