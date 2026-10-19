"""Slot generation: a counsellor's real availability for a given date."""

from datetime import datetime, time, timedelta

from django.utils import timezone

from .calendar_sync import get_busy_intervals
from .models import Booking

SESSION_LENGTH_MINUTES = 50
SLOT_STEP_MINUTES = 60  # slots start on the hour, leaving a 10-minute gap
BOOKING_WINDOW_DAYS = 21  # rolling 3-week booking horizon
MIN_LEAD_TIME = timedelta(hours=2)
SESSION_FEE_PAISE = 150000
SESSION_FEE_DISPLAY = "₹1,500"

# Prices are deliberately defined here, not in the browser.  The booking form
# and the small pricing endpoint both use these values, so a submitted booking
# can never trust a client-side total.
SESSION_PLANS = {
    "single": {"label": "Single session", "sessions": 1, "discount_percent": 0},
    "three": {"label": "3-session package", "sessions": 3, "discount_percent": 10},
    "six": {"label": "6-session package", "sessions": 6, "discount_percent": 15},
}


def quote_booking(plan_code, coupon_code=""):
    """Return the authoritative package quote in paise.

    THANKYOU10 is the existing game reward. Keeping its rule in Python means
    the UI can show feedback without becoming the source of truth.
    """
    plan = SESSION_PLANS.get(plan_code)
    if plan is None:
        raise ValueError("Choose a valid session plan.")

    subtotal = SESSION_FEE_PAISE * plan["sessions"]
    package_discount = subtotal * plan["discount_percent"] // 100
    after_package = subtotal - package_discount
    normalized_code = (coupon_code or "").strip().upper()
    coupon_discount = 0
    coupon_error = ""
    if normalized_code:
        if normalized_code == "THANKYOU10":
            coupon_discount = after_package * 10 // 100
        else:
            coupon_error = "That coupon code isn’t valid."

    return {
        "plan": plan,
        "plan_code": plan_code,
        "subtotal_paise": subtotal,
        "package_discount_paise": package_discount,
        "coupon_code": normalized_code if not coupon_error else "",
        "coupon_discount_paise": coupon_discount,
        "total_paise": after_package - coupon_discount,
        "coupon_error": coupon_error,
    }


def get_available_slots(counsellor, date_):
    """Return a sorted list of tz-aware datetimes counsellor is free to start
    a session at on date_, honouring working hours, existing bookings, and
    (once real) external calendar busy time."""
    windows = counsellor.get("working_hours", {}).get(date_.weekday(), [])
    if not windows:
        return []

    now = timezone.now()
    horizon = now + timedelta(days=BOOKING_WINDOW_DAYS)

    candidates = []
    for start_str, end_str in windows:
        window_start = timezone.make_aware(datetime.combine(date_, time.fromisoformat(start_str)))
        window_end = timezone.make_aware(datetime.combine(date_, time.fromisoformat(end_str)))
        cursor = window_start
        while cursor + timedelta(minutes=SESSION_LENGTH_MINUTES) <= window_end:
            if now + MIN_LEAD_TIME <= cursor <= horizon:
                candidates.append(cursor)
            cursor += timedelta(minutes=SLOT_STEP_MINUTES)

    if not candidates:
        return []

    day_start = timezone.make_aware(datetime.combine(date_, time.min))
    day_end = day_start + timedelta(days=1)
    booked = list(
        Booking.objects.filter(
            counsellor_slug=counsellor["slug"],
            status=Booking.Status.CONFIRMED,
            start_at__lt=day_end,
            end_at__gt=day_start,
        ).values_list("start_at", "end_at")
    )
    busy = get_busy_intervals(counsellor["slug"], date_)  # stub -> [] today

    blocked = booked + busy

    def is_free(slot_start):
        slot_end = slot_start + timedelta(minutes=SESSION_LENGTH_MINUTES)
        return not any(slot_start < b_end and b_start < slot_end for b_start, b_end in blocked)

    return sorted(c for c in candidates if is_free(c))
