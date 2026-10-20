# CLI 调用参考

`CLI` 代表原生可执行程序，或 `python /absolute/path/to/skill/scripts/larksync_cli.py`。
全局参数放在子命令之前：`CLI --base-url http://localhost:18765 --account-id ID task-list`。
不传账号时，单账号自动选择，多账号返回 `ACCOUNT_REQUIRED`。CLI 不更改 UI 活动账号。

## 首次连接

```text
CLI capabilities
CLI check
CLI account-list
CLI app-list
CLI auth-start --register --brand feishu
CLI auth-poll --kind registration --session-id SESSION
CLI auth-start --app-profile-id APP
CLI auth-poll --kind device --session-id SESSION
CLI --account-id ACCOUNT auth-verify
CLI --account-id ACCOUNT drive-list --folder-token https://example.feishu.cn/drive/folder/TOKEN --page-size 100
CLI --account-id ACCOUNT drive-list --folder-token TOKEN --page-token NEXT
```

注册、授权均由用户在返回的官方链接扫码完成。会话状态为 pending / slow_down 时遵循 interval 或 retry_after；
registered 后取 `session.app_profile.id` 开始授权；authorized 后取 `session.account.id` 绑定后续调用。
denied / expired / failed 时报告原因，需要时重新开始；不要循环重试已终止的会话。
取消：`auth-cancel --kind device|registration --session-id SESSION`。
重新授权：`CLI --account-id ACCOUNT auth-reauthorize`，随后用 device 类型轮询。

## 任务 JSON

新建示例；Windows 路径在 JSON 中转义反斜杠，也可使用 `/`：

```json
{
  "name": "团队知识库",
  "local_path": "D:/Knowledge/Feishu",
  "cloud_folder_token": "https://example.feishu.cn/drive/folder/TOKEN",
  "sync_mode": "download_only",
  "delete_policy": "off",
  "enabled": true,
  "ignored_subpaths": ["私人资料"],
  "path_sync_rules": [
    {"path": "参考资料", "kind": "folder", "sync_mode": "download_only"}
  ]
}
```

macOS 路径示例 `/Users/alice/Knowledge/Feishu`。请替换示例路径和 token。
`local_path` 与 `cloud_folder_token` 为新建必填项。支持 token 或 HTTPS 飞书/Lark 文件夹链接；文档、Wiki 链接不支持作为同步根目录。

| 字段 | 允许值 / 说明 |
| --- | --- |
| name / cloud_folder_name | 显示名称 |
| base_path | Markdown 资源路径基准，绝对路径 |
| sync_mode | download_only / upload_only / bidirectional |
| update_mode | auto / partial / full |
| md_sync_mode | download_only / enhanced / doc_only；新建时按方向默认选择 |
| delete_policy | off / safe / strict；新建默认 off |
| delete_grace_minutes | 非负整数 |
| enabled / is_test | JSON true / false |
| ignored_subpaths | 相对路径数组，[] 清空；不是通配符 |
| path_sync_rules | 最多 500 条；path、kind（file / folder）、sync_mode；[] 清空 |

```text
CLI task-plan --spec-file task.json
CLI --account-id ACCOUNT task-create --spec-file task.json
CLI --account-id ACCOUNT task-get --task-id TASK
CLI --account-id ACCOUNT task-update --task-id TASK --spec-file patch.json --dry-run
CLI --account-id ACCOUNT task-update --task-id TASK --spec-file patch.json
CLI --account-id ACCOUNT task-wait --task-id TASK --timeout 60
CLI --account-id ACCOUNT task-run --task-id TASK --wait --timeout 60
CLI --account-id ACCOUNT task-pause --task-id TASK
CLI --account-id ACCOUNT task-resume --task-id TASK
CLI --account-id ACCOUNT task-diagnostics --task-id TASK --run-id RUN
CLI --account-id ACCOUNT task-entries --task-id TASK --path docs --offset 0 --limit 100
CLI --account-id ACCOUNT task-delete --task-id TASK
```

修改 JSON 仅含要改字段，例如 `{"name":"新名称","ignored_subpaths":[]}`。
`--spec-file -` 从 stdin 读 JSON；不要与字段 flags 混用。
预览中的 `may_start_sync` 是可能性；修改省略的方向、删除策略保持现状。服务器仍负责路径冲突、运行模式、规则与账号权限校验。

## 返回和边界

- `ok: false`：看 error_code / next_step。exit 1 为环境/API错误，exit 2 为输入错误。
- `ok: true`：请求成功。同步是否完成必须检查 `sync_complete`；授权是否完成检查 `session.status`。
- `task-wait` 默认等 60 秒，最长 3600 秒；超时返回 `timed_out: true`，不会取消任务。用 `--run-id` 绑定特定运行；被新运行替换会报 RUN_REPLACED。
- `schema` 返回当前服务 OpenAPI，包含任务模型和所有接口字段。`capabilities` 离线可用。
- `auth-verify` 仅验证 Drive 读取；它不创建文档来探测写权限。
- `config-set --download-value 1 --download-unit days --download-time 01:00` 是全局频率修改；全部任务受影响。
- 旧 `bootstrap-*` / `workflow-*` 兼容保留。bootstrap 会修改全局频率；`completed` 只指配置/编排完成，不能用来判断文件已同步。新任务优先采用上述任务 API。
- 旧 workflow 运行记录存放在 `LARKSYNC_CLI_DATA_DIR`，默认用户数据目录 `LarkSync/cli`，不写技能安装目录。
