# LarkSync v0.7.0

- 发布日期：2026-05-11
- 变更区间：v0.6.20 -> v0.7.0

## 本次更新明细

### 升级重点
- `v0.6.21-dev.1`：前端新增 `eventFilters` 纯函数模块，统一维护事件筛选项和后端 `statuses` 查询参数映射。

### 详细变更

#### v0.6.21-dev.1
- 前端新增 `eventFilters` 纯函数模块，统一维护事件筛选项和后端 `statuses` 查询参数映射。
- 日志中心事件 Tab 新增 `上传 / 下载 / 删除` 动作级筛选；删除筛选覆盖 `deleted / delete_pending / delete_failed`，可单独查看删除成功、待删除和删除失败相关事件。
- 前端引入 Vitest 并补充事件筛选规则单元测试，锁定上传、下载、删除和既有聚合筛选的状态映射。

## 安装包校验

| asset | sha256 |
| --- | --- |
| LarkSync-Setup-v0.7.0.exe | `d14cc4c10d8f90b4f2dfbb137536b775fe6482a2f81a929169b33c7985fb0496` |
