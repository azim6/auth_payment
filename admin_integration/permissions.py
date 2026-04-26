from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from .authentication import AdminServiceAuthentication


ADMIN_SERVICE_AUTHENTICATION_CLASSES = [
    AdminServiceAuthentication,
    JWTAuthentication,
    SessionAuthentication,
]


class StaffOrAdminServiceScope(permissions.BasePermission):
    message = "Staff access or a valid admin service credential is required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False):
            return True
        credential = getattr(request, "admin_service_credential", None)
        if credential is None:
            return False
        required_scopes = getattr(view, "required_admin_scopes", [])
        if not required_scopes:
            return True
        return all(scope in credential.scope_set for scope in required_scopes)


def request_actor_user(request):
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False) and getattr(user, "_meta", None) is not None:
        return user
    return None


def request_admin_audit_metadata(request):
    credential = getattr(request, "admin_service_credential", None)
    if credential is None:
        return {}
    return {
        "admin_service_credential_id": str(credential.id),
        "admin_service_credential_name": credential.name,
        "admin_service_scopes": sorted(credential.scope_set),
    }
