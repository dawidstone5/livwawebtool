from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib import messages
from .forms import SignUpForm, LoginForm, UserProfileForm


# Create your views here.

def get_template_name(request):
    """Helper function to determine which base template to use"""
    return 'base_usr.html' if request.user.is_authenticated else 'base_all.html'


def signup_view(request):
    """Handle user registration"""
    context = {'template_name': get_template_name(request)}

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate until email is verified
            user.save()
            
            # Send verification email
            current_site = get_current_site(request)
            mail_subject = 'Activate your LIVWA account'
            # Don't pass template_name for email - it should be a standalone email template
            message = render_to_string('accounts/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.content_subtype = 'html'  # Set email content type to HTML
            email.send()
            
            messages.success(request, 'Please check your email to verify your account.')
            return render(request, 'accounts/acc_active_email_sent.html', context)
    else:
        form = SignUpForm()
    
    context['form'] = form
    return render(request, 'accounts/signup.html', context)


def activate(request, uidb64, token):
    """Activate user account via email link"""
    context = {'template_name': get_template_name(request)}
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, 'Your account has been activated successfully!')
        return redirect('home')
    else:
        messages.error(request, 'Activation link is invalid or has expired.')
        return render(request, 'accounts/acc_invalid_link.html', context)


def login_view(request):
    """Handle user login"""
    context = {'template_name': get_template_name(request)}
    
    # Redirect if already authenticated
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next parameter or home
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    context['form'] = form
    return render(request, 'accounts/login.html', context)


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """View and edit user profile"""
    context = {'template_name': get_template_name(request)}
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context['form'] = form
    return render(request, 'accounts/profile.html', context)


@login_required
def delete_account_view(request):
    """Handle account deletion"""
    context = {'template_name': get_template_name(request)}
    
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been deleted successfully.')
        return redirect('home')
    
    return render(request, 'accounts/delete_account.html', context)