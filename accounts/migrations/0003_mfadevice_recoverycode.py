import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0002_accounttoken"),
    ]

    operations = [
        migrations.CreateModel(
            name="MfaDevice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("type", models.CharField(choices=[("totp", "Authenticator app TOTP")], default="totp", max_length=16)),
                ("name", models.CharField(default="Authenticator app", max_length=120)),
                ("secret", models.TextField(help_text="Signed TOTP secret. Do not expose through APIs.")),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="mfa_device", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="RecoveryCode",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code_hash", models.CharField(max_length=256)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recovery_codes", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="mfadevice",
            index=models.Index(fields=["user", "confirmed_at"], name="accounts_mf_user_id_d0ee5f_idx"),
        ),
        migrations.AddIndex(
            model_name="recoverycode",
            index=models.Index(fields=["user", "used_at"], name="accounts_re_user_id_9b1e2f_idx"),
        ),
    ]
