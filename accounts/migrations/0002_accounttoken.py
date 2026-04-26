# Generated for django-auth-platform v2.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("purpose", models.CharField(choices=[("email_verification", "Email verification"), ("password_reset", "Password reset")], max_length=32)),
                ("token_hash", models.CharField(max_length=128, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="account_tokens", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="accounttoken",
            index=models.Index(fields=["user", "purpose"], name="accounts_ac_user_id_95c475_idx"),
        ),
        migrations.AddIndex(
            model_name="accounttoken",
            index=models.Index(fields=["token_hash"], name="accounts_ac_token_h_1d03f0_idx"),
        ),
        migrations.AddIndex(
            model_name="accounttoken",
            index=models.Index(fields=["expires_at"], name="accounts_ac_expires_8118e3_idx"),
        ),
    ]
