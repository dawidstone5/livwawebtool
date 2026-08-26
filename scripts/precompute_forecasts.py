#!/usr/bin/env python3
"""
Pre-warms the water-level forecast cache for the current and upcoming
quarters, so a user requesting a common date range gets an instant cache
hit instead of waiting on the full autoregressive prediction.

Run daily via cron. Each rerun is near-instant except right after a
calendar-month boundary, when one new quarter needs genuine computation
(see tools/management/commands/precompute_forecasts.py for why cost
doesn't scale with just that one quarter's span).
"""
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
os.chdir(PROJECT_DIR)  # tools/views/api_code.py loads the model/training data via relative paths
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "livwawebtool.settings")

import django
django.setup()

from django.core.management import call_command

SEGMENTS = 8  # ~2 years of quarterly coverage ahead of the current month


def main():
    call_command("precompute_forecasts", segments=SEGMENTS)


if __name__ == "__main__":
    main()
