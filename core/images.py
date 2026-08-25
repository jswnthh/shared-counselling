"""Convert an uploaded counsellor portrait into static WebP variants.

Writes:

    static/images/counsellors/cards/<slug>.webp   (600px)
    static/images/counsellors/thumbs/<slug>.webp  (112px)

Also mirrors into STATIC_ROOT when present so WhiteNoise can serve the
new files without a collectstatic / redeploy.
"""

from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

THUMB_SIZE = 112
CARD_SIZE = 600
WEBP_QUALITY = 82


def card_relpath(slug):
    return f"images/counsellors/cards/{slug}.webp"


def thumb_relpath(slug):
    return f"images/counsellors/thumbs/{slug}.webp"


def _open_rgb(file_obj):
    image = Image.open(file_obj)
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")
    return image


def _webp_bytes(image):
    buf = BytesIO()
    image.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)
    return buf.getvalue()


def _fitted(image, max_edge):
    fitted = image.copy()
    fitted.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return fitted


def _static_roots():
    """Source static/ plus STATIC_ROOT when it exists (production WhiteNoise)."""
    roots = []
    for path in getattr(settings, "STATICFILES_DIRS", []) or []:
        roots.append(Path(path))
    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root:
        root = Path(static_root)
        if root not in roots:
            roots.append(root)
    return roots


def _write(relpath, content):
    for root in _static_roots():
        dest = root / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)


def write_static_portrait(slug, file_obj):
    """Resize and save card + thumb WebPs. Returns the card relative path."""
    if not slug:
        raise ValueError("counsellor slug is required to name the portrait files")

    image = _open_rgb(file_obj)
    _write(card_relpath(slug), _webp_bytes(_fitted(image, CARD_SIZE)))
    _write(thumb_relpath(slug), _webp_bytes(_fitted(image, THUMB_SIZE)))
    return card_relpath(slug)
