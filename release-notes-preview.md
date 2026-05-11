# LarkSync v0.7.3

- 发布日期：2026-05-12
- 变更区间：v0.7.2 -> v0.7.3

## 本次更新明细

### 升级重点
- `v0.7.3-dev.1`：`DocxService` 在补齐表格行列数和列宽后，会递归遍历表格 cell 内的文本类 block，仅对表格内部文本写入 `style.align=2`，不影响表格外正文。

### 详细变更

#### v0.7.3-dev.1
- `DocxService` 在补齐表格行列数和列宽后，会递归遍历表格 cell 内的文本类 block，仅对表格内部文本写入 `style.align=2`，不影响表格外正文。
- `SyncTaskRunner` 将超限表格渲染修复标记从 `#md-table-render-v2` 升级到 `#md-table-render-v3`，使已安装并运行过 `v0.7.2` 的用户在升级后仍能通过普通同步重新覆盖一次云端文档。
- 新增回归测试覆盖表格内部文本居中，以及已有旧 `#md-table-render-v2` 标记但本地 hash 未变化时仍不跳过同步。

## 安装包校验

| asset | sha256 |
| --- | --- |
| LarkSync-Setup-v0.7.3.exe | `7d696feb1779b1c25be4606256d5096b03e9716189a3d4251df4ad780e667430` |
