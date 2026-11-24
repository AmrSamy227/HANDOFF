from django.conf import settings
from rest_framework import exceptions, permissions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that first looks for tokens in the Authorization header.
    If not found, it checks the configured HttpOnly cookie (AUTH_COOKIE_ACCESS_NAME).

    SECURITY:
    When authenticating via HttpOnly cookies for unsafe HTTP methods (POST, PUT, PATCH, DELETE),
    CSRF validation is strictly enforced to protect against Cross-Site Request Forgery attacks.
    Bearer tokens sent via headers are not subject to CSRF checks because browsers do not attach
    custom headers automatically across origins without CORS preflight approval.
    """

    def enforce_csrf(self, request):
        def dummy_get_response(req):
            return None

        check = CSRFCheck(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')

    def authenticate(self, request):
        # 1. Try standard Authorization header (Bearer <token>)
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

        # 2. Fallback to HttpOnly cookie
        cookie_name = getattr(settings, 'AUTH_COOKIE_ACCESS_NAME', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        # Enforce CSRF protection for cookie-authenticated state-changing requests
        if request.method not in permissions.SAFE_METHODS:
            self.enforce_csrf(request)

        return user, validated_token
