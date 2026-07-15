# FastAPI 在路由注册阶段会执行 pydantic.v1 兼容探测，即使业务模型全部使用 v2。
# 必须保留该运行时导入，否则窗口版后端会在日志系统初始化前退出。
hiddenimports = ["pydantic.v1"]
excludedimports = []
