import phonenumbers
from django.core.management.base import BaseCommand
from django.db import connection

from core.models import Booking


class Command(BaseCommand):
    help = (
        "List booking phone numbers that are blank, invalid, or not stored in "
        "E.164 format. Intended for reviewing legacy records after migration."
    )

    def handle(self, *args, **options):
        meta = Booking._meta
        table = connection.ops.quote_name(meta.db_table)
        id_column = connection.ops.quote_name(meta.pk.column)
        phone_column = connection.ops.quote_name(meta.get_field("client_phone").column)

        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {id_column}, {phone_column} FROM {table}")
            rows = cursor.fetchall()

        review_count = 0
        for booking_id, raw_number in rows:
            raw_number = (raw_number or "").strip()
            if not raw_number:
                continue  # Historical blanks are intentionally allowed.
            try:
                parsed = phonenumbers.parse(raw_number, "IN")
                normalized = phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
                valid = phonenumbers.is_valid_number(parsed)
            except phonenumbers.NumberParseException:
                valid = False
                normalized = None

            if not valid:
                self.stdout.write(f"Booking {booking_id}: invalid ({raw_number!r})")
                review_count += 1
            elif raw_number != normalized:
                self.stdout.write(
                    f"Booking {booking_id}: non-E.164 {raw_number!r} -> {normalized}"
                )
                review_count += 1

        if review_count:
            self.stdout.write(self.style.WARNING(f"{review_count} record(s) need review."))
        else:
            self.stdout.write(self.style.SUCCESS("No non-empty legacy phone numbers need review."))
