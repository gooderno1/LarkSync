# macOS 发布与验收

## 支持范围

- 架构：`arm64`、`x86_64`。
- 最低系统：macOS 12.0。
- 安装包：Developer ID 签名并完成 Apple notarization/stapling 的 DMG。

## GitHub Secrets

正式 tag 构建必须配置：

- `MACOS_CERTIFICATE_P12_BASE64`：Developer ID Application 证书 P12 的 Base64。
- `MACOS_CERTIFICATE_PASSWORD`：P12 密码。
- `MACOS_CODESIGN_IDENTITY`：完整签名身份，例如`Developer ID Application: Example (TEAMID)`。
- `APPLE_ID`：提交 notarization 的 Apple ID。
- `APPLE_TEAM_ID`：Apple Developer Team ID。
- `APPLE_APP_SPECIFIC_PASSWORD`：Apple ID 应用专用密码。

Secrets 只注入临时 runner。构建结束后删除临时 P12 和签名 keychain。

## 构建门禁

PR/main 的 macOS 构建允许 ad-hoc 签名，用于尽早检查 Bundle 结构和运行时；正式 tag 构建设置`LARKSYNC_REQUIRE_MACOS_NOTARIZATION=1`，缺少任一公证凭证立即失败。

正式链路依次执行：

1. 生成 `.icns` 与菜单栏 Template 图标。
2. PyInstaller 构建 App Bundle。
3. 使用 Developer ID 和 Hardened Runtime 签名。
4. `codesign --verify --deep --strict`。
5. 创建 DMG。
6. `notarytool submit --wait`。
7. `stapler staple`与`stapler validate`。
8. Gatekeeper assessment。

## 安装 smoke

`python scripts/macos_installer_smoke.py --arch-suffix arm64`会：

- 挂载 DMG，并验证`Applications`投放入口。
- 复制 App 到隔离的临时安装目录。
- 校验 Bundle ID、版本、`.icns`、HiDPI 元数据和代码签名。
- 使用随机临时账户完成 Keychain 写入、读取和删除。
- 启动安装版后端并检查`127.0.0.1:18765/health`。
- 写入隔离 OAuth 测试配置。
- 通过 LaunchServices 启动真实 App，并确认打包入口、Cocoa 窗口创建和`webview_starting`阶段均已到达。
- 交互式 Mac 直接在原生 WKWebView 断言授权首屏和二维码。
- GitHub 托管 Mac runner 无交互式 WindowServer 时，仅要求 App 自身写入`webview_starting`；macOS 双架构任务显式依赖独立 Linux headless Playwright WebKit 任务，后者断言 1080×720 授权首屏存在、二维码状态为`ready`、图片可见且来源是 PNG data URL。托管 runner 不宣称验证原生窗口持续存活。

任何步骤失败都会阻止发布。
