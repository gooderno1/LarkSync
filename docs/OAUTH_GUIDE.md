# OAuth 配置指南（飞书）

本指南用于帮助你在网页端配置飞书 OAuth 参数，并解释每个字段的来源与用途。

## 1. 先决条件
- 已拥有飞书账号并可进入飞书开放平台控制台。
- 本项目已启动后端与前端服务。
- 你能在本地保存配置文件（默认写入 `data/config.json`）。

## 2. 创建与配置应用（官方流程）
### 2.1 创建“企业自建应用”
1) 进入飞书开放平台控制台，选择创建应用。
2) 选择“企业自建应用”，填写应用名称与描述，完成创建。

### 2.2 获取 App ID 与 App Secret
1) 进入应用详情页。
2) 打开“应用凭证”页面，复制 App ID 与 App Secret。

### 2.3 配置 OAuth 回调地址
1) 打开“安全设置 / OAuth 回调”。
2) 添加回调地址（必须与网页配置向导中的回调地址完全一致）：
   - 开发环境：`http://localhost:8000/auth/callback`
   - 生产环境：`http://localhost:8080/api/auth/callback`

### 2.4 配置权限 scopes
1) 打开“权限管理”。
2) 按需添加权限，建议遵循最小权限原则。
3) 保存并等待权限审核（如平台要求）。

> 如果应用未发布或未对测试用户开放，授权可能失败；请完成应用可用性设置。

## 3. 网页配置向导字段对照
| 配置项 | 说明 | 填写来源 |
| --- | --- | --- |
| 授权地址（Authorize URL） | 用户登录授权入口 | OAuth2 授权码文档（获取授权码） |
| Token 地址（Access Token URL） | 授权码换取 user_access_token | OAuth2 Token 文档（获取用户 Access Token） |
| App ID | 应用唯一标识 | 应用凭证页面 |
| App Secret | 应用密钥（敏感信息） | 应用凭证页面 |
| 回调地址（Redirect URI） | 授权完成后的回跳地址 | OAuth 回调配置页面 |
| Scopes | 申请的权限范围（逗号分隔） | 权限管理页面 |

### 常用地址示例（以官方文档为准）
- 授权地址：`https://open.feishu.cn/open-apis/authen/v1/index`
- Token 地址：`https://open.feishu.cn/open-apis/authen/v1/access_token`

### 建议 scopes（按需取用）
以下为本项目常见的最小权限组合，请以你实际业务和官方权限说明为准：
- `drive:drive`
- `docs:doc`
- `drive:meta`
- `contact:contact.base:readonly`

## 4. 保存与验证
1) 在网页端填写配置并点击“保存配置”。
2) 点击“登录飞书”，完成授权。
3) 如失败，请检查：
   - 回调地址是否与控制台完全一致（含协议与端口）。
   - App ID / App Secret 是否正确。
   - 权限 scopes 是否已添加并通过审核（如需要）。
   - 授权地址与 Token 地址是否与官方文档一致。

## 5. 安全提示
- App Secret 为敏感信息，保存后会写入本地 `data/config.json`，请避免提交到公开仓库。
- 如果不希望落盘，可改用环境变量配置并移除文件中的 secret。

本指南将随飞书官方文档更新而同步维护。
