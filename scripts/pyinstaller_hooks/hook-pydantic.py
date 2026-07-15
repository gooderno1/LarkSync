from PyInstaller.utils.hooks import collect_submodules

# LarkSync 业务模型使用 Pydantic v2，但 FastAPI 的运行时兼容探测会导入
# pydantic.v1 并检查传入模型类型。窗口版若排除该命名空间，会在路由注册阶段退出。
hiddenimports = collect_submodules("pydantic")

excludedimports = []
