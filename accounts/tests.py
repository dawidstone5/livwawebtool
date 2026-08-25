from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from axes.models import AccessAttempt


class SignupTests(TestCase):
    def test_signup_creates_inactive_user_and_sends_activation_email(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'a-strong-passw0rd',
            'password2': 'a-strong-passw0rd',
        })
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username='newuser')
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('newuser@example.com', mail.outbox[0].to)

    def test_signup_rejects_duplicate_username(self):
        User.objects.create_user('taken', 'taken@example.com', 'somepassword123')
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'taken',
            'email': 'other@example.com',
            'password1': 'a-strong-passw0rd',
            'password2': 'a-strong-passw0rd',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='other@example.com').exists())


class ActivationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('inactiveuser', 'inactive@example.com', 'somepassword123')
        self.user.is_active = False
        self.user.save()

    def test_valid_activation_link_activates_and_logs_in(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.get(reverse('accounts:activate', args=[uid, token]))

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertRedirects(response, reverse('home'))

    def test_invalid_token_does_not_activate(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(reverse('accounts:activate', args=[uid, 'bad-token']))

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(response.status_code, 200)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('loginuser', 'login@example.com', 'correct-password123')

    def test_correct_credentials_log_in(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'loginuser',
            'password': 'correct-password123',
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_wrong_password_rejected(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'loginuser',
            'password': 'totally-wrong',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_valid())

    def test_open_redirect_is_blocked(self):
        """next= pointing at an external host must not be honored (security regression test)."""
        url = reverse('accounts:login') + '?next=https://evil.example.com/phish'
        response = self.client.post(url, {
            'username': 'loginuser',
            'password': 'correct-password123',
        })
        self.assertRedirects(response, reverse('home'))

    def test_next_param_to_a_local_page_is_honored(self):
        url = reverse('accounts:login') + '?next=' + reverse('support')
        response = self.client.post(url, {
            'username': 'loginuser',
            'password': 'correct-password123',
        })
        self.assertRedirects(response, reverse('support'))


class BruteForceLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('lockoutuser', 'lockout@example.com', 'correct-password123')

    def test_repeated_failures_lock_out_even_correct_password(self):
        for _ in range(5):
            self.client.post(reverse('accounts:login'), {
                'username': 'lockoutuser',
                'password': 'wrong-password',
            })

        self.assertTrue(AccessAttempt.objects.filter(username='lockoutuser').exists())

        response = self.client.post(reverse('accounts:login'), {
            'username': 'lockoutuser',
            'password': 'correct-password123',
        })
        # Locked out: axes' middleware intercepts before a normal redirect happens.
        self.assertNotEqual(response.status_code, 302)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('profileuser', 'profile@example.com', 'correct-password123')

    def test_anonymous_user_redirected_from_profile(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_anonymous_user_redirected_from_delete_account(self):
        response = self.client.get(reverse('accounts:delete_account'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_saving_profile_redirects_without_error(self):
        """Regression test: profile_view used to call redirect('profile') — an
        unnamespaced name that doesn't exist (accounts/urls.py registers it as
        accounts:profile), which raised NoReverseMatch on every profile save."""
        # force_login (not client.login) — django-axes' backend requires a real
        # request during authenticate(), which client.login() doesn't provide.
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:profile'), {
            'email': 'updated@example.com',
            'first_name': 'Test',
            'last_name': 'User',
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')
