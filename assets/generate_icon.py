"""Generate Accentually's scalable, antialiased Windows tray and app icon."""
from pathlib import Path
from PIL import Image, ImageDraw


def generate_ico(output_path):
    # Draw at high resolution, then downsample so curves stay smooth at tray size.
    scale = 4
    size = 256 * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    def box(*coords):
        return tuple(int(value * scale) for value in coords)

    # A compact violet tile and a simple, bold accented "a".
    draw.rounded_rectangle(box(8, 8, 248, 248), radius=57 * scale, fill="#5865f2")
    draw.rounded_rectangle(box(91, 48, 165, 62), radius=7 * scale, fill="#ffffff")
    draw.ellipse(box(66, 91, 178, 203), fill="#ffffff")
    draw.rounded_rectangle(box(153, 91, 185, 203), radius=13 * scale, fill="#ffffff")
    draw.ellipse(box(97, 122, 148, 173), fill="#5865f2")

    image = image.resize((256, 256), Image.Resampling.LANCZOS)
    image.save(output_path, format="ICO", sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    generate_ico(Path(__file__).with_name("app_icon.ico"))
