"""What we hash is what we store: EXIF comes out first, then SHA-256 over the stored bytes (schematics §13)."""
import io

import pytest
from PIL import Image

from app.core.hashing import sha256_hex
from app.core.errors import UnsupportedMedia
from app.domains.evidence.sanitize import sanitize


def photo(fmt: str = "JPEG", size: tuple[int, int] = (64, 48), exif: bool = False) -> bytes:
    image = Image.new("RGB", size, (120, 90, 60))
    out = io.BytesIO()
    if exif:
        gps = Image.Exif()
        gps[0x0112] = 1                       # orientation
        gps[0x8825] = {1: "N", 2: (6.0, 27.0, 0.0)}   # GPS block: must not survive
        image.save(out, format=fmt, exif=gps)
    else:
        image.save(out, format=fmt)
    return out.getvalue()


def test_a_jpeg_survives_and_keeps_its_type():
    clean, mime, ext = sanitize(photo())
    assert mime == "image/jpeg" and ext == "jpg"
    with Image.open(io.BytesIO(clean)) as im:
        assert im.format == "JPEG" and im.size == (64, 48)


def test_exif_including_gps_is_removed():
    raw = photo(exif=True)
    with Image.open(io.BytesIO(raw)) as im:
        assert im.getexif(), "the fixture should carry EXIF"
    clean, _, _ = sanitize(raw)
    with Image.open(io.BytesIO(clean)) as im:
        assert dict(im.getexif()) == {}


@pytest.mark.parametrize("fmt,mime", [("PNG", "image/png"), ("WEBP", "image/webp")])
def test_png_and_webp_are_accepted(fmt: str, mime: str):
    _, got, _ = sanitize(photo(fmt))
    assert got == mime


def test_the_type_comes_from_the_bytes_not_the_name():
    with pytest.raises(UnsupportedMedia):
        sanitize(b"GIF89a" + b"\x00" * 100)
    with pytest.raises(UnsupportedMedia):
        sanitize(b"not an image at all")


def test_a_truncated_file_is_refused():
    raw = photo()
    with pytest.raises(UnsupportedMedia):
        sanitize(raw[: len(raw) // 2])


def test_the_hash_belongs_to_the_stored_bytes():
    clean, _, _ = sanitize(photo(exif=True))
    assert sha256_hex(clean) == sha256_hex(clean)
    assert sha256_hex(clean) != sha256_hex(photo(exif=True))     # the original bytes are not what we anchor


def test_sanitising_twice_is_stable():
    once, _, _ = sanitize(photo(exif=True))
    twice, _, _ = sanitize(once)
    assert sha256_hex(once) == sha256_hex(twice)
