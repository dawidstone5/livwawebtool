import logging

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from tools.views.api_code import get_or_create_forecast, training_data

logger = logging.getLogger(__name__)


MAX_ITERATIONS = 200  # sanity cap; a real run never gets close to this


class Command(BaseCommand):
    help = (
        "Pre-warm the forecast cache with consecutive 3-month segments, so that "
        "when users request one of these common date ranges the prediction is "
        "already stored and loads instantly instead of being computed on demand. "
        "With no --start, also backfills every quarter between where the training "
        "data ends and today, so a request anywhere in that (likely large) gap has "
        "cached data leading up to it for a continuous historical-to-predicted plot."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--segments", type=int, default=8,
            help=(
                "With --start: exact number of consecutive 3-month segments to precompute. "
                "Without --start: how many quarters beyond the current month to precompute, "
                "in addition to backfilling the training-data-to-now gap (default: 8, i.e. 2 years)."
            ),
        )
        parser.add_argument(
            "--start", type=str, default=None,
            help=(
                "First segment's start date as YYYY-MM-DD. If omitted, backfilling starts "
                "the day after the training data's last date, so the entire gap up to now "
                "gets covered too."
            ),
        )

    def handle(self, *args, **options):
        if training_data is None:
            raise CommandError("Training data not loaded; aborting.")

        segments = options["segments"]
        if segments < 1:
            raise CommandError("--segments must be at least 1.")

        if options["start"]:
            segment_start = pd.Timestamp(options["start"]).replace(day=1)
            target_end = None
            iterations = segments
        else:
            # Start right after the training data ends (not rounded to day=1,
            # which could land exactly on the training data's last date and
            # hit a forecast() branch that neither treats it as historical
            # nor as a future start).
            segment_start = training_data['Date'].max() + pd.Timedelta(days=1)
            target_end = pd.Timestamp.today().replace(day=1) + pd.DateOffset(months=3 * segments)
            iterations = MAX_ITERATIONS

        count = 0
        while count < iterations:
            if target_end is not None and segment_start >= target_end:
                break
            count += 1

            segment_end = segment_start + pd.DateOffset(months=3)
            start = {"year": segment_start.year, "month": segment_start.month, "day": segment_start.day}
            end = {"year": segment_end.year, "month": segment_end.month, "day": segment_end.day}

            label = f"{segment_start.date()} -> {segment_end.date()}"
            self.stdout.write(f"Precomputing {label} ...")
            try:
                get_or_create_forecast(start, end, training_data)
                self.stdout.write(self.style.SUCCESS(f"  cached {label}"))
            except Exception:
                logger.exception("Failed to precompute segment %s", label)
                self.stderr.write(self.style.ERROR(f"  failed {label} (see logs)"))

            segment_start = segment_end
