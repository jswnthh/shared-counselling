from datetime import datetime
import re

from django import forms
from django.utils import timezone

from .data import get_counsellor_by_slug, get_counsellors
from .models import Booking
from .scheduling import get_available_slots


class BookingForm(forms.Form):
    counsellor_slug = forms.ChoiceField(choices=[])
    date = forms.DateField()
    time = forms.TimeField()
    mode = forms.ChoiceField(choices=Booking.Mode.choices)
    client_name = forms.CharField(max_length=120)
    client_email = forms.EmailField()
    client_phone = forms.CharField(max_length=20)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["counsellor_slug"].choices = [
            (c["slug"], c["name"]) for c in get_counsellors(bookable_only=True)
        ]

    def clean_client_phone(self):
        phone = (self.cleaned_data.get("client_phone") or "").strip()
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 10:
            raise forms.ValidationError("Enter a valid mobile number.")
        return phone

    def clean(self):
        cleaned = super().clean()
        counsellor = get_counsellor_by_slug(cleaned.get("counsellor_slug"), bookable_only=True)
        if counsellor is None:
            raise forms.ValidationError("Unknown counsellor or counsellor is not currently accepting bookings.")

        mode = cleaned.get("mode")
        if mode and mode not in counsellor["modes"]:
            self.add_error("mode", "This counsellor doesn't offer that mode.")

        date_, time_ = cleaned.get("date"), cleaned.get("time")
        if date_ and time_:
            start_at = timezone.make_aware(datetime.combine(date_, time_))
            if start_at not in get_available_slots(counsellor, date_):
                raise forms.ValidationError(
                    "That slot is no longer available. Please choose another time."
                )
            cleaned["start_at"] = start_at
        return cleaned
