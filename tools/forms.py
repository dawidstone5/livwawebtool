from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

# login form
class LoginForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ('username', 'password')


# signup form
class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False  # Deactivate account till it is confirmed
        if commit:
            user.save()
            self.send_verification_email(user)
        return user

    def send_verification_email(self, user):
        subject = 'Verify your email'
        message = f'Hi {user.username},\n\nPlease click on the link to verify your email:\n\nhttp://{settings.DOMAIN_NAME}/accounts/verify/{user.pk}/{user.username}/'
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
