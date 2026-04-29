# LarkSync v0.6.2

- 变更区间：项目起始版本 -> 当前版本

## 本次更新明细

### 升级重点
- `v0.6.2-dev.5`：新增 `ConflictResolutionService`，冲突解决从“仅写 resolved 标记”升级为“先定位关联任务，再调用同步执行器执行定向上传/下载，成功后才标记冲突已解决”。
- `v0.6.2-dev.4`：`/system/update/install` 默认会把 `silent=true`、`restart_path=<当前 LarkSync.exe>` 写入安装请求；前端安装入口改为“静默安装已下载更新”。
- `v0.6.2-dev.3`：自动更新的安装包、`status.json`、`install-request.json`、`update.log` / `update-install.log` 在冻结打包环境下改为写入用户数据目录，不再落在安装目录 `_internal\\data` 下，降低自更新时与安装目录互相影响的风险。
- `v0.6.2-dev.2`：`ConflictService.add_conflict()` 新增未解决冲突查重；同一路径、同一 cloud token、同一版本差异重复检测时复用原记录，不再重复写库。
- `v0.6.2-dev.1`：`source=local` 删除墓碑执行云端删除前，会检查同一任务内是否仍有其他存在且未被忽略的本地路径绑定同一个 cloud token。

### 详细变更

#### v0.6.2-dev.5
- 新增 `ConflictResolutionService`，冲突解决从“仅写 resolved 标记”升级为“先定位关联任务，再调用同步执行器执行定向上传/下载，成功后才标记冲突已解决”。
- `SyncTaskRunner` 新增冲突定向处理入口：`run_conflict_upload()` 会按本地优先强制绕过云端修改时间阻断，直接上传当前本地版本；`run_conflict_download()` 会按云端优先强制绕过“本地较新”跳过逻辑，下载指定云端文件覆盖本地。
- 解决失败时冲突保持未解决状态，不再出现“页面显示已处理，但文件其实没变化”的假成功。

#### v0.6.2-dev.4
- `/system/update/install` 默认会把 `silent=true`、`restart_path=<当前 LarkSync.exe>` 写入安装请求；前端安装入口改为“静默安装已下载更新”。
- 托盘在 Windows 上检测到静默安装请求后，不再直接 ShellExecute 安装包，而是启动 detached PowerShell helper，以 NSIS `/S` 静默参数运行安装器、等待安装器退出，并在退出码为 0 时自动重启新版本。
- `update-install.log` 新增静默安装阶段日志：安装器启动请求、PID、退出码、自动重启请求，便于定位“托盘已发起”和“安装器实际执行结果”之间的问题。
- 仍保留 UAC 风险提示：如果安装目录位于 `Program Files`，Windows 可能继续弹出系统权限确认，这不属于安装向导界面。

#### v0.6.2-dev.3
- 自动更新的安装包、`status.json`、`install-request.json`、`update.log` / `update-install.log` 在冻结打包环境下改为写入用户数据目录，不再落在安装目录 `_internal\\data` 下，降低自更新时与安装目录互相影响的风险。
- 更新状态读取会始终以当前运行版本覆盖缓存中的 `current_version`，并在最新版本不高于当前版本时自动清掉 `update_available`，避免安装完成后继续提示同一版本更新。
- 托盘日志文案从“使用 ShellExecute 启动安装包”改为“已请求 ShellExecute 启动安装包”，避免把系统已接收启动请求误记成安装器已经实际启动成功。

#### v0.6.2-dev.2
- `ConflictService.add_conflict()` 新增未解决冲突查重；同一路径、同一 cloud token、同一版本差异重复检测时复用原记录，不再重复写库。
- `ConflictService.list_conflicts()` 会折叠历史残留的重复未解决记录；即使旧库里已存在重复数据，冲突管理页面也只展示一条当前冲突。

#### v0.6.2-dev.1
- `source=local` 删除墓碑执行云端删除前，会检查同一任务内是否仍有其他存在且未被忽略的本地路径绑定同一个 cloud token。
- 若同一 cloud token 仍有有效本地路径，删除墓碑会取消执行并记录跳过事件，不再调用飞书删除接口。
- 本地安全删除移入 `.larksync_trash` 前，会静默源路径和回收目标路径的 watcher 事件，避免程序自身移动文件再次触发本地删除墓碑。
