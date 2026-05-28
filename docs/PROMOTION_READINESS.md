# LarkSync 推广就绪检查清单

更新时间：2026-05-28

本文用于公开 Beta / 软启动前的执行检查。更详细的推广计划保存在本地规格目录 `docs/local_specs/`，该目录不提交到 Git。

## 1. 当前状态

- 当前开发版本：`v0.7.22-dev.1`
- 最近稳定版：`v0.7.21`
- 推荐试用模式：`download_only`
- 推荐首批用户：飞书重度用户、Obsidian/VS Code 用户、NAS 用户、OpenClaw / AI Agent 用户

## 2. Release 检查

- [ ] GitHub Release Latest 指向最新稳定版。
- [ ] Windows 安装包可下载。
- [ ] macOS Intel DMG 可下载。
- [ ] macOS Apple Silicon DMG 可下载。
- [ ] 所有安装包都有 sha256 校验。
- [ ] Release Notes 包含升级重点、详细变更和已知边界。
- [ ] 从上一稳定版自动更新到当前稳定版可用。

## 3. 用户首次试用检查

- [ ] README 首屏能直接找到下载入口。
- [ ] README 首屏能直接找到快速开始。
- [ ] OAuth 配置指南覆盖 App ID、App Secret、Redirect URI、权限 scopes。
- [ ] 安全与隐私说明覆盖 token 存储和日志脱敏。
- [ ] 反馈指南给出明确模板。
- [ ] 已知限制前置说明。
- [ ] 首次试用推荐 `download_only`。

## 4. 用户级安装验收

- [ ] Windows 10 安装、启动、退出。
- [ ] Windows 11 安装、启动、退出。
- [ ] macOS Intel 安装、启动、退出。
- [ ] macOS Apple Silicon 安装、启动、退出。
- [ ] 托盘菜单可打开管理面板。
- [ ] 新装环境可完成 OAuth。
- [ ] 新建 `download_only` 任务可完成首次同步。
- [ ] 日志中心能查看最近一次同步结果。

## 5. 同步链路验收

- [ ] 小型飞书目录下行同步。
- [ ] 包含图片的 Docx 转 Markdown。
- [ ] 本地 mtime 与云端修改时间接近。
- [ ] 双向 Markdown 修改可回写云端。
- [ ] 断网重连后可恢复。
- [ ] 两端同时修改时进入冲突处理。
- [ ] 删除策略 `off` / `safe` / `strict` 行为符合预期。
- [ ] 100MB+ 普通文件同步路径验证。

## 6. 推广素材检查

- [ ] 授权流程截图或 GIF。
- [ ] 创建任务截图或 GIF。
- [ ] 日志中心截图。
- [ ] 一篇中文推广文章草稿。
- [ ] OpenClaw / AI Agent 场景教程。
- [ ] 常见问题 FAQ。

## 7. 暂不扩大推广的阻塞项

以下任一项未闭环，不建议扩大推广：

- Latest Release 与 README 版本不一致。
- 安装包缺失或 sha256 缺失。
- OAuth 首次配置说明不清。
- `download_only` 首次同步不稳定。
- 出现未解释的数据风险。
- 用户无法找到反馈入口。
