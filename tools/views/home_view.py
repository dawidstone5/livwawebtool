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
