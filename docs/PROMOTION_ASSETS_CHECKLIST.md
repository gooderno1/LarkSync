# 推广素材清单

更新时间：2026-05-28

本文用于准备公开 Beta 推广所需截图、GIF 和短视频素材。素材完成后可放入 `assets/promotion/`，并在 README、推广文章或 Release Notes 中引用。

## 1. 必备截图

- [ ] GitHub Release 下载入口。
- [ ] LarkSync 托盘图标与菜单。
- [ ] 首次 OAuth 配置页。
- [ ] 飞书 OAuth 授权成功后的连接状态。
- [ ] 新建同步任务向导。
- [ ] `download_only` 任务卡片。
- [ ] 首次同步成功后的日志中心。
- [ ] 冲突管理页面。
- [ ] 设置页中的自动更新面板。

## 2. 必备 GIF / 短视频

- [ ] 安装包下载与启动。
- [ ] OAuth 配置与连接飞书。
- [ ] 创建 `download_only` 任务并完成首次同步。
- [ ] 打开本地同步目录，查看生成的 Markdown 和图片资源。
- [ ] 日志中心定位一次同步运行。

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

- [ ] 桌面分辨率统一。
- [ ] 浏览器缩放为 100%。
- [ ] 页面语言与推广文案一致。
- [ ] 无敏感 token 和真实业务数据。
- [ ] 图片宽度适合 GitHub README 展示。
- [ ] GIF 文件大小可接受。
