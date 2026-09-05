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
MACOS_APP_ICON = PROJECT_ROOT / "assets" / "branding" / "LarkSync.icns"
MACOS_DEV_APP_ICON = PROJECT_ROOT / "assets" / "branding" / "LarkSync-Dev.icns"


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
    original = _prepare_base_icon(original, size)

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

    # macOS 菜单栏使用单色 Template 图标。状态通过形状右下角的小徽标区分，
    # 颜色由系统根据浅色/深色菜单栏自动决定。
    result.update(_generate_macos_template_icons(original, size=size, force=force))

    return result


def generate_macos_app_icon(force: bool = False) -> Path | None:
    """从品牌图生成包含多分辨率表示的 macOS ICNS 应用图标。"""
    return _generate_macos_app_icon(MACOS_APP_ICON, force=force, development=False)


def generate_macos_development_app_icon(force: bool = False) -> Path | None:
    """生成带 DEV 徽标的 macOS 测试版 ICNS，避免与正式版混淆。"""
    return _generate_macos_app_icon(
        MACOS_DEV_APP_ICON,
        force=force,
        development=True,
    )


def _generate_macos_app_icon(
    output: Path,
    *,
    force: bool,
    development: bool,
) -> Path | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    if not BRAND_ICON.is_file():
        return None
    if output.is_file() and not force:
        return output

    output.parent.mkdir(parents=True, exist_ok=True)
    source = Image.open(str(BRAND_ICON)).convert("RGBA")
    canvas = _prepare_macos_app_icon(source, 1024)
    if development:
        canvas = _apply_development_badge(canvas)
    # Pillow 的 ICNS writer 会从 1024px 主图生成 macOS 需要的多尺寸表示。
    canvas.save(str(output), format="ICNS")
    return output


def _prepare_macos_app_icon(source: "Image.Image", size: int) -> "Image.Image":
    """生成符合 macOS 视觉习惯的圆角方形底板，避免横向标识在 Dock 中过小。"""
    from PIL import Image, ImageDraw

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inset = int(size * 0.055)
    radius = int(size * 0.22)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=radius,
        fill=255,
    )
    background = Image.new("RGBA", (size, size))
    pixels = background.load()
    top = (235, 246, 255)
    bottom = (218, 250, 241)
    for y in range(size):
        blend = y / max(size - 1, 1)
        color = tuple(int(top[index] * (1 - blend) + bottom[index] * blend) for index in range(3))
        for x in range(size):
            pixels[x, y] = (*color, 255)
    background.putalpha(mask)
    canvas.alpha_composite(background)

    rgba = source.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    mark = rgba.crop(bbox) if bbox else rgba
    target_width = int(size * 0.72)
    target_height = int(size * 0.38)
    ratio = min(target_width / max(mark.width, 1), target_height / max(mark.height, 1))
    mark = mark.resize(
        (max(1, int(mark.width * ratio)), max(1, int(mark.height * ratio))),
        Image.LANCZOS,
    )
    canvas.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
    return canvas


