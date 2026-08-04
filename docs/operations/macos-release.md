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

## 首次配置：从 Apple 证书到 GitHub Secrets

以下步骤必须在受信任的 Mac 上执行。签发 Developer ID Application 证书需要有效的 Apple Developer Program 团队及相应账户权限；不要把 P12、P12 密码或 Apple 应用专用密码发送到聊天、Issue、PR 或仓库文件。

1. 在 macOS「钥匙串访问」中选择「证书助理 → 从证书颁发机构请求证书」，生成并保存`.certSigningRequest`。
2. 打开 Apple Developer 的 Certificates 页面，新增`Developer ID`，类型选择`Developer ID Application`，上传 CSR 并下载`.cer`。
3. 双击`.cer`安装到创建 CSR 的同一登录钥匙串。在「我的证书」中确认该证书下方可展开私钥。
4. 选中证书和私钥，导出为带强密码的`.p12`；P12 只用于注入 GitHub，不得提交到仓库。
5. 查询完整签名身份：

   ```bash
   security find-identity -v -p codesigning | grep "Developer ID Application"
   ```

6. 从 Apple Developer Account 的 Membership details 获取 Team ID。
7. 确认 Apple Account 已启用双重认证；在`account.apple.com → 登录与安全 → App-Specific Passwords`生成一个仅供 LarkSync notarization 使用的应用专用密码。
8. 在本仓库根目录运行安全注入工具。P12 密码和应用专用密码会无回显读取；工具通过 stdin 调用 GitHub CLI，不把密码放入命令参数：

   ```bash
   python scripts/configure_macos_release_secrets.py \
     --repo gooderno1/LarkSync \
     --p12 "/absolute/path/Developer ID Application.p12" \
     --identity "Developer ID Application: Your Name (TEAMID)" \
     --apple-id "your-apple-id@example.com" \
     --team-id "TEAMID"
   ```

9. 只读检查六个 Secret 名称是否齐全：

   ```bash
   python scripts/configure_macos_release_secrets.py --check --repo gooderno1/LarkSync
   ```

10. 在 GitHub Actions 手动运行`Release Build`，将`validate_macos_credentials`设为`true`。该模式只运行凭据预检，不执行常规质量门或安装包构建；也可在当前发布分支直接使用：

    ```bash
    gh workflow run release-build.yml \
      --repo gooderno1/LarkSync \
      --ref codex/desktop-app-refactor-v0.8 \
      -f validate_macos_credentials=true
    gh run list --workflow release-build.yml --limit 1 --repo gooderno1/LarkSync
    ```

只有该工作流同时通过测试二进制签名和`notarytool history`认证，才允许创建正式 Tag。`python scripts/release.py --publish`也会在任何版本文件变更前检查六项 Secret 名称。

### 凭据轮换

- Developer ID 私钥疑似泄露：立即在 Apple Developer 撤销证书，重新签发并替换前三项证书 Secret。
- Apple Account 主密码被修改或重置：Apple 会撤销现有应用专用密码；重新生成并替换`APPLE_APP_SPECIFIC_PASSWORD`。
- 团队或发布账户变化：同步替换`APPLE_ID`、`APPLE_TEAM_ID`和签名身份，并重新运行凭据验证工作流。

### 官方参考

- [Apple：创建 Developer ID 证书](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/)
- [Apple：创建证书签名请求 CSR](https://developer.apple.com/help/account/certificates/create-a-certificate-signing-request)
- [Apple：使用 notarytool 与应用专用密码](https://developer.apple.com/documentation/technotes/tn3147-migrating-to-the-latest-notarization-tool)
- [Apple：生成应用专用密码](https://support.apple.com/102654)
- [GitHub：在 Actions 中使用 Secrets](https://docs.github.com/actions/security-guides/using-secrets-in-github-actions)

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
