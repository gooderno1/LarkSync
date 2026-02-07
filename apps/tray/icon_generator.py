"""
托盘图标生成器 — 使用 Pillow 程序化生成 4 种状态图标。
首次运行时自动在 apps/tray/icons/ 下生成 PNG 图标。
"""

from pathlib import Path

ICONS_DIR = Path(__file__).resolve().parent / "icons"

# 图标颜色映射
ICON_COLORS = {
    "idle":     ("#10b981", "#065f46"),   # 绿色：空闲/正常
    "syncing":  ("#3370ff", "#1d4ed8"),   # 蓝色：同步中
    "error":    ("#f43f5e", "#9f1239"),   # 红色：有错误
    "paused":   ("#71717a", "#3f3f46"),   # 灰色：已暂停
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def generate_icons(size: int = 64, force: bool = False) -> dict[str, Path]:
    """
    生成托盘图标 PNG 文件。
    返回 {状态名: 文件路径} 字典。
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # Pillow 未安装，返回空字典（使用 fallback 逻辑）
        return {}

    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}

    for name, (color_main, color_dark) in ICON_COLORS.items():
        icon_path = ICONS_DIR / f"icon_{name}.png"
        if icon_path.is_file() and not force:
            result[name] = icon_path
            continue

        # 创建带抗锯齿的圆形图标
        scale = 4  # 超采样倍率
        s = size * scale
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 外圈
        rgb_main = _hex_to_rgb(color_main)
        draw.ellipse([2, 2, s - 3, s - 3], fill=(*rgb_main, 230))

        # 内圈高光
        margin = s // 5
        draw.ellipse(
            [margin, margin, s - margin, s - margin],
            fill=(*_hex_to_rgb(color_dark), 180),
        )

        # 中心点
        center_margin = s // 3
        draw.ellipse(
            [center_margin, center_margin, s - center_margin, s - center_margin],
            fill=(*rgb_main, 255),
        )

        # 缩放到目标尺寸（抗锯齿）
        img = img.resize((size, size), Image.LANCZOS)
        img.save(str(icon_path), "PNG")
        result[name] = icon_path

    return result


def get_icon_path(state: str) -> Path | None:
    """获取指定状态的图标路径，不存在则尝试生成。"""
    icon_path = ICONS_DIR / f"icon_{state}.png"
    if icon_path.is_file():
        return icon_path
    icons = generate_icons()
    return icons.get(state)


if __name__ == "__main__":
    icons = generate_icons(force=True)
    for name, path in icons.items():
        print(f"  {name}: {path}")
    print(f"\n生成了 {len(icons)} 个图标到 {ICONS_DIR}")
