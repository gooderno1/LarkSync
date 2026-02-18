# Transcoder 内部覆盖基线

本文件用于记录 `Docx -> Markdown` 转码的内部回归覆盖点，避免后续只修“单点缺陷”。

## 回归入口

- 单测文件：`apps/backend/tests/test_transcoder.py`
- 下载回刷策略：`apps/backend/tests/test_sync_runner.py`
- 全量覆盖用例：`test_transcoder_internal_full_coverage_document`

## 覆盖清单

- 标题块：`heading1~heading9`
- 段落文本：`text_run` + 行内样式 + 链接
- 列表：无序 / 有序 / 待办（done/undone）
- 代码块：语言标识 + 多行内容
- 引用容器：`quote` / `callout` / `quote_container`
- 分割线：`divider`
- 表格：`table` / `table_cell`（含嵌套文本）
- 图片块：`image`（资源落盘）
- 附件块：`file`（attachments 落盘）
- 内嵌表格：`sheet`（优先转 Markdown 表格，失败回退 token 占位）
- 内嵌表格单元格：rich segment / mention link / formattedValue / formula / bool / number / 嵌套对象
- 插件块：`add_ons`（Mermaid / 文本兜底）
- 文本元素：`mention_doc` / `mention_user` / `reminder` / `equation`
- 视图容器：`block_type=33`（子块递归渲染）
- 历史产物修复：本地若仍含 `sheet_token` 占位，会跳过“云端未更新”短路并强制重转

## 执行命令

```bash
PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_transcoder.py -q
PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_sync_runner.py -q
```
