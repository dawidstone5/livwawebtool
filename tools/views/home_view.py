# import neccessary functions, libraries, and packages
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from tools.forms import SupportForm

logger = logging.getLogger(__name__)

# _____________________________________________________________________________________________________________HOME_VIEW____
def home(request):
    if request.user.is_authenticated:
        template_name = 'base_usr.html'
    else:
        template_name = 'base_all.html'
    return render(request, 'home.html', {'template_name': template_name})

# ____________________________________________________________________________________________________________TOOLS_VIEW____
def tools(request):
    if request.user.is_authenticated:
        template_name = 'base_usr.html'
    else:
        template_name = 'base_all.html'
    return render(request, 'tools/tools.html', {'template_name': template_name})

# __________________________________________________________________________________________________________SUPPORT_VIEW____
def support(request):
    if request.user.is_authenticated:
        template_name = 'base_usr.html'
    else:
        template_name = 'base_all.html'
    context = {'template_name': template_name}

    if request.method == 'POST':
        form = SupportForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            user_message = form.cleaned_data['message']

            if settings.SUPPORT_EMAIL:
                try:
                    EmailMessage(
                        subject=f'[LIVWA Support] Message from {name}',
                        body=f'From: {name} <{email}>\n\n{user_message}',
                        to=[settings.SUPPORT_EMAIL],
                        reply_to=[email],
                    ).send()
                    messages.success(
                        request,
                        "Thanks for reaching out - we've received your message and will get back to you soon.",
                    )
                except Exception:
                    logger.exception("Failed to send support message")
                    messages.error(request, "Something went wrong sending your message. Please try again later.")
            else:
                logger.error("SUPPORT_EMAIL is not configured; dropping support message from %s", email)
                messages.error(request, "Support messaging isn't configured yet. Please try again later.")
            return redirect('support')
    else:
        form = SupportForm()

    context['form'] = form
    return render(request, 'support.html', context)

# ____________________________________________________________________________________________________COMING_SOON_VIEW____
COMING_SOON_TOOLS = {
    'climate-analysis': {
        'label': 'Climate Analysis',
        'description': 'Trend and impact analysis of climate change on Lake Victoria\'s water resources.',
        'icon': 'fa-cloud-sun',
    },
    'recent-activity': {
        'label': 'Recent Activity',
        'description': 'A history of your past analysis sessions, so you can revisit or resume them.',
        'icon': 'fa-history',
    },
}


def coming_soon(request, tool):
    if request.user.is_authenticated:
        template_name = 'base_usr.html'
    else:
        template_name = 'base_all.html'
    info = COMING_SOON_TOOLS.get(tool, {
        'label': tool.replace('-', ' ').title(),
        'description': 'This tool is still being built.',
        'icon': 'fa-tools',
    })
    context = {'template_name': template_name, **info}
    return render(request, 'tools/coming_soon.html', context)
