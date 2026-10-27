"""Screen grabbing and image conversion helpers (PIL <-> QImage)."""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageGrab
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage


def _qimage_from_pil(img: Image.Image) -> QImage:
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    data = img.tobytes("raw", img.mode)
    qimg = QImage(data, img.width, img.height, img.width * len(img.mode),
                  QImage.Format.Format_RGB888 if img.mode == "RGB" else QImage.Format.Format_RGBA8888)
    return qimg.copy()  # detach from the temporary Python buffer


def grab_desktop() -> QImage:
    """Grab the whole virtual desktop in physical pixels."""
    img = ImageGrab.grab(all_screens=True)
    return _qimage_from_pil(img)


def grab_rect(rect: QRect) -> QImage:
    """Grab an absolute screen rectangle (physical pixels)."""
    img = ImageGrab.grab(all_screens=True)
    box = (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
    return _qimage_from_pil(img.crop(box))


def qimage_to_pil(qimg: QImage) -> Image.Image:
    fmt = QImage.Format.Format_RGBA8888 if qimg.hasAlphaChannel() else QImage.Format.Format_RGB888
    converted = qimg.convertToFormat(fmt)
    data = bytes(converted.constBits())
    stride = converted.bytesPerLine()
    width, height = converted.width(), converted.height()
    channels = 4 if fmt == QImage.Format.Format_RGBA8888 else 3
    row = width * channels
    if stride != row:
        packed = bytearray()
        for y in range(height):
            packed += data[y * stride: y * stride + row]
        data = bytes(packed)
    return Image.frombytes("RGBA" if channels == 4 else "RGB", (width, height), data)


def pil_to_qimage(img: Image.Image) -> QImage:
    return _qimage_from_pil(img)


def blur_region(qimg: QImage, rect: QRect, radius: int = 10) -> QImage:
    """Return qimg with `rect` gaussian-blurred."""
    pil = qimage_to_pil(qimg).convert("RGBA")
    box = (max(0, rect.x()), max(0, rect.y()),
           min(pil.width, rect.x() + rect.width()), min(pil.height, rect.y() + rect.height()))
    if box[2] <= box[0] or box[3] <= box[1]:
        return qimg
    patch = pil.crop(box).filter(ImageFilter.GaussianBlur(max(2, radius)))
    pil.paste(patch, box)
    return pil_to_qimage(pil)


def pixelate_region(qimg: QImage, rect: QRect, block: int = 10) -> QImage:
    """Return qimg with `rect` pixelated."""
    pil = qimage_to_pil(qimg).convert("RGBA")
    box = (max(0, rect.x()), max(0, rect.y()),
           min(pil.width, rect.x() + rect.width()), min(pil.height, rect.y() + rect.height()))
    if box[2] <= box[0] or box[3] <= box[1]:
        return qimg
    patch = pil.crop(box)
    w, h = patch.size
    small = patch.resize((max(1, w // max(2, block)), max(1, h // max(2, block))), Image.Resampling.BOX)
    patch = small.resize((w, h), Image.Resampling.NEAREST)
    pil.paste(patch, box)
    return pil_to_qimage(pil)


def add_pretty_frame(qimg: QImage, margin: int = 28, radius: int = 10,
                     shadow: int = 18, background: str = "#f4f5f7") -> QImage:
    """Wrap the capture in a rounded card with a soft drop shadow."""
    src = qimage_to_pil(qimg).convert("RGBA")
    w, h = src.size
    canvas_w = w + margin * 2
    canvas_h = h + margin * 2
    pad = shadow * 2

    card = Image.new("L", (w, h), 0)
    ImageDraw.Draw(card).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    rounded = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rounded.paste(src, (0, 0), card)

    canvas = Image.new("RGBA", (canvas_w + pad, canvas_h + pad), (0, 0, 0, 0))
    base = Image.new("RGBA", canvas.size, background)
    canvas = Image.alpha_composite(canvas, base)

    shadow_mask = Image.new("L", (canvas_w + pad, canvas_h + pad), 0)
    shadow_mask.paste(card, (margin + pad // 2, margin + pad // 2 + 6))
    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow_mask.filter(ImageFilter.GaussianBlur(shadow)).point(lambda v: int(v * 0.35)))
    canvas = Image.alpha_composite(canvas, shadow_layer)
    canvas.paste(rounded, (margin + pad // 2, margin + pad // 2), rounded)
    return pil_to_qimage(canvas.convert("RGB"))


def add_watermark(qimg: QImage, text: str, color: str = "#FFFFFF",
                  opacity: int = 55, margin: int = 16, size: int | None = None) -> QImage:
    """Stamp a subtle text watermark in the bottom-right corner."""
    if not text.strip():
        return qimg
    pil = qimage_to_pil(qimg).convert("RGBA")
    overlay = Image.new("RGBA", pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_size = size or max(14, int(pil.height * 0.028))
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except Exception:
        from PIL import ImageFont
        font = ImageFont.load_default()
    rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    alpha = int(255 * max(0, min(100, opacity)) / 100)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = (pil.width - tw - margin, pil.height - th - margin)
    # a faint outline keeps the text legible on any background
    draw.text((pos[0] + 1, pos[1] + 1), text, font=font, fill=(0, 0, 0, int(alpha * 0.6)))
    draw.text(pos, text, font=font, fill=(*rgb, alpha))
    return pil_to_qimage(Image.alpha_composite(pil, overlay).convert("RGB"))


def resize_image(qimg: QImage, width: int | None = None, height: int | None = None,
                 percent: float | None = None) -> QImage:
    pil = qimage_to_pil(qimg)
    w, h = pil.size
    if percent:
        nw, nh = max(1, int(w * percent / 100)), max(1, int(h * percent / 100))
    elif width:
        nw = max(1, int(width))
        nh = max(1, int(h * nw / w))
    elif height:
        nh = max(1, int(height))
        nw = max(1, int(w * nh / h))
    else:
        return qimg
    return pil_to_qimage(pil.resize((nw, nh), Image.Resampling.LANCZOS))


def scale_image(qimg: QImage, percent: int) -> QImage:
    """Resize by a percentage (100 = unchanged)."""
    percent = max(10, min(100, int(percent)))
    if percent >= 100:
        return qimg
    pil = qimage_to_pil(qimg)
    width = max(1, int(pil.width * percent / 100))
    height = max(1, int(pil.height * percent / 100))
    return pil_to_qimage(pil.resize((width, height), Image.Resampling.LANCZOS))


def encode(qimg: QImage, fmt: str, quality: int = 92, dpi: int = 96,
           compress_level: int = 6) -> bytes:
    """Encode to PNG / JPEG / WEBP bytes.

    ``dpi`` is written as file metadata (it does not change pixel data), while
    ``compress_level`` (PNG) and ``quality`` (JPEG/WebP) change the file weight.
    """
    buf = io.BytesIO()
    fmt = (fmt or "png").lower()
    dpi = max(36, min(1200, int(dpi)))
    compress_level = max(1, min(9, int(compress_level)))
    pil = qimage_to_pil(qimg)
    if fmt in ("jpg", "jpeg"):
        # JPEG has no alpha: flatten transparent holes onto white
        if pil.mode == "RGBA":
            flat = Image.new("RGB", pil.size, (255, 255, 255))
            flat.paste(pil, mask=pil.split()[3])
            pil = flat
        pil.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, dpi=(dpi, dpi))
    elif fmt == "webp":
        pil.save(buf, "WEBP", quality=quality, method=6)
    else:
        pil.save(buf, "PNG", optimize=True, compress_level=compress_level, dpi=(dpi, dpi))
    return buf.getvalue()


def thumbnail(qimg: QImage, longest: int = 160) -> QImage:
    pil = qimage_to_pil(qimg)
    pil.thumbnail((longest, longest), Image.Resampling.LANCZOS)
    return pil_to_qimage(pil)


def save_qimage(qimg: QImage, path, fmt: str | None = None, quality: int = 92,
                dpi: int = 96, compress_level: int = 6) -> None:
    fmt = (fmt or str(path).rsplit(".", 1)[-1]).lower()
    with open(path, "wb") as fh:
        fh.write(encode(qimg, fmt, quality, dpi=dpi, compress_level=compress_level))


def open_image(path) -> Optional[QImage]:
    try:
        with Image.open(path) as img:
            return _qimage_from_pil(img.convert("RGB"))
    except Exception:
        return None
