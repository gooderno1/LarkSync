# LarkSync 推广就绪检查清单

更新时间：2026-05-28

本文用于公开 Beta / 软启动前的执行检查。更详细的推广计划保存在本地规格目录 `docs/local_specs/`，该目录不提交到 Git。

## 1. 当前状态

- 当前开发版本：`v0.7.22-dev.1`
- 最近稳定版：`v0.7.21`
- 推荐试用模式：`download_only`
- 推荐首批用户：飞书重度用户、Obsidian/VS Code 用户、NAS 用户、OpenClaw / AI Agent 用户

## 2. Release 检查

- [x] GitHub Release Latest 指向最新稳定版。
- [x] Windows 安装包可下载。
- [x] macOS Intel DMG 可下载。
- [x] macOS Apple Silicon DMG 可下载。
- [x] 所有安装包都有 sha256 校验。
- [x] Release Notes 包含升级重点、详细变更和已知边界。
- [ ] 从上一稳定版自动更新到当前稳定版可用。

当前检查记录：

- 2026-05-28：`/releases/latest` 仍指向 `v0.7.20`，且 `v0.7.21` 存在 tag 但没有 GitHub Release。
- 2026-05-28：已手动触发 `v0.7.21` Release Build（workflow run: <https://github.com/gooderno1/LarkSync/actions/runs/26554939964>），等待生成 Windows/macOS 安装包与 sha256 后复核。
- 2026-05-28：`v0.7.21` Release Build 已全部通过；`/releases/latest` 现指向 `v0.7.21`，并已上传 Windows 安装包、macOS `arm64` / `x86_64` DMG 及对应 `.sha256`。

## 3. 用户首次试用检查

- [x] README 首屏能直接找到下载入口。
- [x] README 首屏能直接找到快速开始。
- [x] OAuth 配置指南覆盖 App ID、App Secret、Redirect URI、权限 scopes，并补充真实飞书控制台脱敏截图。
- [x] 安全与隐私说明覆盖 token 存储和日志脱敏。
- [x] 反馈指南给出明确模板。
- [x] 已知限制前置说明。
- [x] 首次试用推荐 `download_only`。

当前检查记录：

- 2026-05-28：README 首屏已按“定位、下载入口、快速开始、适合场景、安全边界”重排，长工程细节折叠展示。
- 2026-05-28：OAuth 指南已补齐创建企业自建应用、应用凭证、重定向 URL、权限管理四张真实脱敏截图。

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

- [x] 授权流程截图或 GIF。
- [x] 同步状态总览或最近运行结果截图。
- [x] 创建任务截图或 GIF。
- [x] 日志中心截图。
- [x] 飞书开放平台 OAuth 配置真实脱敏截图。
- [x] 一篇中文推广文章草稿。
- [x] OpenClaw / AI Agent 场景教程。
- [x] 常见问题 FAQ。
- [x] 推广素材清单。

说明：

- 托盘菜单与安装器交互截图不作为当前推广必需素材。后续如要单独宣传“安装体验”或“托盘常驻”，只使用真实截图 / 录屏，不再使用示意图。

## 7. 暂不扩大推广的阻塞项

以下任一项未闭环，不建议扩大推广：

- Latest Release 与 README 版本不一致。
- 安装包缺失或 sha256 缺失。
- OAuth 首次配置说明不清。
- `download_only` 首次同步不稳定。
- 出现未解释的数据风险。
- 用户无法找到反馈入口。
