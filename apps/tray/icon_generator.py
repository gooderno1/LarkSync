"""
托盘图标生成器 — 基于品牌 Logo 生成 4 种状态图标。

使用 assets/branding/LarkSync_Logo_Icon_FullColor.png 为原始图标，
生成 4 种状态变体：
  - idle:    原始配色（蓝绿渐变）
  - syncing: 蓝色色调
  - error:   红色色调
  - paused:  灰色（去饱和）
"""

from pathlib import Path

ICONS_DIR = Path(__file__).resolve().parent / "icons"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRAND_ICON = PROJECT_ROOT / "assets" / "branding" / "LarkSync_Logo_Icon_FullColor.png"


def generate_icons(size: int = 64, force: bool = False) -> dict[str, Path]:
    """
    基于品牌 Logo 生成托盘图标 PNG 文件。
    返回 {状态名: 文件路径} 字典。
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter
    except ImportError:
        return {}

    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    # 检查品牌图标是否存在
    if not BRAND_ICON.is_file():
        return _generate_fallback_icons(size, force)

    result: dict[str, Path] = {}

    # 加载原始图标并裁剪白色边缘，缩放到目标尺寸
    original = Image.open(str(BRAND_ICON)).convert("RGBA")
    original = _trim_whitespace(original)
    original = original.resize((size, size), Image.LANCZOS)

    # ---- idle: 原始配色 ----
    idle_path = ICONS_DIR / "icon_idle.png"
    if not idle_path.is_file() or force:
        original.save(str(idle_path), "PNG")
    result["idle"] = idle_path

    # ---- syncing: 增强蓝色饱和度 ----
    syncing_path = ICONS_DIR / "icon_syncing.png"
    if not syncing_path.is_file() or force:
        enhanced = ImageEnhance.Color(original).enhance(1.4)
        enhanced = ImageEnhance.Brightness(enhanced).enhance(1.1)
        enhanced.save(str(syncing_path), "PNG")
    result["syncing"] = syncing_path

    # ---- error: 红色色调 ----
    error_path = ICONS_DIR / "icon_error.png"
    if not error_path.is_file() or force:
        error_img = _apply_color_tint(original, (220, 50, 50))
        error_img.save(str(error_path), "PNG")
    result["error"] = error_path

    # ---- paused: 灰度 ----
    paused_path = ICONS_DIR / "icon_paused.png"
    if not paused_path.is_file() or force:
        gray = ImageEnhance.Color(original).enhance(0.0)
        gray = ImageEnhance.Brightness(gray).enhance(0.8)
        gray.save(str(paused_path), "PNG")
    result["paused"] = paused_path

    return result


def _trim_whitespace(img: "Image.Image", threshold: int = 240) -> "Image.Image":
    """裁剪图片周围的白色/近白色空白区域。"""
    from PIL import Image
    # 转为 RGBA
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    # 找到非白色/非透明像素的边界
    pixels = img.load()
    w, h = img.size
    left, top, right, bottom = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a > 30 and (r < threshold or g < threshold or b < threshold):
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right <= left or bottom <= top:
        return img
    # 添加少量边距
    margin = max(2, min(w, h) // 20)
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(w, right + margin)
    bottom = min(h, bottom + margin)
    # 裁剪为正方形（取最大边）
    crop_w = right - left
    crop_h = bottom - top
    if crop_w != crop_h:
        side = max(crop_w, crop_h)
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        left = max(0, cx - side // 2)
        top = max(0, cy - side // 2)
        right = min(w, left + side)
        bottom = min(h, top + side)
    return img.crop((left, top, right, bottom))


def _apply_color_tint(
    img: "Image.Image", tint_rgb: tuple[int, int, int]
) -> "Image.Image":
    """对图像应用颜色着色（保留明度通道）。"""
    from PIL import Image
    rgba = img.convert("RGBA")
    r, g, b, a = rgba.split()
    # 转灰度作为明度参考
    gray = img.convert("L")
    # 用灰度值按比例混合目标色
    tr, tg, tb = tint_rgb
    new_r = gray.point(lambda p: int(p / 255.0 * tr))
    new_g = gray.point(lambda p: int(p / 255.0 * tg))
    new_b = gray.point(lambda p: int(p / 255.0 * tb))
    tinted = Image.merge("RGBA", (new_r, new_g, new_b, a))
    return tinted


def _generate_fallback_icons(size: int, force: bool) -> dict[str, Path]:
    """品牌图标不存在时，生成简单彩色圆形图标作为 fallback。"""
    from PIL import Image, ImageDraw

    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    colors = {
        "idle":    (16, 185, 129),
        "syncing": (51, 112, 255),
        "error":   (244, 63, 94),
        "paused":  (113, 113, 122),
    }
    result: dict[str, Path] = {}
    for name, color in colors.items():
        path = ICONS_DIR / f"icon_{name}.png"
        if path.is_file() and not force:
            result[name] = path
            continue
        scale = 4
        s = size * scale
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([2, 2, s - 3, s - 3], fill=(*color, 230))
        img = img.resize((size, size), Image.LANCZOS)
        img.save(str(path), "PNG")
        result[name] = path
    return result


def get_icon_path(state: str) -> Path | None:
    """获取指定状态的图标路径，不存在则尝试生成。"""
    icon_path = ICONS_DIR / f"icon_{state}.png"
    if icon_path.is_file():
        return icon_path
    icons = generate_icons()
    return icons.get(state)


if __name__ == "__main__":
    icons = generate_icons(size=64, force=True)
    for name, path in icons.items():
        print(f"  {name}: {path}")
    print(f"\n生成了 {len(icons)} 个图标到 {ICONS_DIR}")
