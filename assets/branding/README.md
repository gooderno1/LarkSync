# LarkSync Branding Assets

本目录保存 LarkSync 品牌源资产和构建期导出资产。

## 当前版本

v0.8.0-dev.1 起，Logo 视觉设计继续沿用旧版“无限循环箭头 + 鸟形 + 蓝绿渐变”。本次只做资产清理和导出：去除边缘连通白底、裁剪大留白、生成透明 PNG / ICO / favicon / 托盘状态图标。

## 源资产

- `archive/2026-07-06-original/branding/LarkSync_Logo_Icon_FullColor.png`
- `archive/2026-07-06-original/branding/LarkSync_Logo_Horizontal_Lockup_FullColor.png`
- `archive/2026-07-06-original/branding/LarkSync_Logo_CompactVertical_FullColor.png`

这些旧版原图是当前资产链路的唯一视觉来源。不要重画图形，不要用新 SVG 替代旧设计。

## 兼容导出资产

- `LarkSync_Logo_Icon_FullColor.png`
- `LarkSync_Logo_Horizontal_Lockup_FullColor.png`
- `LarkSync_Logo_CompactVertical_FullColor.png`
- `LarkSync.ico`

这些文件保留旧文件名，供 README、安装包、前端和托盘构建链路继续使用。

## 前端与托盘导出

- 前端公共资源：`apps/frontend/public/logo-horizontal.png`、`apps/frontend/public/favicon.png`、`apps/frontend/public/favicon.ico`
- 托盘四态图标：`apps/tray/icons/icon_idle.png`、`icon_syncing.png`、`icon_paused.png`、`icon_error.png`

重新生成资产：

```powershell
python scripts/generate_logo_assets.py
python scripts/process_logo.py
python apps/tray/icon_generator.py
```

## 归档

- `archive/2026-07-06-original/`

该目录保存 v0.8.0-dev.1 清理前的旧 Logo、前端 favicon 和托盘四态图标。其中 `branding/` 下的旧版原图同时作为当前资产导出的视觉源。
