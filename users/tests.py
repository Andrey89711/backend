"""
Автотесты для приложения users.
Запуск: python manage.py test users -v 2
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from users.models import UserProfile, EmailVerificationToken


class AuthAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.me_url = '/api/auth/me/'

    # -- Регистрация --

    def test_register_creates_user_inactive(self):
        resp = self.client.post(self.register_url, {
            'username': 'newuser', 'email': 'new@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='newuser')
        self.assertFalse(user.is_active)

    def test_register_creates_email_token(self):
        self.client.post(self.register_url, {
            'username': 'tokenuser', 'email': 'token@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        user = User.objects.get(username='tokenuser')
        self.assertTrue(EmailVerificationToken.objects.filter(user=user).exists())

    def test_register_creates_user_profile_viewer(self):
        self.client.post(self.register_url, {
            'username': 'profileuser', 'email': 'profile@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        user = User.objects.get(username='profileuser')
        self.assertEqual(user.profile.role, 'viewer')

    def test_register_password_mismatch_returns_400(self):
        resp = self.client.post(self.register_url, {
            'username': 'baduser', 'email': 'bad@test.com',
            'password': 'StrongPass123!', 'password2': 'WrongPass456!'
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Верификация email --

    def test_verify_email_activates_user(self):
        self.client.post(self.register_url, {
            'username': 'verifyuser', 'email': 'verify@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        user = User.objects.get(username='verifyuser')
        token = EmailVerificationToken.objects.get(user=user).token
        resp = self.client.get(f'/api/auth/verify-email/?token={token}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_verify_email_deletes_token(self):
        self.client.post(self.register_url, {
            'username': 'verifyuser2', 'email': 'v2@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        user = User.objects.get(username='verifyuser2')
        token = EmailVerificationToken.objects.get(user=user).token
        self.client.get(f'/api/auth/verify-email/?token={token}')
        self.assertFalse(EmailVerificationToken.objects.filter(user=user).exists())

    def test_verify_email_invalid_token_returns_400(self):
        resp = self.client.get('/api/auth/verify-email/?token=00000000-0000-0000-0000-000000000000')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Вход --

    def _active_user(self, username='activeuser', password='TestPass123!', role='viewer'):
        user = User.objects.create_user(
            username=username, password=password,
            email=f'{username}@test.com', is_active=True
        )
        UserProfile.objects.create(user=user, role=role)
        return user

    def test_login_success_returns_tokens(self):
        self._active_user()
        resp = self.client.post(self.login_url, {'username': 'activeuser', 'password': 'TestPass123!'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_login_returns_role(self):
        self._active_user(role='manager')
        resp = self.client.post(self.login_url, {'username': 'activeuser', 'password': 'TestPass123!'})
        self.assertEqual(resp.data['user']['role'], 'manager')

    def test_login_inactive_user_returns_403(self):
        User.objects.create_user(username='inactive', password='TestPass123!',
                                 email='i@test.com', is_active=False)
        resp = self.client.post(self.login_url, {'username': 'inactive', 'password': 'TestPass123!'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_wrong_password_returns_401(self):
        self._active_user()
        resp = self.client.post(self.login_url, {'username': 'activeuser', 'password': 'WRONG'})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- /me/ --

    def test_me_returns_user_data(self):
        user = self._active_user()
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'activeuser')

    def test_me_unauthenticated_returns_401(self):
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
