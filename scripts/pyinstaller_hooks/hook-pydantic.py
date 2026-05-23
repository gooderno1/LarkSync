from PyInstaller.utils.hooks import collect_submodules

# LarkSync 仅使用 Pydantic v2。默认 hook 会把 pydantic.v1 及其子模块一并收集，
# 在 Python 3.14+ 下会触发“Core Pydantic V1 functionality isn't compatible”的告警。
# 这里显式排除 v1 命名空间，避免把未使用的兼容层打进安装包并污染构建日志。
hiddenimports = collect_submodules(
    "pydantic",
    filter=lambda name: name != "pydantic.v1" and not name.startswith("pydantic.v1."),
)

excludedimports = ["pydantic.v1"]
