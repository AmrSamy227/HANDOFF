import uuid
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.csrf_url = reverse('accounts:auth-csrf')
        self.register_url = reverse('accounts:auth-register')
        self.login_url = reverse('accounts:auth-login')
        self.logout_url = reverse('accounts:auth-logout')
        self.refresh_url = reverse('accounts:auth-refresh')
        self.me_url = reverse('accounts:auth-me')

        self.user_data = {
            'email': 'developer@handoff.design',
            'password': 'SecurePassword123!',
            'first_name': 'Amr',
            'last_name': 'Sami',
        }

    # ---------------------------------------------------------
    # Basic Registration, Login, & User Lifecycle
    # ---------------------------------------------------------
    def test_user_registration_success(self):
        """User registration creates user, returns 201 and sets HttpOnly cookies."""
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['email'], self.user_data['email'])
        self.assertEqual(response.data['user']['first_name'], self.user_data['first_name'])
        self.assertNotIn('password', response.data['user'])

        # Verify HttpOnly cookies
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])
        self.assertTrue(response.cookies['refresh_token']['httponly'])

        # Verify DB record & UUID
        user = User.objects.get(email=self.user_data['email'])
        self.assertIsInstance(user.id, uuid.UUID)

    def test_duplicate_email_registration_rejected(self):
        """Registering with an already used email returns 400 Bad Request."""
        self.client.post(self.register_url, self.user_data, format='json')
        duplicate_response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', duplicate_response.data)

    def test_password_is_hashed_correctly(self):
        """Passwords must be hashed using Django's password hashing and not stored in plaintext."""
        self.client.post(self.register_url, self.user_data, format='json')
        user = User.objects.get(email=self.user_data['email'])
        self.assertNotEqual(user.password, self.user_data['password'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertTrue(user.password.startswith('pbkdf2_') or '$' in user.password)

    def test_login_success(self):
        """Valid login returns 200, user data, and HttpOnly cookies."""
        User.objects.create_user(**self.user_data)
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password'],
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], self.user_data['email'])
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])

    def test_invalid_credentials_rejected(self):
        """Invalid credentials return 400 with validation error."""
        User.objects.create_user(**self.user_data)
        bad_login_data = {
            'email': self.user_data['email'],
            'password': 'WrongPassword999!',
        }
        response = self.client.post(self.login_url, bad_login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_user_cannot_access_me(self):
        """Unauthenticated requests to protected endpoints return 401 Unauthorized."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_access_me_via_bearer_header(self):
        """Users with Bearer token header can access protected endpoints."""
        user = User.objects.create_user(**self.user_data)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)

    def test_authenticated_user_can_access_me_via_cookie(self):
        """Users with a valid HttpOnly access_token cookie can access GET /api/v1/auth/me/ without CSRF."""
        user = User.objects.create_user(**self.user_data)
        refresh = RefreshToken.for_user(user)
        self.client.cookies['access_token'] = str(refresh.access_token)

        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)

    # ---------------------------------------------------------
    # CSRF Security Tests
    # ---------------------------------------------------------
    def test_csrf_token_endpoint(self):
        """GET /api/v1/auth/csrf/ sets csrftoken cookie and returns masked token in response body."""
        response = self.client.get(self.csrf_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('csrfToken', response.data)
        self.assertIn('csrftoken', response.cookies)
        self.assertTrue(len(response.data['csrfToken']) > 20)
        self.assertTrue(len(response.cookies['csrftoken'].value) > 20)

    def test_cookie_authenticated_unsafe_request_fails_without_csrf(self):
        """
        SECURITY AUDIT CHECK:
        State-changing request (PATCH) authenticated via HttpOnly cookie MUST fail (403) when CSRF token is missing.
        """
        csrf_client = APIClient(enforce_csrf_checks=True)
        user = User.objects.create_user(**self.user_data)
        refresh = RefreshToken.for_user(user)
        csrf_client.cookies['access_token'] = str(refresh.access_token)

        # Attempt PATCH without X-CSRFToken header or matching cookie
        response = csrf_client.patch(self.me_url, {'first_name': 'HackedName'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('CSRF Failed', str(response.data))

    def test_cookie_authenticated_unsafe_request_succeeds_with_valid_csrf(self):
        """
        SECURITY AUDIT CHECK:
        State-changing request (PATCH) authenticated via cookie succeeds when matching CSRF token is provided.
        """
        csrf_client = APIClient(enforce_csrf_checks=True)
        user = User.objects.create_user(**self.user_data)
        refresh = RefreshToken.for_user(user)
        csrf_client.cookies['access_token'] = str(refresh.access_token)

        # 1. Fetch CSRF token to establish csrftoken cookie
        csrf_res = csrf_client.get(self.csrf_url)
        csrf_token = csrf_res.data['csrfToken']

        # 2. Send PATCH with valid X-CSRFToken header
        response = csrf_client.patch(
            self.me_url,
            {'first_name': 'AmrUpdated'},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'AmrUpdated')

    def test_bearer_authenticated_unsafe_request_does_not_require_csrf(self):
        """
        SECURITY AUDIT CHECK:
        API clients using Authorization: Bearer <token> can make unsafe requests without CSRF token.
        """
        csrf_client = APIClient(enforce_csrf_checks=True)
        user = User.objects.create_user(**self.user_data)
        refresh = RefreshToken.for_user(user)
        csrf_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = csrf_client.patch(self.me_url, {'first_name': 'AmrBearer'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'AmrBearer')

    # ---------------------------------------------------------
    # JWT Lifecycle: Rotation, Blacklisting, & Logout
    # ---------------------------------------------------------
    def test_refresh_token_rotation_and_old_token_blacklisting(self):
        """
        SECURITY AUDIT CHECK:
        1. Calling refresh generates new access and new refresh tokens.
        2. The previous refresh token is blacklisted.
        3. Attempting to reuse the previous refresh token is rejected with 401.
        """
        user = User.objects.create_user(**self.user_data)
        old_refresh = RefreshToken.for_user(user)
        old_refresh_str = str(old_refresh)

        self.client.cookies['refresh_token'] = old_refresh_str
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # New refresh token cookie must be set and different from old
        new_refresh_str = response.cookies['refresh_token'].value
        self.assertNotEqual(old_refresh_str, new_refresh_str)

        # Attempt to reuse the old refresh token
        self.client.cookies['refresh_token'] = old_refresh_str
        reuse_response = self.client.post(self.refresh_url)
        self.assertEqual(reuse_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('blacklisted', str(reuse_response.data).lower())

    def test_logout_blacklists_refresh_token_server_side(self):
        """
        SECURITY AUDIT CHECK:
        Logout must blacklist the refresh token on the server so it cannot be used again.
        """
        user = User.objects.create_user(**self.user_data)
        refresh = RefreshToken.for_user(user)
        refresh_str = str(refresh)

        # Logout
        self.client.cookies['refresh_token'] = refresh_str
        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # Attempt to refresh using the logged-out refresh token
        self.client.cookies['refresh_token'] = refresh_str
        refresh_response = self.client.post(self.refresh_url)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('blacklisted', str(refresh_response.data).lower())
