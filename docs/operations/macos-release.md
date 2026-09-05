# macOS 发布与验收

## 支持范围

- 架构：`arm64`、`x86_64`。
- 最低系统：macOS 12.0。
- 安装包：默认可发布 ad-hoc 签名 DMG；配置 Apple 凭据后自动升级为 Developer ID 签名并完成 notarization/stapling 的 DMG。

## GitHub Secrets

以下六项为可选增强配置。全部不配置时，正式 tag 仍发布 ad-hoc 签名 DMG；六项全部配置时启用 Developer ID 签名与 Apple 公证；只配置部分字段会阻止 macOS job，避免产生签名状态不明确的产物：

- `MACOS_CERTIFICATE_P12_BASE64`：Developer ID Application 证书 P12 的 Base64。
- `MACOS_CERTIFICATE_PASSWORD`：P12 密码。
- `MACOS_CODESIGN_IDENTITY`：完整签名身份，例如`Developer ID Application: Example (TEAMID)`。
- `APPLE_ID`：提交 notarization 的 Apple ID。
- `APPLE_TEAM_ID`：Apple Developer Team ID。
- `APPLE_APP_SPECIFIC_PASSWORD`：Apple ID 应用专用密码。

Secrets 只注入临时 runner。构建结束后删除临时 P12 和签名 keychain。

## 可选增强：从 Apple 证书到 GitHub Secrets

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

该预检通过后，正式 Tag 会自动生成 Developer ID 签名公证版本。未配置凭据也允许创建正式 Tag，发布脚本和 CI 会明确记录使用 ad-hoc 签名。

## 无 Apple 凭据的安装方式

ad-hoc 签名版本仍会经过双架构构建、Bundle 校验、DMG 挂载、安装复制、Keychain、后端健康检查、原生账号连接首屏和两次扫码 WebKit smoke，但没有 Apple Developer 身份和公证票据。用户首次打开时：

1. 从本项目官方 GitHub Release 下载与机器架构匹配的 DMG，并核对 SHA256。
2. 打开 DMG，将`LarkSync.app`拖入`Applications`，然后尝试打开一次。
3. 如出现“无法验证开发者”或“Apple 无法检查是否包含恶意软件”，进入「系统设置 → 隐私与安全性」。
4. 在安全区域点击「仍要打开」，再次确认；系统会将该应用保存为例外，后续可正常双击启动。

Apple 官方说明：[安全打开 Mac App](https://support.apple.com/102445)。只应对来源和 SHA256 均已确认的安装包手动放行。

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

PR/main 的 macOS 构建使用 ad-hoc 签名，用于尽早检查 Bundle 结构和运行时。正式 tag 构建先检测六项 Apple 凭据：全部缺失时继续使用 ad-hoc 签名；全部存在时设置`LARKSYNC_REQUIRE_MACOS_NOTARIZATION=1`；部分存在时立即失败并提示补齐或清空。

所有 macOS 构建均执行步骤 1-5；仅 Developer ID 模式继续执行步骤 6-8：

1. 生成稳定版、带橙色 `DEV` 徽标的预发布版 `.icns` 与菜单栏 Template 图标；语义版本包含预发布后缀时自动选择 `LarkSync-Dev.icns`，稳定版选择 `LarkSync.icns`。
2. PyInstaller 构建 App Bundle。
3. 使用 Developer ID 和 Hardened Runtime 签名。
4. `codesign --verify --deep --strict`。
5. 创建 DMG。
6. `notarytool submit --wait`。
7. `stapler staple`与`stapler validate`。
8. Gatekeeper assessment。

DMG 默认由 `create-dmg` 生成带图标布局的镜像；构建机未安装该命令时自动使用 macOS 自带的 `hdiutil`，并保留 `LarkSync.app` 与指向 `/Applications` 的投放入口。可用 `LARKSYNC_DMG_TOOL=auto|create-dmg|hdiutil` 固定构建工具。

## 安装 smoke

`python scripts/macos_installer_smoke.py --arch-suffix arm64`会：

- 挂载 DMG，并验证`Applications`投放入口。
- 复制 App 到隔离的临时安装目录。
- 校验 Bundle ID、版本、Release Channel 对应的 `.icns`、HiDPI 元数据、`LSUIElement=true` 后台托盘身份和代码签名。
- 使用随机临时账户完成 Keychain 写入、读取和删除。
- 启动安装版后端并检查`127.0.0.1:18765/health`。
- 写入隔离 OAuth 测试配置。
- 通过 LaunchServices 启动真实 App，并确认打包入口、Cocoa 窗口创建和`webview_starting`阶段均已到达。
- 交互式 Mac 直接在原生 WKWebView 断言当前 Device Flow 账号连接首屏、`choose_method` 阶段、“开始第 1 次扫码”操作可见且可用，并要求 LarkSync Logo 已成功解码而不是收到 SPA HTML。
- GitHub 托管 Mac runner 无交互式 WindowServer 时，要求 App 自身写入`webview_starting`且对应原生 PID 在 WebKit 回退前仍存活；macOS 双架构任务显式依赖独立 Linux headless Playwright WebKit 任务，后者断言 1080×720 第 1 次扫码完成检查点、第 2 次扫码二维码状态为`ready`、图片可见且来源是 PNG data URL。托管 runner 不宣称验证原生窗口像素。

任何步骤失败都会阻止发布。
