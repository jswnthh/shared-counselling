"""Regression coverage for provider configuration and saved-booking emails."""
import os
import runpy
from datetime import datetime, timedelta, timezone as datetime_timezone
from pathlib import Path
from unittest.mock import patch

from django.core import mail
from django.core.mail import get_connection
from django.test import SimpleTestCase, TestCase, override_settings

from .booking_email import send_booking_emails
from .models import Booking, Counsellor, CounsellorPackage


class EmailConfigurationTests(SimpleTestCase):
    def load_settings(self, **environment):
        with patch.dict(os.environ, {"SECRET_KEY": "test-only", **environment}, clear=True):
            with patch.object(Path, "is_file", return_value=False):
                settings_path = Path(__file__).resolve().parent.parent / "ProjectCounsellingSite/settings.py"
                return runpy.run_path(str(settings_path))

    def test_provider_keys_reach_the_selected_backend(self):
        for provider in ("resend", "brevo", "sendgrid"):
            with self.subTest(provider=provider):
                key = f"{provider.upper()}_API_KEY"
                configured = self.load_settings(**{key: "test-provider-key"})
                backend = f"anymail.backends.{provider}.EmailBackend"
                self.assertEqual(configured["EMAIL_BACKEND"], backend)
                with override_settings(EMAIL_BACKEND=backend, ANYMAIL=configured["ANYMAIL"]):
                    connection = get_connection()
                    self.assertEqual(connection.api_key, "test-provider-key")
                    connection.close()

    def test_explicit_console_backend_overrides_present_api_key(self):
        backend = "django.core.mail.backends.console.EmailBackend"
        configured = self.load_settings(EMAIL_BACKEND=backend, RESEND_API_KEY="test-key")
        self.assertEqual(configured["EMAIL_BACKEND"], backend)

    def test_provider_priority_and_smtp_fallback(self):
        configured = self.load_settings(
            RESEND_API_KEY="resend-test", BREVO_API_KEY="brevo-test", SENDGRID_API_KEY="sg-test",
        )
        self.assertEqual(configured["EMAIL_BACKEND"], "anymail.backends.resend.EmailBackend")
        self.assertEqual(self.load_settings()["EMAIL_BACKEND"], "django.core.mail.backends.smtp.EmailBackend")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    BOOKING_NOTIFY_EMAIL="practice@example.com",
    TIME_ZONE="Asia/Kolkata",
)
class BookingEmailTests(TestCase):
    def setUp(self):
        start = datetime(2026, 10, 5, 9, 0, tzinfo=datetime_timezone.utc)
        self.booking = Booking.objects.create(
            counsellor_slug="former-counsellor", client_name="Test Client",
            client_email="client@example.com", mode="online",
            start_at=start, end_at=start + timedelta(minutes=50),
        )
        self.booking.refresh_from_db()

    def test_saved_utc_booking_is_shown_in_practice_timezone(self):
        send_booking_emails(self.booking)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("2:30 PM", mail.outbox[0].body)
        self.assertIn("Asia/Kolkata", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].reply_to, ["practice@example.com"])

    def test_delivery_failure_is_logged_and_booking_survives(self):
        with patch("core.booking_email.get_connection", side_effect=OSError("unavailable")):
            with self.assertLogs("core.booking_email", level="ERROR"):
                send_booking_emails(self.booking)
        self.assertTrue(Booking.objects.filter(pk=self.booking.pk).exists())

    def test_package_and_coupon_are_in_client_and_staff_emails(self):
        counsellor = Counsellor.objects.create(slug="email-test", name="Test Counsellor")
        package = CounsellorPackage.objects.create(
            counsellor=counsellor, name="3-session package", sessions=3,
            total_price_rupees=4050,
        )
        self.booking.session_plan = f"package-{package.pk}"
        self.booking.coupon_code = "THANKYOU10"
        self.booking.save()
        self.booking.refresh_from_db()

        send_booking_emails(self.booking)

        self.assertEqual(len(mail.outbox), 2)
        for message in mail.outbox:
            self.assertIn("Package:    3-session package", message.body)
            self.assertIn("Coupon:     THANKYOU10", message.body)

    def test_emails_explicitly_show_when_no_coupon_was_applied(self):
        send_booking_emails(self.booking)
        self.assertEqual(len(mail.outbox), 2)
        for message in mail.outbox:
            self.assertIn("Coupon:     None applied", message.body)
