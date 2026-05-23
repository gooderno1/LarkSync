# FastAPI 0.128.0 在 _compat.shared 中保留了面向 pydantic.v1 的运行时兼容探测。
# LarkSync 全量使用 Pydantic v2，这里显式告诉 PyInstaller 忽略该导入，避免
# Python 3.14+ 构建时把未使用的 v1 兼容层纳入分析并触发上游告警。
excludedimports = ["pydantic.v1"]
