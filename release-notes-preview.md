# LarkSync v0.7.25

- 发布日期：2026-05-31
- 变更区间：v0.7.24 -> v0.7.25

## 本次更新明细

### 升级重点
- `v0.7.25-dev.1`：通过失败日志确认，`replace_document_content()` 在已经持有根块 `children` 数量时仍调用 `create_from_convert(... current_root_children_count=None)`，导致写入前额外执行一次 `GET /blocks`；这会在使用固定假响应序列的 `tests/test_docx_service.py` 中打乱后续 `create / upload / delete` 响应顺序，也让真实运行多一次无意义请求。

### 详细变更

#### v0.7.25-dev.1
- 通过失败日志确认，`replace_document_content()` 在已经持有根块 `children` 数量时仍调用 `create_from_convert(... current_root_children_count=None)`，导致写入前额外执行一次 `GET /blocks`；这会在使用固定假响应序列的 `tests/test_docx_service.py` 中打乱后续 `create / upload / delete` 响应顺序，也让真实运行多一次无意义请求。
- `DocxContentWriteService.replace_document_content()` 现会把 `remaining_old_children` 直接传给 `create_from_convert()`，既复用当前上下文，也让全量替换与之前新增的失败回滚逻辑保持一致。
- `tests/test_docx_service.py` 的 `test_insert_markdown_block_creates_children_at_index` 已改为显式覆盖“先 convert，再取根块 children，再插入”的当前调用顺序；配合前述代码修复，整组 `DocxService` 集成测试重新恢复通过。
