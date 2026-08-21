"""Generate PeerCode app icons (Windows .ico + cross-platform .png)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def rounded_gradient(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    radius = max(4, size // 5)
    top = (242, 197, 127)
    bottom = (232, 177, 90)
    grad = Image.new("RGBA", (size, size))
    gd = ImageDraw.Draw(grad)
    for y in range(size):
        t = y / max(1, size - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        gd.line([(0, y), (size, y)], fill=color)
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)
    return img


def draw_letter(img: Image.Image, size: int) -> None:
    d = ImageDraw.Draw(img)
    font_size = int(size * 0.62)
    font = None
    for candidate in ("georgia.ttf", "times.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(f"C:\\Windows\\Fonts\\{candidate}", font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    text = "P"
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - w) / 2 - bbox[0]
    y = (size - h) / 2 - bbox[1]
    # subtle dark drop shadow for depth
    shadow = tuple(int(c * 0.55) for c in (28, 20, 8)) + (120,)
    d.text((x + max(1, size // 96), y + max(1, size // 96)), text, font=font, fill=shadow)
    d.text((x, y), text, font=font, fill=(28, 20, 8, 255))


def main() -> None:
    ASSETS.mkdir(exist_ok=True)

    master = rounded_gradient(256)
    draw_letter(master, 256)

    master.save(ASSETS / "icon_256.png")
    master.resize((512, 512), Image.LANCZOS).save(ASSETS / "icon_512.png")

    # PIL derives all frames from the master using `sizes`
    master.save(ASSETS / "PeerCode.ico", format="ICO", sizes=[(s, s) for s in SIZES])
    print("icons written to", ASSETS)


if __name__ == "__main__":
    main()
