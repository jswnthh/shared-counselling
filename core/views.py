from datetime import date, timedelta
import re

from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .booking_email import send_booking_emails
from .calendar_sync import create_calendar_event
from .data import get_counsellor_by_slug, get_counsellors, get_services, get_topic_labels
from .forms import BookingForm
from .models import Booking
from .scheduling import BOOKING_WINDOW_DAYS, SESSION_FEE_DISPLAY, SESSION_LENGTH_MINUTES, get_available_slots

# Digits only for https://wa.me/<number> (shared practice line until
# counsellor-specific chat numbers exist).
PRACTICE_CHAT_NUMBER = "917904221476"


def _bio_paragraphs(bio):
    """Split a packed bio into a few short paragraphs for the profile overlay."""
    text = (bio or "").strip()
    if not text:
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= 1:
        return [text]
    if len(sentences) <= 4:
        return sentences
    # Cap at 4 paragraphs by folding leftover sentences into the last one.
    head, tail = sentences[:3], sentences[3:]
    return head + [" ".join(tail)]


def _short_display_name(name):
    cleaned = re.sub(r"^(Ms\.|Mr\.|Mrs\.|Dr\.)\s+", "", name or "", flags=re.IGNORECASE).strip()
    if not cleaned:
        return name or ""
    return cleaned.split()[0]


def _resolved_counsellor(counsellor, topic_labels):
    specialty_labels = sorted(
        counsellor["specialties"],
        key=lambda topic_slug: counsellor["specialties"][topic_slug],
        reverse=True,
    )
    return {
        **counsellor,
        "specialty_labels": [
            topic_labels.get(topic_slug, topic_slug.replace("-", " ").title())
            for topic_slug in specialty_labels
        ],
        "bio_paragraphs": _bio_paragraphs(counsellor.get("bio", "")),
        "short_name": _short_display_name(counsellor.get("name", "")),
        "chat_number": counsellor.get("chat_number") or PRACTICE_CHAT_NUMBER,
        "whatsapp_enquire_text": (
            "Hello, I would like to enquire about a counselling session with "
            f"{_short_display_name(counsellor.get('name', ''))}."
        ),
    }


def index(request):
    context = {
        "counsellor_previews": [
            {"photo": c["photo"], "name": c["name"], "is_active": c["is_active"]}
            for c in get_counsellors()
        ],
    }
    return render(request, "index.html", context)


def service_detail(request, slug):
    service = get_services().get(slug)
    if service is None:
        raise Http404("Unknown service")

    topic_labels = get_topic_labels()
    topics = [
        {"slug": topic_slug, "label": topic_labels[topic_slug]}
        for topic_slug in service["topics"]
    ]

    context = {
        "service": service,
        "topics": topics,
        "counsellors": get_counsellors(bookable_only=True),
    }
    return render(request, "service_detail.html", context)


def counsellors(request):
    topic_labels = get_topic_labels()
    context = {
        "counsellors": [_resolved_counsellor(c, topic_labels) for c in get_counsellors()],
    }
    return render(request, "counsellors.html", context)


@require_http_methods(["GET", "POST"])
def book(request):
    preselected_slug = request.GET.get("counsellor", "") or request.POST.get(
        "counsellor_slug", ""
    )

    selected_counsellor = None
    if preselected_slug:
        selected_counsellor = get_counsellor_by_slug(
            preselected_slug,
            bookable_only=True,
        )

    # Booking assumes the counsellor was chosen on /counsellors/ (or a
    # match card). Without a valid slug, send people back to pick one.
    if selected_counsellor is None and request.method == "GET":
        return redirect("counsellors")

    if request.method == "POST":
        form = BookingForm(request.POST)

        if form.is_valid():
            start_at = form.cleaned_data["start_at"]
            end_at = start_at + timedelta(
                minutes=SESSION_LENGTH_MINUTES
            )

            try:
                with transaction.atomic():
                    booking = Booking.objects.create(
                        counsellor_slug=form.cleaned_data["counsellor_slug"],
                        client_name=form.cleaned_data["client_name"],
                        client_email=form.cleaned_data["client_email"],
                        client_phone=form.cleaned_data["client_phone"],
                        mode=form.cleaned_data["mode"],
                        start_at=start_at,
                        end_at=end_at,
                    )

            except IntegrityError:
                form.add_error(
                    None,
                    "Sorry — that slot was just booked by someone else. "
                    "Please pick another time.",
                )
                selected_counsellor = get_counsellor_by_slug(
                    form.data.get("counsellor_slug", ""),
                    bookable_only=False,
                ) or selected_counsellor

            else:
                create_calendar_event(booking)
                send_booking_emails(booking)

                return redirect(
                    "book_confirmed",
                    booking_id=booking.pk,
                )
        else:
            # Keep enough counsellor context to re-render the page even when
            # the slug fails bookable_only checks (e.g. just flipped inactive).
            selected_counsellor = get_counsellor_by_slug(
                form.data.get("counsellor_slug", ""),
                bookable_only=False,
            ) or selected_counsellor

    else:
        form = BookingForm(
            initial={"counsellor_slug": selected_counsellor["slug"]}
        )

    if selected_counsellor is None:
        return redirect("counsellors")

    counsellor_list = [selected_counsellor]

    context = {
        "form": form,
        "selected_counsellor": {
            **selected_counsellor,
            "short_name": _short_display_name(selected_counsellor["name"]),
            "photo": selected_counsellor["photo_thumb"],
        },
        "counsellors_json": [
            {
                "slug": c["slug"],
                "name": c["name"],
                "credentials": c["credentials"],
                "photo": c["photo_thumb"],
                "modes": c["modes"],
                "working_hours": c["working_hours"],
            }
            for c in counsellor_list
        ],
        "preselected_slug": selected_counsellor["slug"],
        "booking_window_days": BOOKING_WINDOW_DAYS,
        "booking_horizon": (
            timezone.now()
            + timedelta(days=BOOKING_WINDOW_DAYS)
        ).isoformat(),
        "session_fee_display": SESSION_FEE_DISPLAY,
        "session_length_minutes": SESSION_LENGTH_MINUTES,
    }

    return render(request, "booking.html", context)

@require_GET
def booking_availability(request):
    counsellor = get_counsellor_by_slug(request.GET.get("counsellor", ""), bookable_only=True)
    if counsellor is None:
        return JsonResponse({"error": "unknown counsellor"}, status=404)
    try:
        requested_date = date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return JsonResponse({"error": "invalid date"}, status=400)

    slots = get_available_slots(counsellor, requested_date)
    return JsonResponse({
        "date": requested_date.isoformat(),
        "counsellor": counsellor["slug"],
        "modes": counsellor["modes"],
        "slots": [s.isoformat() for s in slots],
    })


@require_GET
def book_confirmed(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    counsellor = get_counsellor_by_slug(booking.counsellor_slug)
    context = {
        "booking": booking,
        "counsellor_name": counsellor["name"] if counsellor else booking.counsellor_slug.replace("-", " ").title(),
    }
    return render(request, "booking_confirmed.html", context)


@require_GET
def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /book/availability/\n"
        f"\nSitemap: {sitemap_url}\n"
    )
    return HttpResponse(body, content_type="text/plain")
