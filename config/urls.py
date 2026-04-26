from django.apps import apps
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from accounts.views import OAuthDiscoveryView

from config.app_registry import APP_URL_PREFIXES

urlpatterns = [
    path("admin/", admin.site.urls),
    path(".well-known/openid-configuration", OAuthDiscoveryView.as_view(), name="openid-configuration"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

for app_label, prefix in APP_URL_PREFIXES.items():
    if apps.is_installed(app_label):
        urlpatterns.append(path(prefix, include(f"{app_label}.urls")))
