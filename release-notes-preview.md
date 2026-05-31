# LarkSync v0.7.24

- 发布日期：2026-05-31
- 变更区间：v0.7.23 -> v0.7.24

## 本次更新明细

### 升级重点
- `v0.7.24-dev.2`：复核线上失败日志与异常 Markdown 样例后确认，这次 `软件设计说明书-V1.4-插图规划说明.md` 的直接触发点是透明容器块 payload 使用了空 `text.elements`，飞书 `docx/v1/.../children` 会返回 `1770001 invalid param`；同时全量替换链路在创建失败后没有回滚已插入的顶层块，会把同一份正文不断追加到云端文档里，形成“越失败越膨胀”的坏状态。
- `v0.7.24-dev.1`：`apps/tray/autostart.py` 的 Windows Startup 快捷方式路径已从单段反斜杠字符串改为逐级目录拼接，避免在非 Windows 主机上模拟 `sys.platform == "win32"` 时把 `Microsoft\Windows\...` 当成一个普通目录名。

### 详细变更

#### v0.7.24-dev.2
- 复核线上失败日志与异常 Markdown 样例后确认，这次 `软件设计说明书-V1.4-插图规划说明.md` 的直接触发点是透明容器块 payload 使用了空 `text.elements`，飞书 `docx/v1/.../children` 会返回 `1770001 invalid param`；同时全量替换链路在创建失败后没有回滚已插入的顶层块，会把同一份正文不断追加到云端文档里，形成“越失败越膨胀”的坏状态。
- `DocxContentWriteService` 现改为先执行“最小尾部旧块腾位”，再根据腾位后的真实根块子节点数决定是否压缩一级块，避免在已经腾出空间后仍提前把 convert 结果包成透明容器。
- 透明容器块现改为写入合法零宽字符段落，而不是空 `text.elements`，与飞书 Docx 创建子块参数约束保持一致。
- `create_from_convert()` 现会在 `_create_children_recursive()` 过程中检测失败标记，并基于创建前的根块子节点数回滚本轮刚插入的顶层块，避免下一次同步面对已被部分污染的云端正文。
- `apps/backend/tests/test_docx_content_write_service.py` 已补齐三条独立回归：透明容器 payload 合法化、删尾腾位后不再误包裹一级块、创建失败后的顶层回滚；仓库版本同步提升到 `v0.7.24-dev.2` / `0.7.24-dev.2`，README 与 CHANGELOG 已补齐本轮问题说明。
- 现场任务 `算云项目更新` 已于 2026-05-31 21:14 左右完成一次手动重跑，状态为 `success`，原 `创建块失败` 不再出现；但目标文档当前被后端判定为“云端已更新，阻止本地覆盖”的冲突，需要在带本修复的后续构建中继续执行“使用本地”或其他冲突处理动作，才能把修好的 Markdown 正式回写云端。

#### v0.7.24-dev.1
- `apps/tray/autostart.py` 的 Windows Startup 快捷方式路径已从单段反斜杠字符串改为逐级目录拼接，避免在非 Windows 主机上模拟 `sys.platform == "win32"` 时把 `Microsoft\Windows\...` 当成一个普通目录名。
- 本次修复不改变真实 Windows 上自启动 `.lnk` 的目标、参数或工作目录，只消除了单元测试与跨平台 CI 环境中的路径语义漂移。
- 仓库版本已切入下一开发版：根包、后端、前端、前端 lockfile、README、CHANGELOG 与本开发日志统一提升到 `v0.7.24-dev.1` / `0.7.24-dev.1`，最新稳定版继续保留为 `v0.7.23`。