def _apply_development_badge(source: "Image.Image") -> "Image.Image":
    """在应用图标右下角绘制高对比度 DEV 徽标，小尺寸 Dock 中仍可识别。"""
    from PIL import ImageDraw, ImageFont

    canvas = source.copy().convert("RGBA")
    size = min(canvas.size)
    left = int(size * 0.47)
    top = int(size * 0.72)
    right = int(size * 0.945)
    bottom = int(size * 0.91)
    radius = int(size * 0.055)
    shadow_offset = int(size * 0.014)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (
            left + shadow_offset,
            top + shadow_offset,
            right + shadow_offset,
            bottom + shadow_offset,
        ),
        radius=radius,
        fill=(15, 23, 42, 90),
    )
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=radius,
        fill=(255, 122, 26, 255),
        outline=(255, 255, 255, 255),
        width=max(4, size // 128),
    )

    font_size = max(12, int(size * 0.105))
    font = None
    for candidate in (
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            font = ImageFont.truetype(candidate, font_size)
            break
        except OSError:
            continue
    if font is None:
        try:
            font = ImageFont.load_default(size=font_size)
        except TypeError:
            font = ImageFont.load_default()

    label = "DEV"
    label_box = draw.textbbox((0, 0), label, font=font, stroke_width=max(1, size // 512))
    label_width = label_box[2] - label_box[0]
    label_height = label_box[3] - label_box[1]
    label_x = left + (right - left - label_width) // 2
    label_y = top + (bottom - top - label_height) // 2 - label_box[1]
    draw.text(
        (label_x, label_y),
        label,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=max(1, size // 512),
        stroke_fill=(178, 63, 0, 255),
    )
    return canvas


def _generate_macos_template_icons(
    original: "Image.Image",
    *,
    size: int,
    force: bool,
) -> dict[str, Path]:
    """生成适合 18–22pt 菜单栏的高占比单色图标。"""
    from PIL import Image, ImageDraw

    alpha = original.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        alpha = alpha.crop(bbox)
    target_height = max(1, int(size * 0.82))
    target_width = max(1, min(size - 4, int(alpha.width * target_height / max(alpha.height, 1))))
    alpha = alpha.resize((target_width, target_height), Image.LANCZOS)

    states = {"idle": None, "syncing": "sync", "error": "error", "paused": "pause"}
    result: dict[str, Path] = {}
    for state, badge in states.items():
        path = ICONS_DIR / f"icon_macos_{state}Template.png"
        if not path.is_file() or force:
            image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            glyph = Image.new("RGBA", alpha.size, (0, 0, 0, 255))
            glyph.putalpha(alpha)
            image.alpha_composite(glyph, ((size - target_width) // 2, (size - target_height) // 2))
            draw = ImageDraw.Draw(image)
            if badge:
                radius = max(5, size // 7)
                cx, cy = size - radius - 2, size - radius - 2
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(0, 0, 0, 255))
                if badge == "pause":
                    bar = max(1, radius // 3)
                    draw.rectangle((cx - radius // 2, cy - radius // 2, cx - radius // 2 + bar, cy + radius // 2), fill=(255, 255, 255, 255))
                    draw.rectangle((cx + radius // 2 - bar, cy - radius // 2, cx + radius // 2, cy + radius // 2), fill=(255, 255, 255, 255))
                elif badge == "error":
                    draw.line((cx, cy - radius // 2, cx, cy + radius // 5), fill=(255, 255, 255, 255), width=max(1, radius // 3))
                    draw.ellipse((cx - 1, cy + radius // 2 - 1, cx + 1, cy + radius // 2 + 1), fill=(255, 255, 255, 255))
                else:
                    draw.arc((cx - radius // 2, cy - radius // 2, cx + radius // 2, cy + radius // 2), 30, 300, fill=(255, 255, 255, 255), width=max(1, radius // 3))
            image.save(str(path), "PNG")
        result[f"macos_{state}"] = path
    return result


def _prepare_base_icon(img: "Image.Image", size: int) -> "Image.Image":
    """裁剪源图并放入透明正方形画布，保留小尺寸安全边距。"""
    from PIL import Image
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    trimmed = _trim_whitespace(img)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    padding = max(2, size // 18)
    target = size - padding * 2
    if trimmed.width <= 0 or trimmed.height <= 0:
        return canvas
    ratio = min(target / trimmed.width, target / trimmed.height)
    resized = trimmed.resize(
        (max(1, int(trimmed.width * ratio)), max(1, int(trimmed.height * ratio))),
        Image.LANCZOS,
    )
    x = (size - resized.width) // 2
    y = (size - resized.height) // 2
    canvas.alpha_composite(resized, (x, y))
    return canvas


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
    _r, _g, _b, a = rgba.split()
    gray = img.convert("L")
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


def get_macos_icon_path(state: str) -> Path | None:
    """获取 macOS Template 状态图标。"""
    icon_path = ICONS_DIR / f"icon_macos_{state}Template.png"
    if icon_path.is_file():
        return icon_path
    icons = generate_icons()
    return icons.get(f"macos_{state}")


if __name__ == "__main__":
    icons = generate_icons(size=64, force=True)
    app_icon = generate_macos_app_icon(force=True)
    development_app_icon = generate_macos_development_app_icon(force=True)
    for name, path in icons.items():
        print(f"  {name}: {path}")
    print(f"\n生成了 {len(icons)} 个图标到 {ICONS_DIR}")
    if app_icon:
        print(f"macOS 应用图标: {app_icon}")
    if development_app_icon:
        print(f"macOS 测试版应用图标: {development_app_icon}")
