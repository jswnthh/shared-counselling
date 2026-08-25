# Re-point photo_placeholder at static portraits. Safe to run even if 0006
# already applied: production often still had images/face_N.avif because the
# ImageField drop happened while the CharField was left on the old fallbacks.

from django.db import migrations

PORTRAITS = {
    "divya-shri": "images/counsellors/cards/divya-shri.webp",
    "jayalakshmi-esakki": "images/counsellors/cards/jayalakshmi-esakki.webp",
    "rakshena": "images/counsellors/cards/rakshena.webp",
    "shaffran": "images/counsellors/cards/shaffran.webp",
    "thara": "images/counsellors/cards/thara.webp",
    "yasotha-natarajan": "images/counsellors/cards/yasotha-natarajan.webp",
}


def point_at_static_portraits(apps, schema_editor):
    Counsellor = apps.get_model("core", "Counsellor")
    for row in Counsellor.objects.all():
        path = PORTRAITS.get(row.slug)
        if path and row.photo_placeholder != path:
            row.photo_placeholder = path
            row.save(update_fields=["photo_placeholder"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_counsellor_static_portraits"),
    ]

    operations = [
        migrations.RunPython(point_at_static_portraits, noop),
    ]
