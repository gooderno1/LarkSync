# LarkSync

运行在本地的“双向同步助手”，通过智能转码引擎连接飞书云端（Docx）与本地文件系统（Markdown/Office）。实现“本地编辑，云端协作”的无缝工作流，打通个人数据孤岛与企业知识库。

## 功能概览
- 全栈脚手架已搭建：FastAPI 后端 + Vite React TypeScript 前端
- 统一开发入口：根目录 `npm run dev` 并行启动前后端
- 预留同步核心模块与数据层目录结构（core / services / db）

## 开发
- 后端：`apps/backend`（FastAPI，默认端口 8000）
- 前端：`apps/frontend`（Vite，默认端口 3000）
