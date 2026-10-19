from datetime import datetime

from django import forms
from django.utils import timezone
from phonenumber_field.formfields import PhoneNumberField

from .data import get_counsellor_by_slug, get_counsellors
from .models import Booking
from .scheduling import get_available_slots
from .scheduling import SESSION_PLANS, quote_booking


class BookingForm(forms.Form):
    counsellor_slug = forms.ChoiceField(choices=[])
    date = forms.DateField()
    time = forms.TimeField()
    mode = forms.ChoiceField(choices=Booking.Mode.choices)
    session_plan = forms.ChoiceField(
        choices=[(key, value["label"]) for key, value in SESSION_PLANS.items()],
        required=False,
        initial="single",
    )
    coupon_code = forms.CharField(max_length=40, required=False)
    client_name = forms.CharField(max_length=120)
    client_email = forms.EmailField()
    client_phone = PhoneNumberField(
        region="IN",
        widget=forms.TelInput(
            attrs={
                "class": "field-input",
                "id": "clientPhone",
                "autocomplete": "tel",
                "inputmode": "tel",
                "aria-describedby": "clientPhoneHelp",
                "required": True,
            }
        ),
        error_messages={"invalid": "Enter a valid phone number, including its country code if outside India."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["counsellor_slug"].choices = [
            (c["slug"], c["name"]) for c in get_counsellors(bookable_only=True)
        ]

    def clean(self):
        cleaned = super().clean()
        counsellor = get_counsellor_by_slug(cleaned.get("counsellor_slug"), bookable_only=True)
        if counsellor is None:
            raise forms.ValidationError("Unknown counsellor or counsellor is not currently accepting bookings.")

        mode = cleaned.get("mode")
        if mode and mode not in counsellor["modes"]:
            self.add_error("mode", "This counsellor doesn't offer that mode.")

        plan_code = cleaned.get("session_plan") or "single"
        cleaned["session_plan"] = plan_code
        quote = quote_booking(plan_code, cleaned.get("coupon_code", ""))
        if quote["coupon_error"]:
            self.add_error("coupon_code", quote["coupon_error"])
        else:
            cleaned["quote"] = quote

        date_, time_ = cleaned.get("date"), cleaned.get("time")
        if date_ and time_:
            start_at = timezone.make_aware(datetime.combine(date_, time_))
            if start_at not in get_available_slots(counsellor, date_):
                raise forms.ValidationError(
                    "That slot is no longer available. Please choose another time."
                )
            cleaned["start_at"] = start_at
        return cleaned
