from datetime import timedelta
from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token=None):
    """
    Set HttpOnly secure cookies for access and refresh tokens.
    """
    secure = getattr(settings, 'AUTH_COOKIE_SECURE', not settings.DEBUG)
    samesite = getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax')
    access_cookie_name = getattr(settings, 'AUTH_COOKIE_ACCESS_NAME', 'access_token')
    refresh_cookie_name = getattr(settings, 'AUTH_COOKIE_REFRESH_NAME', 'refresh_token')

    # Access token cookie (typically 15-30 minutes)
    access_max_age = int(getattr(settings, 'AUTH_COOKIE_ACCESS_MAX_AGE', 1800))
    response.set_cookie(
        key=access_cookie_name,
        value=str(access_token),
        max_age=access_max_age,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path='/',
    )

    # Refresh token cookie (typically 7 days)
    if refresh_token:
        refresh_max_age = int(getattr(settings, 'AUTH_COOKIE_REFRESH_MAX_AGE', 7 * 24 * 3600))
        response.set_cookie(
            key=refresh_cookie_name,
            value=str(refresh_token),
            max_age=refresh_max_age,
            httponly=True,
            secure=secure,
            samesite=samesite,
            path='/',
        )

    return response


def clear_auth_cookies(response):
    """
    Clear access and refresh token cookies from client.
    """
    access_cookie_name = getattr(settings, 'AUTH_COOKIE_ACCESS_NAME', 'access_token')
    refresh_cookie_name = getattr(settings, 'AUTH_COOKIE_REFRESH_NAME', 'refresh_token')
    samesite = getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax')

    response.delete_cookie(key=access_cookie_name, path='/', samesite=samesite)
    response.delete_cookie(key=refresh_cookie_name, path='/', samesite=samesite)
    return response
