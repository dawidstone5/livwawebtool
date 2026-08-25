from django.urls import path
from tools.views import (bias_view, home_view, levels_view, reports_view)
from tools.views.api_code import ForecastLakeLevelsView, HealthCheckView

urlpatterns = [
    path('', home_view.home, name='home'),
    path('support/', home_view.support, name='support'),
    path('coming-soon/<slug:tool>/', home_view.coming_soon, name='coming-soon'),

    # Tools
    path('tools/', home_view.tools, name='tools'),
    path('bias/', bias_view.bias, name='bias'),
    path('bias/export/csv/', bias_view.bias_export_csv, name='bias-export-csv'),
    path('bias/export/pdf/', bias_view.bias_export_pdf, name='bias-export-pdf'),
    path('levels/', levels_view.levels, name='levels'),
    path('reports/', reports_view.reports, name='reports'),

    # Lake levels API endpoints
    path('forecast/', ForecastLakeLevelsView.as_view(), name='forecast-lake-levels'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]