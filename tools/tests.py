import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tools.models import ForecastResult


class HealthCheckTests(TestCase):
    def test_health_check_returns_healthy(self):
        response = self.client.get(reverse('health-check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'healthy')


class ForecastApiTests(TestCase):
    def test_valid_request_returns_forecast(self):
        response = self.client.post(
            reverse('forecast-lake-levels'),
            data=json.dumps({
                'start_year': 2020, 'start_month': 1, 'start_day': 1,
                'end_year': 2020, 'end_month': 2, 'end_day': 1,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn('forecast', body)
        self.assertGreater(len(body['forecast']), 0)
        self.assertIn('Date', body['forecast'][0])
        self.assertIn('Lake_Level', body['forecast'][0])

    def test_missing_fields_rejected(self):
        response = self.client.post(
            reverse('forecast-lake-levels'),
            data=json.dumps({'start_year': 2020}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_end_before_start_is_rejected_not_500(self):
        response = self.client.post(
            reverse('forecast-lake-levels'),
            data=json.dumps({
                'start_year': 2020, 'start_month': 6, 'start_day': 1,
                'end_year': 2020, 'end_month': 1, 'end_day': 1,
            }),
            content_type='application/json',
        )
        self.assertNotEqual(response.status_code, 500)


class ForecastCacheTests(TestCase):
    payload = {
        'start_year': 2020, 'start_month': 1, 'start_day': 1,
        'end_year': 2020, 'end_month': 2, 'end_day': 1,
    }

    def test_repeat_request_reuses_cached_row(self):
        self.assertEqual(ForecastResult.objects.count(), 0)

        first = self.client.post(
            reverse('forecast-lake-levels'),
            data=json.dumps(self.payload),
            content_type='application/json',
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(ForecastResult.objects.count(), 1)

        second = self.client.post(
            reverse('forecast-lake-levels'),
            data=json.dumps(self.payload),
            content_type='application/json',
        )
        self.assertEqual(second.status_code, 200)
        # Same request served from the cache: no second row, identical payload.
        self.assertEqual(ForecastResult.objects.count(), 1)
        self.assertEqual(first.json(), second.json())


class ToolAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tooluser', 'tool@example.com', 'correct-password123')

    def test_home_page_loads_for_anonymous(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_tools_dashboard_loads(self):
        response = self.client.get(reverse('tools'))
        self.assertEqual(response.status_code, 200)

    def test_bias_requires_login(self):
        response = self.client.get(reverse('bias'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_levels_requires_login(self):
        response = self.client.get(reverse('levels'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_reports_requires_login(self):
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_authenticated_user_can_reach_bias_page(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bias'))
        self.assertEqual(response.status_code, 200)


class ComingSoonTests(TestCase):
    def test_known_tool_shows_its_own_label(self):
        response = self.client.get(reverse('coming-soon', args=['climate-analysis']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Climate Analysis')

    def test_unknown_tool_slug_does_not_error(self):
        response = self.client.get(reverse('coming-soon', args=['something-made-up']))
        self.assertEqual(response.status_code, 200)


class BiasCorrectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('biasuser', 'bias@example.com', 'correct-password123')
        self.client.force_login(self.user)

    def _csv_upload(self, values):
        from django.core.files.uploadedfile import SimpleUploadedFile
        rows = "\n".join(f"2020-01-0{i+1},{v}" for i, v in enumerate(values))
        content = f"date,value\n{rows}\n".encode()
        return SimpleUploadedFile("data.csv", content, content_type="text/csv")

    def test_valid_upload_produces_metrics_and_chart(self):
        response = self.client.post(reverse('bias'), {
            'observations_file': self._csv_upload([10.1, 10.3, 10.5, 10.2, 10.6]),
            'remote_sensing_file': self._csv_upload([9.5, 9.7, 9.9, 9.6, 10.0]),
            'variable_select': 'precipitation',
            'correction_method': 'linear_scaling',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('metrics_after', response.context)
        self.assertIn('plot_html', response.context)
        # Session summary used by the Reports tool should be populated
        self.assertIn('last_bias_result', self.client.session)

    def test_missing_files_shows_error_not_500(self):
        response = self.client.post(reverse('bias'), {
            'variable_select': 'precipitation',
            'correction_method': 'linear_scaling',
        })
        self.assertEqual(response.status_code, 200)
