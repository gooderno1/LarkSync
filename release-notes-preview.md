# LarkSync v0.7.26

- 发布日期：2026-06-11
- 变更区间：v0.7.25 -> v0.7.26

## 本次更新明细

### 升级重点
- `v0.7.26-dev.1`：复现确认旧的 Markdown 图片正则只截取到第一个右括号，遇到 `assets/diagram (1).png` 这类文件名时会把路径截成 `assets/diagram (1`，再把残留 `.png)` 继续送入飞书 `blocks/convert`，导致图片无法被替换成占位符并可能触发 400。

### 详细变更

#### v0.7.26-dev.1
- 复现确认旧的 Markdown 图片正则只截取到第一个右括号，遇到 `assets/diagram (1).png` 这类文件名时会把路径截成 `assets/diagram (1`，再把残留 `.png)` 继续送入飞书 `blocks/convert`，导致图片无法被替换成占位符并可能触发 400。
- `DocxMarkdownAssetService` 已将本地图片和附件链接扫描改为括号感知解析，支持转义、嵌套标签、尖括号目标、标题和文件名中的成对括号；占位替换改为逐个替换，减少重复链接场景下的误替换风险。
- Markdown 列表缩进图片的规范化正则同步放宽到最后一个右括号，避免带括号图片路径在列表上下文中漏掉列表子项转换。
- `apps/backend/tests/test_docx_service.py` 新增带括号本地图片路径回归测试，确保 convert 前图片语法已被替换为 `LARKSYNC_IMAGE` 占位符。

## 安装包校验

| asset | sha256 |
| --- | --- |
| LarkSync-Setup-v0.7.26.exe | `dc10448cc713ab7f8382fb0aa36d1d65a8eebe3ecb831a609083b94fd307aa4e` |
