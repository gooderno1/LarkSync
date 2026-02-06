# OAuth 配置指南（飞书）

本指南用于帮助你在网页端完成飞书 OAuth 配置，所有说明以飞书官方文档为准。

## 1. 先决条件
- 你有飞书账号，且能进入飞书开放平台控制台（企业管理员或应用创建者权限）。
- 本项目已启动后端与前端服务。
- 本地允许写入 `data/config.json`（网页配置会写入该文件）。

## 2. 创建应用（官方流程）
### 2.1 创建“企业自建应用”
1) 进入飞书开放平台控制台。
2) 选择创建应用并选择“企业自建应用”。
3) 填写应用名称与描述并完成创建。

### 2.2 获取 App ID / App Secret
1) 打开应用详情页。
2) 在“应用凭证”页面复制 App ID 与 App Secret。

### 2.3 配置 OAuth 回调地址
1) 打开“安全设置 / OAuth 回调”。
2) 添加回调地址（必须与 LarkSync 设置中填写的地址完全一致）：
   - 开发环境：`http://localhost:8000/auth/callback`
   - 生产环境：`http://localhost:8080/api/auth/callback`
3) 保存设置。

> 说明：回调地址填写在飞书控制台；LarkSync 设置页只需要填写同样的 Redirect URI。

### 2.4 配置权限 Scopes（在飞书控制台配置）
1) 打开“权限管理”。
2) 添加需要的权限（建议遵循最小权限原则）。
3) 如平台需要审核，等待审核通过后再授权。

**常用最小权限建议：**
- `drive:drive`
- `docs:doc`
- `drive:drive.metadata:readonly`
- `contact:contact.base:readonly`

> 注意：权限必须在飞书控制台配置，LarkSync 设置页不要求手动填写 scopes。

## 3. LarkSync 设置页填写
打开 LarkSync 的“设置”页面，只需填写以下字段：
- App ID
- App Secret
- Redirect URI

> 授权地址与 Token 地址均为可选项，通常可留空，系统会使用默认值。

## 4. 保存与验证
1) 在设置页点击“保存配置”。
2) 点击“连接飞书”完成授权。
3) 如失败，请逐项排查：
   - 回调地址是否与控制台完全一致（含协议与端口）。
   - App ID / App Secret 是否正确。
   - 控制台中是否已添加所需权限并通过审核。

### 常见报错：Access denied / 缺少权限
若出现“获取根目录失败: Access denied”或提示缺少权限（如 `drive:drive`、`drive:drive.metadata:readonly`），请确认：
1) 飞书控制台“权限管理”中已添加上述权限，且是**用户身份权限**。
2) 保存权限配置后，必须**重新授权**（退出登录后再次点击“连接飞书”）。

## 5. 官方文档入口
飞书官方文档为动态页面，请以最新说明为准：
- 飞书开放平台首页：`https://open.feishu.cn/document/home/index`
- OAuth2 授权码与 Token 文档
- OAuth 回调地址配置
- 权限管理（Scopes）

## 6. 安全提示
- App Secret 为敏感信息，保存后会写入本地 `data/config.json`，请勿提交到公开仓库。
- 若不希望落盘，可改用环境变量并清空配置文件中的 Secret。

本指南将随飞书官方文档更新而同步维护。
