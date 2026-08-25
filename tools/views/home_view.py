# import neccessary functions, libraries, and packages
from django.shortcuts import render

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
    return render(request, 'support.html', {'template_name': template_name})

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
