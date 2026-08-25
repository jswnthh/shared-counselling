"""DB-backed accessors for the site's content: topics, services, and the
counsellors they map to. Counsellor/topic/service content now lives in real
tables (see core/models.py: ServiceCategory, Topic, Counsellor,
CounsellorWorkingHours, CounsellorSpecialty) editable via Django admin — this
module is a thin query layer that reshapes those rows into the same plain-dict
shapes views.py/forms.py/scheduling.py/templates/JS have always consumed, so
nothing downstream needs to know the data used to be static Python literals.

Every function here queries fresh each call (never cache at module import
time) so admin edits show up immediately, without a server restart.
"""

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.templatetags.static import static

from .models import Counsellor, ServiceCategory, Topic


def get_topic_labels():
    """slug -> display label, across every topic in every category."""
    return {t.slug: t.label for t in Topic.objects.select_related("category")}


def get_services():
    """service slug -> {name, eyebrow, intro, topics: [slug, ...]}."""
    return {
        category.slug: {
            "name": category.name,
            "eyebrow": category.eyebrow,
            "intro": category.intro,
            "topics": [t.slug for t in category.topics.all()],
        }
        for category in ServiceCategory.objects.prefetch_related("topics")
    }


def _placeholder_path(path):
    """Seeded rows still say .png; files on disk are .avif."""
    if path.endswith(".png") and path.startswith("images/face_"):
        return f"{path[:-4]}.avif"
    return path


def _static_url(path):
    """Resolve a path under static/. Missing hashed names must not 500."""
    converted = _placeholder_path(path or "")
    try:
        return static(converted)
    except ValueError:
        pass
    if converted.endswith(".avif"):
        try:
            return static(f"{converted[:-5]}.png")
        except ValueError:
            pass
    suffix = converted or path or "images/face_1.png"
    return f"{settings.STATIC_URL.rstrip('/')}/{suffix.lstrip('/')}"


def _thumb_static_path(card_path):
    """cards/foo.webp → thumbs/foo.webp; face_N stays itself."""
    path = _placeholder_path(card_path or "")
    if "/cards/" in path:
        return path.replace("/cards/", "/thumbs/", 1)
    return path


def _has_static(rel):
    """True if collectstatic output or STATICFILES_DIRS contains this file."""
    rel = _placeholder_path(rel)
    try:
        if staticfiles_storage.exists(rel):
            return True
    except (ValueError, OSError):
        pass
    return finders.find(rel) is not None


def _resolve_photos(counsellor):
    """Prefer static/images/counsellors/{cards,thumbs}/<slug>.webp.

    Production rows still had images/face_N.avif after the ImageField was
    dropped, which made every profile show the illustrations. The files on
    disk are the source of truth; photo_placeholder is the fallback.
    """
    slug_card = f"images/counsellors/cards/{counsellor.slug}.webp"
    if _has_static(slug_card):
        rel = slug_card
    else:
        rel = counsellor.photo_placeholder or "images/face_1.avif"
    return _static_url(rel), _static_url(_thumb_static_path(rel))


def _working_hours_dict(counsellor):
    hours = {}
    for block in counsellor.hour_blocks.all():
        hours.setdefault(block.weekday, []).append(
            (block.start_time.strftime("%H:%M"), block.end_time.strftime("%H:%M"))
        )
    return hours


def _specialties_dict(counsellor):
    return {link.topic.slug: link.level for link in counsellor.specialty_links.all()}


def _to_dict(counsellor):
    photo, photo_thumb = _resolve_photos(counsellor)
    return {
        "slug": counsellor.slug,
        "name": counsellor.name,
        "credentials": counsellor.credentials,
        "photo": photo,
        "photo_thumb": photo_thumb,
        "is_active": counsellor.is_active,
        "modes": counsellor.modes,
        "languages": counsellor.languages,
        "location": counsellor.location,
        "intro": counsellor.intro,
        "bio": counsellor.bio,
        "modalities": counsellor.modalities,
        "specialties": _specialties_dict(counsellor),
        "fee_note": counsellor.fee_note,
        "working_hours": _working_hours_dict(counsellor),
    }


def _counsellor_queryset(*, bookable_only=False):
    qs = Counsellor.objects.prefetch_related("hour_blocks", "specialty_links__topic")
    if bookable_only:
        qs = qs.filter(is_active=True)
    return qs


def get_counsellors(*, bookable_only=False):
    return [_to_dict(c) for c in _counsellor_queryset(bookable_only=bookable_only)]


def get_counsellor_by_slug(slug, *, bookable_only=False):
    counsellor = _counsellor_queryset(bookable_only=bookable_only).filter(slug=slug).first()
    return _to_dict(counsellor) if counsellor else None
