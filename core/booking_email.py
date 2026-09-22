"""Emails sent after a successful booking."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils.formats import date_format

from .data import get_counsellor_by_slug
from .scheduling import SESSION_LENGTH_MINUTES

logger = logging.getLogger(__name__)


def _booking_details(booking):
    counsellor = get_counsellor_by_slug(booking.counsellor_slug)
    counsellor_name = (
        counsellor["name"]
        if counsellor
        else booking.counsellor_slug.replace("-", " ").title()
    )
    mode_label = "In person" if booking.mode == "in-person" else "Online"
    when = date_format(booking.start_at, "l, j F Y · g:i A")
    return counsellor_name, mode_label, when


def _send(subject, body, recipients, *, booking_id, kind):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send booking %s email for booking %s",
            kind,
            booking_id,
        )


def send_booking_emails(booking):
    """Notify the practice and confirm to the client.

    Failures are logged but never raised — the booking itself already
    succeeded, and a mail outage shouldn't roll that back or 500 the user.
    """
    counsellor_name, mode_label, when = _booking_details(booking)
    details = (
        f"  Counsellor: {counsellor_name}\n"
        f"  When:       {when}\n"
        f"  Duration:   {SESSION_LENGTH_MINUTES} minutes\n"
        f"  Mode:       {mode_label}\n"
        f"  Client:     {booking.client_name}\n"
        f"  Email:      {booking.client_email}\n"
        f"  Mobile:     {booking.client_phone or '—'}\n"
    )

    practice_to = getattr(
        settings,
        "BOOKING_NOTIFY_EMAIL",
        "sharedcounselling@gmail.com",
    )
    _send(
        subject=f"New booking · {booking.client_name} with {counsellor_name}",
        body=(
            f"A new session was booked on the site.\n\n"
            f"{details}\n"
            f"— Shared Counselling booking system\n"
        ),
        recipients=[practice_to],
        booking_id=booking.pk,
        kind="practice notification",
    )

    _send(
        subject=f"Booking confirmed with {counsellor_name}",
        body=(
            f"Hi {booking.client_name},\n\n"
            f"Your session is confirmed. Here's a quick summary:\n\n"
            f"{details}\n"
            f"If you need to reschedule, reply to this email or message us on WhatsApp.\n\n"
            f"— Shared Counselling\n"
        ),
        recipients=[booking.client_email],
        booking_id=booking.pk,
        kind="client confirmation",
    )


# Keep the old name as an alias for any call sites / imports.
send_booking_confirmation = send_booking_emails
