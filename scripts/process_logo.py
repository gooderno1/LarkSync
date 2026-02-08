"""
Logo 图片处理脚本 — 去除白色/浅灰色背景，生成透明底色版本。

功能：
  1. 读取 assets/branding/ 中的品牌 Logo 原图
  2. 去除白色/近白色背景像素，替换为透明
  3. 对边缘进行平滑过渡（抗锯齿）
  4. 裁剪多余空白边距
  5. 输出到 apps/frontend/public/ 供前端使用
  6. 同时生成 favicon.png（带圆角和适当边距）
"""

from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 源文件
BRAND_HORIZONTAL = PROJECT_ROOT / "assets" / "branding" / "LarkSync_Logo_Horizontal_Lockup_FullColor.png"
BRAND_ICON = PROJECT_ROOT / "assets" / "branding" / "LarkSync_Logo_Icon_FullColor.png"

# 输出目标
PUBLIC_DIR = PROJECT_ROOT / "apps" / "frontend" / "public"


def remove_white_background(
    img: Image.Image,
    threshold: int = 235,
    smooth_range: int = 25,
) -> Image.Image:
    """
    去除图片中的白色/近白色背景，使其变为透明。

    Args:
        img: PIL Image 对象
        threshold: 高于此值的 RGB 像素视为"白色"，完全透明
        smooth_range: 在 threshold - smooth_range 到 threshold 之间的像素
                      进行渐变透明处理（平滑边缘抗锯齿）
    """
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            min_val = min(r, g, b)

            if min_val >= threshold:
                # 纯白/近白 → 完全透明
                pixels[x, y] = (r, g, b, 0)
            elif min_val >= (threshold - smooth_range):
                # 边缘过渡区 → 渐变透明（抗锯齿）
                # min_val 越接近 threshold → 越透明
                ratio = (threshold - min_val) / smooth_range
                new_alpha = int(ratio * a)
                new_alpha = max(0, min(255, new_alpha))
                pixels[x, y] = (r, g, b, new_alpha)

    return img


def trim_transparent(img: Image.Image, margin: int = 4) -> Image.Image:
    """裁剪图片周围的全透明区域，保留少量边距。"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # 获取 alpha 通道的边界
    bbox = img.getbbox()
    if bbox is None:
        return img

    left, top, right, bottom = bbox
    # 添加边距
    w, h = img.size
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(w, right + margin)
    bottom = min(h, bottom + margin)

    return img.crop((left, top, right, bottom))


def make_transparent_favicon(
    img: Image.Image,
    size: int = 192,
    padding: int = 12,
) -> Image.Image:
    """
    生成透明背景的 favicon，图标居中并留出少量边距。

    Args:
        img: 源图标（透明底色）
        size: 输出尺寸
        padding: 图标与边缘的内边距
    """
    # 创建透明画布
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # 缩放图标到适当大小（留出 padding）
    icon_size = size - padding * 2
    icon = img.copy()
    icon = icon.resize((icon_size, icon_size), Image.LANCZOS)

    # 粘贴到画布中心
    offset = padding
    canvas.paste(icon, (offset, offset), icon)

    return canvas


def process_horizontal_logo(max_width: int = 600):
    """处理水平 Logo → 透明底色版本，缩放到合理的 Web 尺寸。"""
    if not BRAND_HORIZONTAL.is_file():
        print(f"[SKIP] 品牌横版 Logo 不存在：{BRAND_HORIZONTAL}")
        return

    print(f"[INFO] 处理横版 Logo：{BRAND_HORIZONTAL}")
    img = Image.open(str(BRAND_HORIZONTAL))
    img.load()  # 确保图片完全加载
    print(f"       原始尺寸：{img.size}")

    # 去除白色背景
    transparent = remove_white_background(img)
    # 裁剪多余透明区域
    trimmed = trim_transparent(transparent, margin=6)
    print(f"       裁剪后尺寸：{trimmed.size}")

    # 缩放到合理的 Web 尺寸（保持宽高比）
    w, h = trimmed.size
    if w > max_width:
        ratio = max_width / w
        new_h = int(h * ratio)
        trimmed = trimmed.resize((max_width, new_h), Image.LANCZOS)
        print(f"       缩放至：{trimmed.size}")

    output_path = PUBLIC_DIR / "logo-horizontal.png"
    trimmed.save(str(output_path), "PNG", optimize=True)
    print(f"[DONE] 已保存到：{output_path}（{output_path.stat().st_size} bytes）")


def process_favicon():
    """处理图标 Logo → 透明底色 + 圆角 favicon。"""
    if not BRAND_ICON.is_file():
        print(f"[SKIP] 品牌图标不存在：{BRAND_ICON}")
        return

    print(f"[INFO] 处理图标 Logo：{BRAND_ICON}")
    img = Image.open(str(BRAND_ICON))
    print(f"       原始尺寸：{img.size}")

    # 去除白色背景
    transparent = remove_white_background(img)
    trimmed = trim_transparent(transparent, margin=2)

    # 生成 192x192 透明 favicon
    favicon_192 = make_transparent_favicon(trimmed, size=192, padding=12)
    favicon_path = PUBLIC_DIR / "favicon.png"
    favicon_192.save(str(favicon_path), "PNG", optimize=True)
    print(f"[DONE] favicon.png (192x192)：{favicon_path}")

    # 生成 32x32 ICO（边距稍小以保证辨识度）
    favicon_32 = make_transparent_favicon(trimmed, size=32, padding=1)
    ico_path = PUBLIC_DIR / "favicon.ico"
    favicon_32.save(str(ico_path), format="ICO", sizes=[(32, 32)])
    print(f"[DONE] favicon.ico (32x32)：{ico_path}")


def main():
    """主入口。"""
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("LarkSync Logo 处理工具")
    print("=" * 60)

    process_horizontal_logo()
    print()
    process_favicon()

    print()
    print("[OK] 所有 Logo 处理完成！")


if __name__ == "__main__":
    main()
