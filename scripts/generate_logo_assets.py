from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRANDING_DIR = PROJECT_ROOT / "assets" / "branding"
ORIGINAL_DIR = BRANDING_DIR / "archive" / "2026-07-06-original" / "branding"
PUBLIC_DIR = PROJECT_ROOT / "apps" / "frontend" / "public"
TRAY_ICONS_DIR = PROJECT_ROOT / "apps" / "tray" / "icons"

ORIGINAL_ICON = ORIGINAL_DIR / "LarkSync_Logo_Icon_FullColor.png"
ORIGINAL_HORIZONTAL = ORIGINAL_DIR / "LarkSync_Logo_Horizontal_Lockup_FullColor.png"
ORIGINAL_COMPACT = ORIGINAL_DIR / "LarkSync_Logo_CompactVertical_FullColor.png"

ICON_PNG = BRANDING_DIR / "LarkSync_Logo_Icon_FullColor.png"
HORIZONTAL_PNG = BRANDING_DIR / "LarkSync_Logo_Horizontal_Lockup_FullColor.png"
COMPACT_PNG = BRANDING_DIR / "LarkSync_Logo_CompactVertical_FullColor.png"
WINDOWS_ICO = BRANDING_DIR / "LarkSync.ico"

TRANSPARENT = (0, 0, 0, 0)


def _is_background_pixel(
    pixel: tuple[int, int, int, int],
    *,
    threshold: int = 232,
    max_chroma: int = 42,
) -> bool:
    r, g, b, a = pixel
    if a <= 8:
        return True
    return min(r, g, b) >= threshold and (max(r, g, b) - min(r, g, b)) <= max_chroma


def _remove_connected_light_background(img: Image.Image) -> Image.Image:
    """只移除与画布边缘连通的近白背景，保留 Logo 内部白色细节。"""
    rgba = img.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def index(x: int, y: int) -> int:
        return y * width + x

    def add_if_background(x: int, y: int) -> None:
        idx = index(x, y)
        if visited[idx]:
            return
        visited[idx] = 1
        if _is_background_pixel(pixels[x, y]):
            queue.append((x, y))

    for x in range(width):
        add_if_background(x, 0)
        add_if_background(x, height - 1)
    for y in range(1, height - 1):
        add_if_background(0, y)
        add_if_background(width - 1, y)

    while queue:
        x, y = queue.popleft()
        pixels[x, y] = TRANSPARENT
        if x > 0:
            add_if_background(x - 1, y)
        if x + 1 < width:
            add_if_background(x + 1, y)
        if y > 0:
            add_if_background(x, y - 1)
        if y + 1 < height:
            add_if_background(x, y + 1)

    return rgba


def _trim_alpha(img: Image.Image, margin: int = 0) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(img.width, right + margin)
    bottom = min(img.height, bottom + margin)
    return img.crop((left, top, right, bottom))


def _fit_to_canvas(img: Image.Image, size: tuple[int, int], padding: int = 0) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    trimmed = _trim_alpha(img)
    canvas = Image.new("RGBA", size, TRANSPARENT)
    max_w = size[0] - padding * 2
    max_h = size[1] - padding * 2
    ratio = min(max_w / trimmed.width, max_h / trimmed.height)
    resized = trimmed.resize(
        (max(1, int(trimmed.width * ratio)), max(1, int(trimmed.height * ratio))),
        Image.LANCZOS,
    )
    x = (size[0] - resized.width) // 2
    y = (size[1] - resized.height) // 2
    canvas.alpha_composite(resized, (x, y))
    return canvas


def _resize_to_width(img: Image.Image, width: int) -> Image.Image:
    ratio = width / img.width
    return img.resize((width, max(1, int(img.height * ratio))), Image.LANCZOS)


def _apply_color_tint(img: Image.Image, tint_rgb: tuple[int, int, int]) -> Image.Image:
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    gray = rgba.convert("L")
    tr, tg, tb = tint_rgb
    new_r = gray.point(lambda p: int(p / 255.0 * tr))
    new_g = gray.point(lambda p: int(p / 255.0 * tg))
    new_b = gray.point(lambda p: int(p / 255.0 * tb))
    return Image.merge("RGBA", (new_r, new_g, new_b, alpha))


