import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import icon_generator


def test_macos_app_icon_is_valid_multiresolution_icns(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "brand.png"
    output = tmp_path / "LarkSync.icns"
    image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    for x in range(120, 904):
        for y in range(240, 784):
            image.putpixel((x, y), (51, 112, 255, 255))
    image.save(source)
    monkeypatch.setattr(icon_generator, "BRAND_ICON", source)
    monkeypatch.setattr(icon_generator, "MACOS_APP_ICON", output)

    assert icon_generator.generate_macos_app_icon(force=True) == output
    with Image.open(output) as generated:
        assert generated.format == "ICNS"
        assert generated.width >= 512
        assert generated.height >= 512


def test_macos_development_app_icon_uses_separate_visible_badge(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "brand.png"
    stable_output = tmp_path / "LarkSync.icns"
    development_output = tmp_path / "LarkSync-Dev.icns"
    Image.new("RGBA", (1024, 1024), (51, 112, 255, 255)).save(source)
    monkeypatch.setattr(icon_generator, "BRAND_ICON", source)
    monkeypatch.setattr(icon_generator, "MACOS_APP_ICON", stable_output)
    monkeypatch.setattr(icon_generator, "MACOS_DEV_APP_ICON", development_output)

    assert (
        icon_generator.generate_macos_development_app_icon(force=True)
        == development_output
    )
    assert development_output.is_file()
    assert not stable_output.exists()

    with Image.open(development_output) as generated:
        rgba = generated.convert("RGBA")
        width, height = rgba.size
        badge_pixels = 0
        badge_region = rgba.crop((width // 2, height * 2 // 3, width, height))
        for red, green, blue, alpha in badge_region.get_flattened_data():
            if alpha > 220 and red > 220 and 70 < green < 190 and blue < 80:
                badge_pixels += 1
        assert badge_pixels > width * height * 0.01


def test_macos_template_icons_fill_menu_bar_canvas(monkeypatch, tmp_path: Path) -> None:
    icons_dir = tmp_path / "icons"
    source = tmp_path / "brand.png"
    Image.new("RGBA", (512, 256), (0, 0, 0, 255)).save(source)
    monkeypatch.setattr(icon_generator, "ICONS_DIR", icons_dir)
    monkeypatch.setattr(icon_generator, "BRAND_ICON", source)

    generated = icon_generator.generate_icons(size=64, force=True)

    for state in ("idle", "syncing", "error", "paused"):
        with Image.open(generated[f"macos_{state}"]) as image:
            bbox = image.getchannel("A").getbbox()
            assert bbox is not None
            assert bbox[3] - bbox[1] >= 48
