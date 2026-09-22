from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .images import write_static_portrait
from .models import (
    Booking,
    CalendarAccount,
    Counsellor,
    CounsellorSpecialty,
    CounsellorWorkingHours,
    ServiceCategory,
    Topic,
)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("label", "slug", "category", "order")
    list_filter = ("category",)
    search_fields = ("label", "slug")


class CounsellorWorkingHoursInline(admin.TabularInline):
    model = CounsellorWorkingHours
    extra = 1


class CounsellorSpecialtyInline(admin.TabularInline):
    model = CounsellorSpecialty
    extra = 1
    autocomplete_fields = ("topic",)


class CounsellorAdminForm(forms.ModelForm):
    photo_upload = forms.ImageField(
        required=False,
        label="Upload portrait",
        help_text=(
            "JPEG/PNG/WebP. Converted to WebP cards (600px) and thumbs (112px) "
            "under static/images/counsellors/ and linked automatically."
        ),
    )

    class Meta:
        model = Counsellor
        fields = "__all__"


@admin.register(Counsellor)
class CounsellorAdmin(admin.ModelAdmin):
    form = CounsellorAdminForm
    list_display = ("name", "slug", "location", "is_active", "user")
    list_filter = ("is_active",)
    list_editable = ("is_active",)
    search_fields = ("name", "slug", "location")
    inlines = [CounsellorWorkingHoursInline, CounsellorSpecialtyInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "credentials",
                    "location",
                    "is_active",
                    "user",
                )
            },
        ),
        (
            "Portrait",
            {
                "fields": ("photo_placeholder", "photo_upload"),
                "description": (
                    "Prefer Upload portrait. photo_placeholder is the static "
                    "path used by the site (usually set for you after upload)."
                ),
            },
        ),
        (
            "Profile",
            {
                "fields": (
                    "intro",
                    "bio",
                    "languages",
                    "modes",
                    "modalities",
                    "fee_note",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        # slug is the lookup key used everywhere (URLs, ?counsellor=<slug>,
        # Booking.counsellor_slug — a plain string, not a FK) — renaming it
        # after creation would silently orphan booking history and break
        # bookmarked links, so it's only editable at creation time.
        return ("slug",) if obj else ()

    def save_model(self, request, obj, form, change):
        upload = form.cleaned_data.get("photo_upload")
        if upload:
            try:
                obj.photo_placeholder = write_static_portrait(obj.slug, upload)
            except (OSError, ValidationError, ValueError) as exc:
                self.message_user(
                    request,
                    f"Portrait upload failed: {exc}",
                    level=messages.ERROR,
                )
            else:
                self.message_user(
                    request,
                    f"Portrait saved as {obj.photo_placeholder} "
                    "(and matching thumbs/). Commit the new static files "
                    "so they survive the next deploy.",
                    level=messages.SUCCESS,
                )
        super().save_model(request, obj, form, change)

    # --- Per-counsellor self-edit restriction (groundwork for a future
    # counsellor login: a non-superuser tied to a Counsellor via `user` can
    # only ever see/edit their own row here; no inline-level overrides are
    # needed since the inlines are only ever reached through this
    # already-restricted parent object). ---

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        return request.user.is_superuser or obj is None or obj.user_id == request.user.id

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("start_at", "counsellor_slug", "client_name", "client_phone", "mode", "status")
    list_filter = ("status", "mode", "counsellor_slug")
    search_fields = ("client_name", "client_email", "client_phone", "counsellor_slug")
    date_hierarchy = "start_at"
    readonly_fields = ("created_at",)


@admin.register(CalendarAccount)
class CalendarAccountAdmin(admin.ModelAdmin):
    list_display = ("counsellor_slug", "provider", "is_connected", "connected_at")
