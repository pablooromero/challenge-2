import unittest
from unittest.mock import patch

from app.core.errors import AnalyticsValidationError
from app.domain.analytics.filters import normalize_date
from app.domain.analytics import flexible


class NormalizeDateTests(unittest.TestCase):
    def test_year_expands_to_boundaries(self) -> None:
        self.assertEqual(normalize_date("2025", "start_date", "start"), "2025-01-01")
        self.assertEqual(normalize_date("2025", "end_date", "end"), "2025-12-31")

    def test_month_expands_to_month_boundaries(self) -> None:
        self.assertEqual(normalize_date("2026-02", "start_date", "start"), "2026-02-01")
        # 2026 is not a leap year, so February ends on the 28th.
        self.assertEqual(normalize_date("2026-02", "end_date", "end"), "2026-02-28")

    def test_full_date_passthrough(self) -> None:
        self.assertEqual(normalize_date("2026-03-15", "start_date", "start"), "2026-03-15")

    def test_none_returns_none(self) -> None:
        self.assertIsNone(normalize_date(None, "start_date", "start"))

    def test_invalid_value_raises(self) -> None:
        with self.assertRaises(AnalyticsValidationError):
            normalize_date("not-a-date", "start_date", "start")


class FlexibleQueryValidationTests(unittest.TestCase):
    def test_unsupported_metric_raises(self) -> None:
        with self.assertRaises(AnalyticsValidationError):
            flexible._validate_spec(["not_a_metric"], "none", None)

    def test_unsupported_dimension_raises(self) -> None:
        with self.assertRaises(AnalyticsValidationError):
            flexible._validate_spec(["total_sales"], "channel", None)

    def test_metrics_are_deduped_and_default(self) -> None:
        self.assertEqual(
            flexible._validate_spec(["total_sales", "total_sales", "total_leads"], "month", None),
            ["total_sales", "total_leads"],
        )
        self.assertEqual(flexible._validate_spec([], "none", None), ["total_sales"])

    def test_derived_metrics_computed_from_base_sums(self) -> None:
        row = flexible._row_from_db(
            {
                "dimension": "2025-10",
                "total_leads": 100,
                "total_sales": 25,
                "total_revenue_usd": 5000.0,
                "total_ad_cost_usd": 1000.0,
                "total_clicks": 200,
                "total_impressions": 4000,
            }
        )
        self.assertEqual(row.conversion_rate, 0.25)
        self.assertEqual(row.roas, 5.0)
        self.assertEqual(row.ctr, 0.05)
        self.assertEqual(row.cpa, 40.0)

    def test_derived_metrics_handle_zero_denominators(self) -> None:
        row = flexible._row_from_db(
            {
                "dimension": None,
                "total_leads": 0,
                "total_sales": 0,
                "total_revenue_usd": 0.0,
                "total_ad_cost_usd": 0.0,
                "total_clicks": 0,
                "total_impressions": 0,
            }
        )
        self.assertEqual(row.roas, 0.0)
        self.assertEqual(row.conversion_rate, 0.0)
        self.assertEqual(row.ctr, 0.0)

    def test_run_metric_query_sorts_and_limits_in_python(self) -> None:
        fake_rows = [
            {"dimension": "2025-01", "total_leads": 10, "total_sales": 1, "total_revenue_usd": 0.0,
             "total_ad_cost_usd": 0.0, "total_clicks": 0, "total_impressions": 0},
            {"dimension": "2025-02", "total_leads": 30, "total_sales": 3, "total_revenue_usd": 0.0,
             "total_ad_cost_usd": 0.0, "total_clicks": 0, "total_impressions": 0},
            {"dimension": "2025-03", "total_leads": 20, "total_sales": 2, "total_revenue_usd": 0.0,
             "total_ad_cost_usd": 0.0, "total_clicks": 0, "total_impressions": 0},
        ]
        with patch.object(flexible, "fetch_metric_aggregates", return_value=fake_rows), patch.object(
            flexible, "build_meta"
        ) as mock_meta:
            mock_meta.return_value = _fake_meta()
            result = flexible.run_metric_query(
                metrics=["total_leads"], dimension="month", sort_by="total_leads", limit=2
            )
        self.assertEqual([row.dimension for row in result.rows], ["2025-02", "2025-03"])


def _fake_meta():
    from app.schemas.analytics import AnalyticsMeta
    from app.schemas.responses import DataRange

    return AnalyticsMeta(
        data_range=DataRange(from_date="2025-01-01", to_date="2025-03-31"),
        record_count=3,
        granularity="month",
        primary_unit="mixed",
    )


if __name__ == "__main__":
    unittest.main()
