# LarkSync v0.7.1

- 发布日期：2026-05-11
- 变更区间：v0.7.0 -> v0.7.1

## 本次更新明细

### 升级重点
- `v0.7.1-dev.1`：`DocxService` 在调用飞书 `blocks/convert` 前会把超过飞书建表行数限制的 Markdown 表格拆成多个原生表格，保留表头并避免触发表格创建失败。

### 详细变更

#### v0.7.1-dev.1
- `DocxService` 在调用飞书 `blocks/convert` 前会把超过飞书建表行数限制的 Markdown 表格拆成多个原生表格，保留表头并避免触发表格创建失败。
- 表格属性会根据 Markdown 单元格内容补齐 `column_width`，创建请求继续剥离 `cells/merge_info`，但保留合法列宽，改善默认窄表格显示。
- 表格创建失败的兜底逻辑改为“拆表重试 -> 普通文本兜底”，不再把表格包装成 fenced `markdown` 代码块。
- 用 `软件设计说明书-V1.5.md` 做本地 dry-run：原 118 个表格中 37 个超过 8 行，拆分后为 159 个表格，最大行数为 8。

## 安装包校验

| asset | sha256 |
| --- | --- |
| LarkSync-Setup-v0.7.1.exe | `5123bbf0d7527364a913eca4228e18e7e02bc3a5514eea20183680bcc9c5144f` |
