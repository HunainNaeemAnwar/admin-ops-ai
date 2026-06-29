from services.report_tools import get_daily_status, get_summary
from services.production_tools import log_production_json, mark_absent


class TestGetDailyStatus:
    def test_no_data(self):
        result = get_daily_status("2026-06-01")
        assert "NO_DATA" in result

    def test_with_data(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        result = get_daily_status()
        assert "DATA_FOUND" in result
        assert "Kaleem" in result

    def test_multiple_workers(self):
        log_production_json(
            '[{"worker":"Kaleem","product_code":"NUT","quantity":300},'
            '{"worker":"Naeem","product_code":"10*20","quantity":150}]'
        )
        result = get_daily_status()
        assert "Kaleem" in result
        assert "Naeem" in result

    def test_shows_product_totals(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        log_production_json('[{"worker":"Naeem","product_code":"NUT","quantity":200}]')
        result = get_daily_status()
        assert "NUT" in result
        assert "500" in result  # total NUT

    def test_shows_absent_workers(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        result = get_daily_status()
        assert "Absent" in result
        assert "Kaleem" in result


class TestSummary:
    def test_daily_summary_no_data(self):
        result = get_summary("daily", 2026, 6, 1)
        assert "Summary" in result

    def test_daily_summary_with_data(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        from datetime import date
        today = date.today()
        result = get_summary("daily", today.year, today.month, today.day)
        assert "NUT" in result
        assert "300" in result

    def test_weekly_summary(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        from datetime import date
        today = date.today()
        result = get_summary("weekly", today.year, today.month, today.day)
        assert "Weekly Summary" in result

    def test_monthly_summary(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        log_production_json('[{"worker":"Naeem","product_code":"10*20","quantity":150}]')
        from datetime import date
        today = date.today()
        result = get_summary("monthly", today.year, today.month)
        assert "Monthly Summary" in result
        assert "Kaleem" in result
        assert "Naeem" in result

    def test_invalid_period(self):
        result = get_summary("yearly", 2026, 6, 1)
        assert "Unknown period" in result
