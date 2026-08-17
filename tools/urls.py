from django.urls import path
from tools.views import (bias_view, home_view, levels_view, reports_view)
from tools.views.api_code import ForecastLakeLevelsView, HealthCheckView

urlpatterns = [
    path('', home_view.home, name='home'),
    path('support/', home_view.support, name='support'),

    # Tools
    path('tools/', home_view.tools, name='tools'),
    path('bias/', bias_view.bias, name='bias'),
    path('levels/', levels_view.levels, name='levels'),
    path('reports/', reports_view.reports, name='reports'),

    # Lake levels API endpoints
    path('forecast/', ForecastLakeLevelsView.as_view(), name='forecast-lake-levels'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]