from rest_framework import authentication, exceptions

from .services import verify_admin_request


class AdminServicePrincipal:
    is_authenticated = True
    is_staff = False

    def __init__(self, credential):
        self.credential = credential
        self.id = f"admin-service:{credential.id}"
        self.username = credential.name

    def __str__(self):
        return self.username


class AdminServiceAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if not request.headers.get("X-Admin-Service-Key"):
            return None
        result = verify_admin_request(request)
        if not result.ok:
            raise exceptions.AuthenticationFailed(result.error or "invalid admin service request")
        request.admin_service_credential = result.credential
        return (AdminServicePrincipal(result.credential), result.credential)
