"""Emails sent after a successful booking."""

import logging

from django.conf import settings
from django.core.mail import EmailMessage
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


def _practice_inboxes():
    raw = getattr(
        settings,
        "BOOKING_NOTIFY_EMAIL",
        "sharedcounsellingteam@gmail.com",
    )
    return [addr.strip() for addr in str(raw).split(",") if addr.strip()]


def _send_message(message, *, booking_id, kind):
    if not settings.EMAIL_HOST:
        logger.error(
            "Cannot send booking %s email for booking %s: EMAIL_HOST is not set",
            kind,
            booking_id,
        )
        return
    if not settings.EMAIL_HOST_PASSWORD:
        logger.error(
            "Cannot send booking %s email for booking %s: EMAIL_HOST_PASSWORD is not set",
            kind,
            booking_id,
        )
        return
    try:
        message.send(fail_silently=False)
    except Exception:
        logger.exception(
            "Failed to send booking %s email for booking %s",
            kind,
            booking_id,
        )


def send_booking_emails(booking):
    """Email a confirmation to the client (CC the practice) and a staff copy.

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
    practice = _practice_inboxes()
    from_email = settings.DEFAULT_FROM_EMAIL

    confirmation = EmailMessage(
        subject=f"Booking confirmed with {counsellor_name}",
        body=(
            f"Hi {booking.client_name},\n\n"
            f"Your session is confirmed. Here's a quick summary:\n\n"
            f"{details}\n"
            f"If you need to reschedule, reply to this email or message us on WhatsApp.\n\n"
            f"— Shared Counselling\n"
        ),
        from_email=from_email,
        to=[booking.client_email],
        cc=practice,
        reply_to=practice[:1],
    )
    _send_message(
        confirmation,
        booking_id=booking.pk,
        kind="client confirmation",
    )

    if practice:
        staff = EmailMessage(
            subject=f"New booking · {booking.client_name} with {counsellor_name}",
            body=(
                f"A new session was booked on the site.\n\n"
                f"{details}\n"
                f"— Shared Counselling booking system\n"
            ),
            from_email=from_email,
            to=practice,
        )
        _send_message(
            staff,
            booking_id=booking.pk,
            kind="practice notification",
        )


send_booking_confirmation = send_booking_emails
