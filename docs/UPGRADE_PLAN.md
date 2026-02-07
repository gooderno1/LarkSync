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

### v0.4.0-dev.1 — FastAPI 静态文件服务 + 构建脚本
- [ ] `main.py` 增加静态文件服务（检测 dist/ 目录，挂载 + SPA fallback）
- [ ] `scripts/build.py` 构建脚本（调用 npm build + 验证 dist/）
- [ ] 前端 `vite.config.ts` 确认 base 路径配置正确
- [ ] 验证：单独运行 `uvicorn` 可访问完整应用

### v0.4.0-dev.2 — 托盘应用核心
- [ ] 创建 `apps/tray/` 目录结构
- [ ] `tray_app.py`：pystray 托盘主程序 + 右键菜单
- [ ] `backend_manager.py`：后端进程启动/停止/健康检查/自动重启
- [ ] `config.py`：托盘配置（端口、超时等）
- [ ] 托盘图标资源（4 种状态 PNG）
- [ ] 验证：运行 tray_app.py，托盘出现 → 后端自动启动 → 菜单可打开浏览器

### v0.4.0-dev.3 — 一键启动器 + 状态轮询 + 图标动态变色
- [ ] `LarkSync.pyw`（Windows 无终端启动器）
- [ ] `LarkSync.command`（macOS 启动器）
- [ ] `status_poller.py`：定期查询 /health + /sync/tasks/status
- [ ] 托盘图标根据状态动态切换颜色
- [ ] 后端新增 `GET /api/tray/status` 聚合状态接口
- [ ] 验证：双击 .pyw 启动 → 图标随同步状态变色

### v0.4.0-dev.4 — 系统通知 + 开机自启动
- [ ] `notifier.py`：plyer 系统通知（同步完成/冲突/错误）
- [ ] 通知去重（60s 内同类不重复）
- [ ] `autostart.py`：Windows 快捷方式 / macOS LaunchAgent
- [ ] 托盘菜单"开机自启动"选项可切换
- [ ] 后端新增 `POST /api/tray/pause-all` / `resume-all` 接口
- [ ] 验证：冲突时弹出通知 → 开机自启功能正常

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
| 2026-02-07 | 初始创建，v0.3.x 已完成，v0.4.x 开始规划 |
