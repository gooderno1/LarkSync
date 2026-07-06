# LarkSync v0.7.29

- 发布日期：2026-07-06
- 变更区间：v0.7.28 -> v0.7.29

## 本次更新明细

### 升级重点
- `v0.7.29-dev.1`：安装版打开管理面板、设置、日志中心时都会走 `http://127.0.0.1:8000`。

### 详细变更

#### v0.7.29-dev.1
- 安装版打开管理面板、设置、日志中心时都会走 `http://127.0.0.1:8000`。
- `npm run dev` / `python apps/tray/tray_app.py --dev` 仍会使用 `http://localhost:3666`。
- 验证：
- `python -m pytest tests/test_tray_config.py`（工作目录：`apps/backend`，结果：5 passed）