def _make_status_icon(base: Image.Image, state: str, size: int = 64) -> Image.Image:
    icon = _fit_to_canvas(base, (size, size), padding=max(2, size // 18))
    if state == "syncing":
        icon = ImageEnhance.Color(icon).enhance(1.35)
        return ImageEnhance.Brightness(icon).enhance(1.08)
    if state == "paused":
        icon = ImageEnhance.Color(icon).enhance(0.0)
        return ImageEnhance.Brightness(icon).enhance(0.82)
    if state == "error":
        return _apply_color_tint(icon, (220, 50, 50))
    return icon


def _save_ico(source: Image.Image) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [_fit_to_canvas(source, (size, size), padding=max(1, size // 16)) for size in sizes]
    images[-1].save(
        WINDOWS_ICO,
        format="ICO",
        sizes=[(size, size) for size in sizes],
        append_images=images[:-1],
    )
    images[2].save(PUBLIC_DIR / "favicon.ico", format="ICO", sizes=[(32, 32)])


def _make_preview(icon: Image.Image, horizontal: Image.Image, compact: Image.Image) -> None:
    preview_dir = BRANDING_DIR / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (1400, 900), (245, 249, 255, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.text((56, 44), "LarkSync logo asset cleanup preview", fill=(16, 32, 51, 255))
    draw.text((56, 78), "visual design is the original logo; assets are transparent, cropped, and resized", fill=(82, 101, 122, 255))
    for box in [(56, 132, 480, 560), (520, 132, 1344, 390), (520, 430, 1344, 560), (56, 610, 1344, 820)]:
        draw.rounded_rectangle(box, radius=28, fill=(255, 255, 255, 255), outline=(215, 230, 255, 255), width=2)

    icon_preview = _fit_to_canvas(icon, (360, 360), padding=6)
    canvas.alpha_composite(icon_preview, (88, 166))
    draw.text((92, 520), "Original icon design, cleaned", fill=(82, 101, 122, 255))

    horizontal_preview = _resize_to_width(_trim_alpha(horizontal, margin=8), 760)
    canvas.alpha_composite(horizontal_preview, (552, 210))
    draw.text((552, 342), "Horizontal lockup, same old design", fill=(82, 101, 122, 255))

    compact_preview = _fit_to_canvas(compact, (250, 190), padding=0)
    canvas.alpha_composite(compact_preview, (552, 410))
    draw.text((840, 498), "Compact lockup, cleaned only", fill=(82, 101, 122, 255))

    x = 120
    for state in ("idle", "syncing", "paused", "error"):
        status = _make_status_icon(icon, state, size=96)
        canvas.alpha_composite(status, (x, 660))
        draw.text((x, 770), state, fill=(82, 101, 122, 255))
        x += 180
    draw.text((850, 700), "Tray variants preserve the same silhouette", fill=(16, 32, 51, 255))

    canvas.convert("RGB").save(preview_dir / "larksync-logo-v0.8.0-preview.png", "PNG", optimize=True)


def generate_assets() -> None:
    for source in (ORIGINAL_ICON, ORIGINAL_HORIZONTAL, ORIGINAL_COMPACT):
        if not source.is_file():
            raise FileNotFoundError(f"Missing original logo asset: {source}")

    BRANDING_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    TRAY_ICONS_DIR.mkdir(parents=True, exist_ok=True)

    icon = _remove_connected_light_background(Image.open(ORIGINAL_ICON))
    horizontal = _remove_connected_light_background(Image.open(ORIGINAL_HORIZONTAL))
    compact = _remove_connected_light_background(Image.open(ORIGINAL_COMPACT))

    _fit_to_canvas(icon, (2048, 2048), padding=80).save(ICON_PNG, "PNG", optimize=True)
    _trim_alpha(horizontal, margin=20).save(HORIZONTAL_PNG, "PNG", optimize=True)
    _trim_alpha(compact, margin=20).save(COMPACT_PNG, "PNG", optimize=True)

    _resize_to_width(_trim_alpha(horizontal, margin=8), 600).save(PUBLIC_DIR / "logo-horizontal.png", "PNG", optimize=True)
    _fit_to_canvas(icon, (192, 192), padding=12).save(PUBLIC_DIR / "favicon.png", "PNG", optimize=True)
    _save_ico(icon)

    for state in ("idle", "syncing", "paused", "error"):
        _make_status_icon(icon, state, size=64).save(TRAY_ICONS_DIR / f"icon_{state}.png", "PNG", optimize=True)

    _make_preview(icon, horizontal, compact)


def main() -> None:
    generate_assets()
    print("Generated LarkSync logo assets from the original design:")
    for path in [
        ICON_PNG,
        HORIZONTAL_PNG,
        COMPACT_PNG,
        WINDOWS_ICO,
        PUBLIC_DIR / "logo-horizontal.png",
        PUBLIC_DIR / "favicon.png",
        PUBLIC_DIR / "favicon.ico",
        TRAY_ICONS_DIR / "icon_idle.png",
        TRAY_ICONS_DIR / "icon_syncing.png",
        TRAY_ICONS_DIR / "icon_paused.png",
        TRAY_ICONS_DIR / "icon_error.png",
        BRANDING_DIR / "previews" / "larksync-logo-v0.8.0-preview.png",
    ]:
        print(f"  {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
