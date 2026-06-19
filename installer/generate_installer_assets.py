"""Generate branded bitmap assets for the Inno Setup wizard."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


INSTALLER_DIR = Path(__file__).resolve().parent
PROJECT_DIR = INSTALLER_DIR.parent
ASSET_DIR = INSTALLER_DIR / "assets"
APP_ICON = PROJECT_DIR / "assets" / "asud_icon.png"

DARK = "#102D36"
TEAL = "#16877C"
TEAL_LIGHT = "#59B6A7"
WHITE = "#FFFFFF"
MUTED = "#B7CDD1"


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_name = "segoeuib.ttf" if bold else "segoeui.ttf"
    font_path = Path("C:/Windows/Fonts") / font_name
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def fit_icon(size: tuple[int, int]) -> Image.Image:
    icon = Image.open(APP_ICON).convert("RGBA")
    icon.thumbnail(size, Image.Resampling.LANCZOS)
    return icon


def draw_centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill: str) -> None:
    x, y = xy
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text((x - width // 2, y), text, font=font, fill=fill)


def create_large_wizard_image() -> Image.Image:
    image = Image.new("RGB", (164, 314), DARK)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((18, 22, 146, 150), radius=24, fill="#123C45")
    draw.rounded_rectangle((22, 26, 142, 146), radius=22, outline=TEAL, width=2)
    icon = fit_icon((88, 88))
    image.paste(icon, ((164 - icon.width) // 2, 42), icon)

    draw_centered(draw, (82, 165), "АСУД", load_font(24, bold=True), WHITE)
    draw_centered(draw, (82, 201), "Реестр", load_font(12, bold=True), TEAL_LIGHT)
    draw_centered(draw, (82, 218), "диссертаций", load_font(12, bold=True), TEAL_LIGHT)

    draw.line((28, 251, 136, 251), fill="#2D525A", width=1)
    draw_centered(draw, (82, 264), "ВМедА", load_font(11, bold=True), MUTED)
    draw_centered(draw, (82, 280), "им. С.М. Кирова", load_font(9), MUTED)

    draw.rectangle((0, 306, 164, 314), fill=TEAL)
    return image


def create_small_wizard_image() -> Image.Image:
    image = Image.new("RGB", (55, 55), WHITE)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, 53, 53), radius=12, fill=DARK)
    draw.rounded_rectangle((3, 3, 51, 51), radius=10, outline=TEAL, width=2)
    icon = fit_icon((39, 39))
    image.paste(icon, ((55 - icon.width) // 2, (55 - icon.height) // 2), icon)
    return image


def main() -> None:
    if not APP_ICON.exists():
        raise FileNotFoundError(f"Не найдена иконка приложения: {APP_ICON}")

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    create_large_wizard_image().save(ASSET_DIR / "wizard-large.bmp", format="BMP")
    create_small_wizard_image().save(ASSET_DIR / "wizard-small.bmp", format="BMP")
    print(f"Созданы ресурсы установщика: {ASSET_DIR}")


if __name__ == "__main__":
    main()
