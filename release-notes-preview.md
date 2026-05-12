# LarkSync v0.7.4

- 发布日期：2026-05-12
- 变更区间：v0.7.3 -> v0.7.4

## 本次更新明细

### 升级重点
- `v0.7.4-dev.1`：移除 `DocxService` 中递归给表格 cell 内文本类 block 写入 `style.align=2` 的逻辑。

### 详细变更

#### v0.7.4-dev.1
- 移除 `DocxService` 中递归给表格 cell 内文本类 block 写入 `style.align=2` 的逻辑。
- 更新回归测试，锁定 Markdown 表格上传转换结果不会主动写入水平 `style.align`。
- `SyncTaskRunner` 将超限表格渲染修复标记从 `#md-table-render-v3` 升级到 `#md-table-render-v4`，使已安装并运行过 `v0.7.3` 的用户在升级后通过普通同步重新覆盖一次云端文档。

## 安装包校验

| asset | sha256 |
| --- | --- |
| LarkSync-Setup-v0.7.4.exe | `4f2ae2db2c0581634f23c3339ea424a509c94089171ec7f0efa356e7f26da592` |
