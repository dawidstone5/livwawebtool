from django.urls import path
from tools.views import (bias_view, home_view,
                         levels_view, reports_view,
                         auths_view)
from tools.views.api_code import ForecastLakeLevelsView, HealthCheckView
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', home_view.home, name='home'),
    path('support/', home_view.support, name='support'),

    # authentication
    path('signup/', auths_view.signup_view, name='signup'),
    path('login/', auths_view.login_view, name='login'),
    path('logout/', auths_view.user_logout, name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
    path('activate/<uidb64>/<token>/', auths_view.activate, name='activate'),

    # tools
    path('tools/', home_view.tools, name='tools'),
    path('bias/', bias_view.bias, name='bias'),
    path('levels/', levels_view.levels, name='levels'),
    path('reports/', reports_view.reports, name='reports'),

    # lake levels API endpoints
    path('forecast/', ForecastLakeLevelsView.as_view(), name='forecast-lake-levels'),
    path('', HealthCheckView.as_view(), name='health-check'),
]
