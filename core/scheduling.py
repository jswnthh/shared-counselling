"""Slot generation: a counsellor's real availability for a given date."""

from datetime import datetime, time, timedelta

from django.utils import timezone

from .calendar_sync import get_busy_intervals
from .models import Booking, CounsellorPackage

SESSION_LENGTH_MINUTES = 50
SLOT_STEP_MINUTES = 60  # slots start on the hour, leaving a 10-minute gap
BOOKING_WINDOW_DAYS = 21  # rolling 3-week booking horizon
MIN_LEAD_TIME = timedelta(hours=2)
SESSION_FEE_PAISE = 150000
SESSION_FEE_DISPLAY = "₹1,500"

def get_session_plans(counsellor):
    """Return only active packages configured for this counsellor in admin."""
    custom_packages = list(
        CounsellorPackage.objects.filter(
            counsellor__slug=counsellor["slug"],
            is_active=True,
        )
    )
    # A counsellor's one-session package is their own baseline. It must never
    # be presented as a discounted package merely because it differs from the
    # legacy global fee.
    single_session = next((package for package in custom_packages if package.sessions == 1), None)
    base_session_paise = (
        single_session.total_price_rupees * 100
        if single_session
        else None
    )
    plans = []
    for package in custom_packages:
        total_paise = package.total_price_rupees * 100
        subtotal = (
            base_session_paise * package.sessions
            if base_session_paise is not None
            else total_paise
        )
        discount = max(subtotal - total_paise, 0)
        plans.append({
            "code": f"package-{package.pk}",
            "label": package.name,
            "sessions": package.sessions,
            "subtotal_paise": subtotal,
            "total_paise": total_paise,
            "discount_percent": round(discount * 100 / subtotal) if subtotal else 0,
        })
    return plans


def quote_booking(counsellor, plan_code, coupon_code=""):
    """Return the authoritative package quote in paise.

    THANKYOU10 is the existing game reward. Keeping its rule in Python means
    the UI can show feedback without becoming the source of truth.
    """
    plan = next((item for item in get_session_plans(counsellor) if item["code"] == plan_code), None)
    if plan is None:
        raise ValueError("Choose a valid session plan.")

    subtotal = plan["subtotal_paise"]
    package_discount = max(subtotal - plan["total_paise"], 0)
    after_package = plan["total_paise"]
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


def session_plan_label(plan_code):
    """Resolve a saved custom-plan code for email/admin display."""
    if plan_code.startswith("package-"):
        try:
            package_id = int(plan_code.removeprefix("package-"))
        except ValueError:
            return plan_code
        return CounsellorPackage.objects.filter(pk=package_id).values_list("name", flat=True).first() or plan_code
    return plan_code


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
