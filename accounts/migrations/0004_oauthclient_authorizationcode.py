# Generated for django-auth-platform v4.

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_mfadevice_recoverycode"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OAuthClient",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("client_id", models.CharField(max_length=80, unique=True)),
                ("client_secret_hash", models.CharField(blank=True, max_length=256)),
                ("is_confidential", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("redirect_uris", models.TextField(help_text="One redirect URI per line. Exact match required.")),
                ("allowed_scopes", models.CharField(default="openid profile email", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_oauth_clients", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AuthorizationCode",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code_hash", models.CharField(max_length=128, unique=True)),
                ("redirect_uri", models.CharField(max_length=500)),
                ("scope", models.CharField(default="openid profile email", max_length=255)),
                ("state", models.CharField(blank=True, max_length=255)),
                ("nonce", models.CharField(blank=True, max_length=255)),
                ("code_challenge", models.CharField(blank=True, max_length=255)),
                ("code_challenge_method", models.CharField(blank=True, max_length=16)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="authorization_codes", to="accounts.oauthclient")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="authorization_codes", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(model_name="oauthclient", index=models.Index(fields=["client_id"], name="accounts_oa_client__797c6c_idx")),
        migrations.AddIndex(model_name="oauthclient", index=models.Index(fields=["is_active"], name="accounts_oa_is_acti_6bb5e7_idx")),
        migrations.AddIndex(model_name="authorizationcode", index=models.Index(fields=["client", "user"], name="accounts_au_client__d71efe_idx")),
        migrations.AddIndex(model_name="authorizationcode", index=models.Index(fields=["code_hash"], name="accounts_au_code_ha_5833f8_idx")),
        migrations.AddIndex(model_name="authorizationcode", index=models.Index(fields=["expires_at"], name="accounts_au_expires_f4af54_idx")),
    ]
