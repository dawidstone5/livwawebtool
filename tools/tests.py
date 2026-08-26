import io
import json
import re
from unittest.mock import patch

import pandas as pd
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from tools.models import ForecastResult
from tools.views.api_code import training_data


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


class PrecomputeForecastsCommandTests(TestCase):
    def test_precompute_creates_one_row_per_segment(self):
        call_command(
            "precompute_forecasts",
            "--start", "2022-08-01",
            "--segments", "2",
            stdout=io.StringIO(), stderr=io.StringIO(),
        )
        rows = list(ForecastResult.objects.order_by("start_date"))
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0].start_date.isoformat(), rows[0].end_date.isoformat()),
                          ("2022-08-01", "2022-11-01"))
        self.assertEqual((rows[1].start_date.isoformat(), rows[1].end_date.isoformat()),
                          ("2022-11-01", "2023-02-01"))
        self.assertTrue(all(row.result for row in rows))

    def test_rerunning_reuses_existing_cache_rows(self):
        call_command(
            "precompute_forecasts",
            "--start", "2022-08-01",
            "--segments", "1",
            stdout=io.StringIO(), stderr=io.StringIO(),
        )
        self.assertEqual(ForecastResult.objects.count(), 1)
        call_command(
            "precompute_forecasts",
            "--start", "2022-08-01",
            "--segments", "1",
            stdout=io.StringIO(), stderr=io.StringIO(),
        )
        self.assertEqual(ForecastResult.objects.count(), 1)


class PrecomputeForecastsBackfillTests(TestCase):
    """The no-`--start` path is a real full backfill from the training data's
    end through the future, which can take many minutes end-to-end - too slow
    for a test. Mock the expensive call and just verify the date math/looping
    produces the right segment sequence."""

    @patch("tools.management.commands.precompute_forecasts.get_or_create_forecast")
    def test_backfills_from_training_end_through_future_segments(self, mock_get_or_create):
        mock_get_or_create.return_value = []
        call_command("precompute_forecasts", "--segments", "1", stdout=io.StringIO(), stderr=io.StringIO())

        calls = mock_get_or_create.call_args_list
        self.assertGreater(len(calls), 1)

        expected_first_start = training_data['Date'].max() + pd.Timedelta(days=1)
        first_start = calls[0].args[0]
        self.assertEqual(first_start, {
            "year": expected_first_start.year,
            "month": expected_first_start.month,
            "day": expected_first_start.day,
        })

        last_end = calls[-1].args[1]
        last_end_ts = pd.Timestamp(year=last_end["year"], month=last_end["month"], day=last_end["day"])
        today_first = pd.Timestamp.today().replace(day=1)
        self.assertGreaterEqual(last_end_ts, today_first + pd.DateOffset(months=3))

        # Segments should be contiguous (no gaps, no overlaps).
        for prev_call, curr_call in zip(calls, calls[1:]):
            prev_end = prev_call.args[1]
            curr_start = curr_call.args[0]
            self.assertEqual(prev_end, curr_start)


class LevelsContinuousPlotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('levelsuser', 'levels@example.com', 'correct-password123')
        self.client.force_login(self.user)

    def test_plot_highlights_requested_range(self):
        response = self.client.post(reverse('levels'), {
            'reference_start': '2022-08-01', 'reference_end': '2022-11-01',
        })
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('Requested prediction', html)

    def test_second_adjacent_request_reuses_first_as_context(self):
        first = self.client.post(reverse('levels'), {
            'reference_start': '2022-08-01', 'reference_end': '2022-11-01',
        })
        self.assertEqual(first.status_code, 200)
        self.assertEqual(ForecastResult.objects.count(), 1)

        second = self.client.post(reverse('levels'), {
            'reference_start': '2022-11-01', 'reference_end': '2023-02-01',
        })
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ForecastResult.objects.count(), 2)

        # The chart embedded in the second response should carry more data
        # points than just its own ~3-month slice, since it pulls in the
        # first (adjacent, already-cached) request as context.
        match = re.search(r'"x":\[(.*?)\]', second.content.decode())
        self.assertIsNotNone(match)
        point_count = match.group(1).count(",") + 1
        self.assertGreater(point_count, 93)


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
