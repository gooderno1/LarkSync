# 推广素材清单

更新时间：2026-05-28 14:28:02 +08:00

本文用于准备公开 Beta 推广所需截图、GIF 和短视频素材。素材完成后可放入 `assets/promotion/`，并在 README、推广文章或 Release Notes 中引用。

## 1. 必备截图

- [x] GitHub Release 下载入口：`assets/promotion/github-release-download.png`
- [x] LarkSync 托盘图标与菜单：`assets/promotion/tray-menu.png`（基于当前托盘菜单项生成的公开演示图）。
- [x] 首次 OAuth 配置页：`assets/promotion/quick-start-oauth.png`
- [x] 飞书 OAuth 授权成功后的连接状态：`assets/promotion/connect-feishu.png`、`assets/promotion/dashboard-connected.png`
- [x] 新建同步任务向导：`assets/promotion/create-download-task.png`
- [x] `download_only` 任务卡片：`assets/promotion/task-card-download-only.png`
- [x] 首次同步成功后的日志中心：`assets/promotion/log-center-success.png`
- [x] 冲突管理页面：`assets/promotion/conflict-management.png`
- [x] 设置页中的自动更新面板：`assets/promotion/settings-oauth-update.png`
- [x] 本地 Markdown 输出目录：`assets/promotion/local-markdown-output.png`

## 2. 必备 GIF / 短视频

- [x] 安装包下载与启动：`assets/promotion/github-release-download.png`、`assets/promotion/windows-download-startup.gif`；真实安装器交互录屏仍需单独确认后补充。
- [x] OAuth 配置与连接飞书：`assets/promotion/oauth-connect-flow.gif`
- [x] 创建 `download_only` 任务并完成首次同步：`assets/promotion/quick-start-flow.gif`
- [x] 打开本地同步目录，查看生成的 Markdown 和图片资源：`assets/promotion/local-markdown-output.png`
- [x] 日志中心定位一次同步运行：`assets/promotion/log-center-success.png`、`assets/promotion/quick-start-flow.gif`

## 3. 推荐录制脚本

### 3.1 首次试用脚本

1. 打开 GitHub Release 页面。
2. 下载并启动 LarkSync。
3. 打开设置页，填写 App ID / App Secret / Redirect URI。
4. 点击连接飞书。
5. 创建 `download_only` 任务。
6. 点击立即同步。
7. 打开本地目录展示 Markdown 文件。
8. 打开日志中心展示成功运行。

### 3.2 OpenClaw 本地缓存脚本

1. 展示飞书文档目录。
2. 展示 LarkSync `download_only` 任务。
3. 展示本地缓存目录。
4. 展示 OpenClaw / CLI 读取本地目录。
5. 强调“低频同步，高频本地读取”。

## 4. 脱敏要求

截图和视频中必须遮盖：

- App Secret。
- access token / refresh token。
- 飞书文件 token、文档 token、文件夹 token。
- 公司、客户、项目名。
- 不适合公开的本地路径。
- 私人头像、昵称、成员列表。

## 5. 命名建议

```text
assets/promotion/quick-start-oauth.png
assets/promotion/create-download-task.png
assets/promotion/log-center-success.png
assets/promotion/openclaw-local-cache.png
assets/promotion/quick-start-flow.gif
```

## 6. 发布前检查

- [x] 桌面分辨率统一：当前截图统一为约 1280 × 720。
- [x] 浏览器缩放为 100%。
- [x] 页面语言与推广文案一致。
- [x] 无敏感 token 和真实业务数据：截图使用临时 mock API 与演示任务。
- [x] 图片宽度适合 GitHub README 展示。
- [x] GIF 文件大小可接受：`quick-start-flow.gif` 约 590KB。
- [x] 补充 GIF 文件大小可接受：`oauth-connect-flow.gif` 约 211KB，`windows-download-startup.gif` 约 274KB。

## 7. 本轮素材说明

本轮素材使用本地临时 mock API 生成，示例任务、路径、账号均为公开演示数据：

- 账号：`Demo User`
- 设备：`Demo PC`
- 本地路径：`D:/LarkSyncTrial/FeishuMirror`
- 云端目录：`LarkSync测试专用`
- 同步模式：`download_only`
- 结果：`total=5`、`downloaded=5`、`failed=0`

补充素材：

- `tray-menu.png`：基于当前 `apps/tray/tray_app.py` 菜单项生成的公开演示图，避免截图暴露用户桌面和任务栏隐私。
- `conflict-management.png`：通过临时 mock API 构造 `产品周报.md` 的模拟冲突，token、路径和内容均为演示数据。
- `oauth-connect-flow.gif`：串联 OAuth 配置、连接飞书和已连接仪表盘。
- `windows-download-startup.gif`：串联 GitHub Release 下载入口、托盘菜单和管理面板启动状态。

后续可选补充：

- 真实 Windows 安装器交互录屏：需要明确授权实际运行安装包后再补充。
- 真实系统托盘菜单实机截图：需要确认不会暴露桌面、任务栏或个人环境信息。
