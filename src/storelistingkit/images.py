"""Compose real screenshots into exact store image sizes (ADR 0003). No generated content."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError

from .config import LIMITS
from .models import ImageResult, StoreId
from .stores import image_slots

ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
Image.MAX_IMAGE_PIXELS = LIMITS.max_image_pixels


class ImageError(ValueError):
    pass


def load_image(path: Path) -> Image.Image:
    """Open and fully decode an untrusted image with format, size and pixel limits."""
    if path.stat().st_size > LIMITS.max_image_bytes:
        raise ImageError(f"{path.name}: larger than {LIMITS.max_image_bytes // (1024 * 1024)} MB.")
    try:
        with Image.open(path) as im:
            if im.format not in ALLOWED_FORMATS:
                raise ImageError(f"{path.name}: unsupported format {im.format}; use PNG, JPEG or WebP.")
            im.load()
            im = ImageOps.exif_transpose(im)
            return im.convert("RGB")
    except Image.DecompressionBombError as exc:
        raise ImageError(f"{path.name}: image has too many pixels.") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageError(f"{path.name}: not a readable image.") from exc


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def compose(src: Image.Image, width: int, height: int, caption: str | None = None) -> Image.Image:
    """Contain-fit ``src`` over a blurred, darkened cover-fit copy of itself; optional caption band."""
    bg = ImageOps.fit(src, (width, height), method=Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=max(4, min(width, height) // 25)))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (12, 14, 20)), 0.45)

    band = int(height * 0.16) if caption else 0
    margin = max(2, int(min(width, height) * 0.03)) if caption else 0
    box_w, box_h = width - 2 * margin, height - band - 2 * margin
    fg = ImageOps.contain(src, (max(1, box_w), max(1, box_h)), method=Image.Resampling.LANCZOS)
    x = (width - fg.width) // 2
    y = margin + (box_h - fg.height) // 2
    bg.paste(fg, (x, y))

    if caption:
        draw = ImageDraw.Draw(bg)
        size = max(10, int(band * 0.5))
        font = _font(size)
        text = caption
        while size > 10 and draw.textlength(text, font=font) > width * 0.92:
            size -= 2
            font = _font(size)
        if draw.textlength(text, font=font) > width * 0.92:
            while len(text) > 1 and draw.textlength(text + "…", font=font) > width * 0.92:
                text = text[:-1]
            text += "…"
        draw.rectangle([0, height - band, width, height], fill=(12, 14, 20))
        draw.text((width / 2, height - band / 2), text, font=font, fill=(240, 242, 248), anchor="mm")
    return bg


def build_store_images(store: StoreId, screenshots: list[Path], title: str, out_dir: Path) -> list[ImageResult]:
    """Fill each image slot of ``store`` from the screenshots, in upload order."""
    if not screenshots:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    loaded = [(p, load_image(p)) for p in screenshots]
    results: list[ImageResult] = []
    for slot, s in image_slots(store).items():
        w, h = s["width"], s["height"]
        sources = loaded if s.get("max_count", 1) > 1 else loaded[:1]
        for idx, (path, im) in enumerate(sources[: s.get("max_count", 1)], start=1):
            name = f"{slot}.png" if s.get("max_count", 1) == 1 else f"{slot}_{idx:02d}.png"
            img = compose(im, w, h, caption=title if s.get("caption") else None)
            img.save(out_dir / name, format="PNG", optimize=True)
            results.append(ImageResult(store=store, slot=slot, filename=name, width=img.width,
                                       height=img.height, source=path.name))
    return results
