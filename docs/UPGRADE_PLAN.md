# LarkSync 版本升级计划

> 创建日期：2026-02-07 | 最后更新：2026-02-07

## 版本线路图

```
v0.3.x  UI/UX 优化（已完成）
  │
  ▼
v0.4.x  桌面托盘化 ← 当前里程碑
  │
  ▼
v0.5.x  打包与安装包
  │
  ▼
v1.0.0  正式发布
```

---

## v0.3.x — UI/UX 优化（已完成 ✅）

| 版本 | 日期 | 内容 | 状态 |
|------|------|------|------|
| v0.3.0-dev.1 | 2026-02-07 | 前端架构拆分 + TanStack Query + Toast/确认弹窗 + 分步向导 | ✅ |
| v0.3.0-dev.2 | 2026-02-07 | Header 精简 + 明亮模式修复 + 同步策略卡片化 + Redirect URI 自动生成 | ✅ |
| v0.3.0-dev.3 | 2026-02-07 | 双 Header 修复 + 弹窗去模糊 + OAuth 教程页 | ✅ |
| v0.3.0-dev.4 | 2026-02-07 | ThemeToggle 组件化 + 非仪表盘页面 Header 移除 | ✅ |
| v0.3.0-dev.5 | 2026-02-07 | cloud_folder_name 字段 + /sync/logs/file API + 系统日志标签 | ✅ |
| v0.3.0-dev.6 | 2026-02-07 | 日志中心页码分页 + Pagination 组件 + 飞书频率限制智能重试 | ✅ |

---

## v0.4.x — 桌面托盘化（进行中 🔧）

> 设计文档：[`docs/design/v0.4.0-desktop-tray-design.md`](design/v0.4.0-desktop-tray-design.md)

### v0.4.0-dev.1 — FastAPI 静态文件服务 + 构建脚本 ✅
- [x] `main.py` 增加静态文件服务（检测 dist/ 目录，挂载 + SPA fallback）
- [x] `scripts/build.py` 构建脚本（调用 npm build + 验证 dist/）
- [x] 前端 `api.ts` 基址改为 `VITE_API_BASE` 环境变量配置
- [x] 验证：单独运行 `uvicorn` 可访问完整应用
- [x] 托盘应用核心：`apps/tray/` 目录结构 + tray_app + backend_manager + config
- [x] 一键启动器：LarkSync.pyw / .command / .bat
- [x] 状态轮询 + 图标动态变色（5 秒轮询 /tray/status）
- [x] 后端新增 `GET /tray/status` 聚合状态接口
- [x] 系统通知：notifier.py（plyer + 60 秒去重 + PowerShell fallback）
- [x] 开机自启动：autostart.py（Windows Startup / macOS LaunchAgent）
- [x] PyInstaller 打包配置：build_installer.py + spec 自动生成

### v0.4.0-dev.2 — 修复 + 品牌集成 ✅
- [x] 端口冲突修复：智能检测已有后端并复用
- [x] 单实例锁：防止多次启动（端口锁 48901）
- [x] BAT 启动器清理旧进程
- [x] SPA fallback 修复：dist 根目录静态文件正确服务
- [x] 品牌 Logo 集成：托盘 4 状态变体 + favicon + 侧边栏横版 Logo
- [x] 开发/生产 URL 自动检测（有 dist → 8000，无 dist → 3666）

---

## v0.5.x — 打包与安装包（计划中 📋）

### v0.5.0-dev.1 — PyInstaller 打包配置
- [ ] `larksync.spec`：PyInstaller 配置文件
- [ ] `scripts/build_installer.py`：统一构建脚本
- [ ] 解决 PyInstaller 打包 FastAPI/uvicorn 的依赖问题
- [ ] 数据目录迁移到用户目录（%APPDATA% / ~/Library/Application Support/）
- [ ] 验证：`pyinstaller larksync.spec` 生成可运行的独立目录

### v0.5.0-dev.2 — Windows 安装包
- [ ] NSIS 安装脚本（`scripts/installer/nsis/larksync.nsi`）
- [ ] 安装向导（选择路径、桌面快捷方式、开始菜单）
- [ ] 注册卸载程序
- [ ] 验证：生成 `LarkSync-Setup-vX.Y.Z.exe` 可安装/卸载

### v0.5.0-dev.3 — macOS 打包
- [ ] `.app` bundle 生成
- [ ] DMG 打包脚本
- [ ] 验证：生成 `LarkSync-vX.Y.Z.dmg` 可拖拽安装

### v0.5.0-dev.4 — CI/CD 自动构建（可选）
- [ ] GitHub Actions workflow
- [ ] 自动构建 Windows + macOS 安装包
- [ ] Release 自动上传产物

---

## v1.0.0 — 正式发布（规划中 📋）

- [ ] 所有 P0/P1 功能完成
- [ ] 跨平台测试（Windows 10/11、macOS M1/M2）
- [ ] 性能优化（大文件夹同步、日志文件流式读取）
- [ ] 安全审计（Token 加密存储验证）
- [ ] 用户文档完善
- [ ] 版本号去掉 `-dev` 后缀

---

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-02-08 | v0.4.0-dev.2 完成：修复 + 品牌集成 |
| 2026-02-07 | 初始创建，v0.3.x 已完成，v0.4.0-dev.1 完成 |
