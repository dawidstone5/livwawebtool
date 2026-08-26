from django.db import models


class ForecastResult(models.Model):
    """Cached output of tools.views.api_code.forecast() for a given date range.

    model_version pins a cache row to the model artifact that produced it
    (see api_code.model_version), so replacing models/output.pkl naturally
    invalidates stale predictions instead of serving them forever.
    """
    start_date = models.DateField()
    end_date = models.DateField()
    horizon = models.PositiveIntegerField(default=120)
    model_version = models.CharField(max_length=64)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("start_date", "end_date", "horizon", "model_version")
