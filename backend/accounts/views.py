from django.conf import settings
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import UserSerializer, RegisterSerializer, LoginSerializer
from .cookies import set_auth_cookies, clear_auth_cookies

User = get_user_model()


class CSRFTokenView(APIView):
    """
    Provides a CSRF token to the client and sets the csrftoken cookie.
    """
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        token = get_token(request)
        return Response({'csrfToken': token}, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        response_data = {
            'message': 'Registration successful.',
            'user': UserSerializer(user).data,
        }
        response = Response(response_data, status=status.HTTP_201_CREATED)
        return set_auth_cookies(response, access_token=access_token, refresh_token=refresh)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        response_data = {
            'message': 'Login successful.',
            'user': UserSerializer(user).data,
        }
        response = Response(response_data, status=status.HTTP_200_OK)
        return set_auth_cookies(response, access_token=access_token, refresh_token=refresh)


class LogoutView(APIView):
    """
    Logs out the user, invalidates/blacklists the refresh token server-side,
    and clears authentication cookies.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_cookie_name = getattr(settings, 'AUTH_COOKIE_REFRESH_NAME', 'refresh_token')
        refresh_token = request.COOKIES.get(refresh_cookie_name) or request.data.get('refresh')

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                # Token already blacklisted or expired
                pass

        response = Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        return clear_auth_cookies(response)


class RefreshTokenView(APIView):
    """
    Refreshes the access token using the HttpOnly refresh token cookie.
    Rotates the refresh token and blacklists the previous refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_cookie_name = getattr(settings, 'AUTH_COOKIE_REFRESH_NAME', 'refresh_token')
        raw_refresh = request.COOKIES.get(refresh_cookie_name) or request.data.get('refresh')

        if not raw_refresh:
            return Response(
                {'detail': 'Refresh token not found.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(raw_refresh)
            user_id = refresh.payload.get('user_id')
            user = User.objects.get(id=user_id)
            if not user.is_active:
                return Response({'detail': 'User account is inactive.'}, status=status.HTTP_401_UNAUTHORIZED)

            # Blacklist the old refresh token (Token rotation)
            refresh.blacklist()

            # Generate new tokens
            new_refresh = RefreshToken.for_user(user)
            new_access_token = new_refresh.access_token

            response = Response({'detail': 'Token refreshed successfully.'}, status=status.HTTP_200_OK)
            return set_auth_cookies(response, access_token=new_access_token, refresh_token=new_refresh)
        except (TokenError, User.DoesNotExist) as e:
            response = Response({'detail': f'Invalid or expired refresh token: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)
            return clear_auth_cookies(response)


class CurrentUserView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
