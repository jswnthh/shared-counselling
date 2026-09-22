from django.conf import settings
from django.db import models
from django.db.models import Q


class ServiceCategory(models.Model):
    """One of the 4 service pages — also the grouping used for the topic
    checklist on each service page (e.g. "Individual therapy" topics)."""

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    eyebrow = models.CharField(max_length=80)
    intro = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class Topic(models.Model):
    """A single specialty checkbox (e.g. "Anxiety") under a ServiceCategory."""

    slug = models.SlugField(max_length=64, unique=True)
    label = models.CharField(max_length=120)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="topics")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category__order", "order"]

    def __str__(self):
        return self.label


class Counsellor(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    credentials = models.CharField(max_length=160)
    # Path under static/ (no leading slash), e.g.
    # images/counsellors/cards/thara.webp — thumbs are the same filename
    # under images/counsellors/thumbs/. Hero-style face_N.avif still works.
    photo_placeholder = models.CharField(
        max_length=200,
        default="images/face_1.avif",
        blank=True,
        help_text=(
            "Static path, e.g. images/counsellors/cards/thara.webp. "
            "Usually set automatically when you use Upload portrait in admin."
        ),
    )
    location = models.CharField(max_length=120)
    # Whether this counsellor is currently practising/accepting new clients —
    # shown as a green/red status dot on the homepage. Defaults to True so
    # every seeded profile starts "active"; flip it per-counsellor in admin.
    is_active = models.BooleanField(default=True)
    # blank=True on all 3 JSONFields below: Django's admin form validation
    # treats an empty list "[]" as a missing required value (it's in
    # Field.empty_values), so without blank=True the admin form would refuse
    # to ever save an empty list even though it's a legitimate value.
    languages = models.JSONField(default=list, blank=True)
    # Subset of ["online", "in-person"] — kept as a list (not two booleans)
    # since every consumer (forms/scheduling/templates/JS) already expects
    # counsellor["modes"] / counsellor.modes as a list.
    modes = models.JSONField(default=list, blank=True)
    intro = models.TextField()
    bio = models.TextField()
    modalities = models.JSONField(default=list, blank=True)
    # Reference-only free text from intake — not read by scheduling.py or the
    # booking page, which still show one flat SESSION_FEE_DISPLAY for everyone.
    fee_note = models.CharField(max_length=200, blank=True, default="")
    # Nullable groundwork for a future counsellor self-edit login — no real
    # accounts are created yet, but Django admin already restricts a
    # non-superuser tied to a Counsellor to only their own row (see
    # CounsellorAdmin in admin.py).
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="counsellor_profile",
    )

    def __str__(self):
        return self.name


class CounsellorWorkingHours(models.Model):
    """One working window for a counsellor on a given weekday. Multiple rows
    per counsellor/weekday are allowed (split shifts, e.g. 11-1 and 5-10)."""

    counsellor = models.ForeignKey(Counsellor, on_delete=models.CASCADE, related_name="hour_blocks")
    weekday = models.SmallIntegerField()  # 0=Monday .. 6=Sunday
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["counsellor", "weekday", "start_time"],
                name="unique_counsellor_weekday_start",
            ),
        ]

    def __str__(self):
        return f"{self.counsellor.slug} · working {self.weekday} {self.start_time}-{self.end_time}"


class CounsellorSpecialty(models.Model):
    """A counsellor's primary/secondary specialty pick for one Topic — the
    data behind the future primary/secondary checkbox grid."""

    class Level(models.IntegerChoices):
        PRIMARY = 2, "Primary"
        SECONDARY = 1, "Secondary"

    counsellor = models.ForeignKey(Counsellor, on_delete=models.CASCADE, related_name="specialty_links")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    level = models.SmallIntegerField(choices=Level.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["counsellor", "topic"], name="unique_counsellor_topic"),
        ]

    def __str__(self):
        return f"{self.counsellor.slug} · {self.topic.slug}"


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    class Mode(models.TextChoices):
        ONLINE = "online", "Online"
        IN_PERSON = "in-person", "In person"

    # References core.data.COUNSELLORS[i]["slug"] — a plain string, not a
    # ForeignKey, since counsellors live in core/data.py, not the database.
    counsellor_slug = models.CharField(max_length=64, db_index=True)
    client_name = models.CharField(max_length=120)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=20, blank=True, default="")
    mode = models.CharField(max_length=16, choices=Mode.choices)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CONFIRMED)
    calendar_event_id = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # The real double-booking guard: SQLite has no useful row-level
            # locking, so two concurrent requests for the same slot both pass
            # the availability pre-check and race to INSERT — only one can
            # win once this constraint is in place, the other raises
            # IntegrityError and is turned into a "slot just taken" error.
            models.UniqueConstraint(
                fields=["counsellor_slug", "start_at"],
                condition=Q(status="confirmed"),
                name="unique_confirmed_slot_per_counsellor",
            ),
        ]
        ordering = ["-start_at"]

    def __str__(self):
        return f"{self.counsellor_slug} @ {self.start_at:%Y-%m-%d %H:%M}"


class CalendarAccount(models.Model):
    """Per-counsellor external calendar connection.

    Nothing populates or authenticates these rows yet — there is no live
    Google/Outlook OAuth flow. This model exists so core/calendar_sync.py has
    something real to query; is_connected stays False until that flow exists.
    """

    class Provider(models.TextChoices):
        NONE = "none", "Not connected"
        GOOGLE = "google", "Google Calendar"
        OUTLOOK = "outlook", "Outlook"

    counsellor_slug = models.CharField(max_length=64, unique=True)
    provider = models.CharField(max_length=16, choices=Provider.choices, default=Provider.NONE)
    is_connected = models.BooleanField(default=False)
    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    external_calendar_id = models.CharField(max_length=255, blank=True, default="")
    connected_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.counsellor_slug} ({self.get_provider_display()})"
