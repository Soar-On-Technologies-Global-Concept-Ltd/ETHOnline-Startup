"""Validate and clean uploads before hashing: the bytes we hash are the bytes we store and anchor."""
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import UnsupportedMedia

Image.MAX_IMAGE_PIXELS = 40_000_000
ALLOWED = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png"), "WEBP": ("image/webp", "webp")}


def sanitize(raw: bytes) -> tuple[bytes, str, str]:
    """Returns (clean_bytes, mime, extension). EXIF (including GPS) is dropped; orientation is applied first."""
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(raw)) as im:
            fmt = im.format
            if fmt not in ALLOWED:
                raise UnsupportedMedia(f"{fmt} is not accepted; use JPEG, PNG or WebP")
            clean = ImageOps.exif_transpose(im)
            if fmt == "JPEG" and clean.mode not in ("RGB", "L"):
                clean = clean.convert("RGB")
            out = io.BytesIO()
            clean.save(out, format=fmt, **({"quality": 90} if fmt != "PNG" else {}))
    except UnsupportedMedia:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as err:
        raise UnsupportedMedia("file is not a readable image") from err
    mime, ext = ALLOWED[fmt]
    return out.getvalue(), mime, ext
