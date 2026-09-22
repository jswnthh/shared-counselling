# Generated manually for client_phone on Booking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_counsellor_static_portrait_paths"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="client_phone",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
