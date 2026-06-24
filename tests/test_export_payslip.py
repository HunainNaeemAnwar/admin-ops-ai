from pathlib import Path

from tools.production_tools import log_production_json
from tools.export_tools import generate_excel_report
from tools.payslip_tools import generate_pdf_payslip
from tools.database import get_worker_id, get_worker_month_production
from tools.rejection_tools import log_rejection
from tools.advance_tools import record_advance


class TestGenerateExcelReport:
    def test_daily_report_creates_file(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        log_production_json('[{"worker":"Naeem","product_code":"10*20","quantity":150}]')
        from datetime import date
        today = date.today()
        path = generate_excel_report("daily", today.year, today.month, today.day)
        assert path is not None
        assert Path(path).exists()
        Path(path).unlink()

    def test_weekly_report_creates_file(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        from datetime import date
        today = date.today()
        path = generate_excel_report("weekly", today.year, today.month, today.day)
        assert path is not None
        assert Path(path).exists()
        Path(path).unlink()

    def test_monthly_report_creates_file(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        from datetime import date
        today = date.today()
        path = generate_excel_report("monthly", today.year, today.month)
        assert path is not None
        assert Path(path).exists()
        Path(path).unlink()

    def test_invalid_period(self):
        result = generate_excel_report("yearly")
        assert "Unknown period" in result


class TestPayslipGeneration:
    def test_pdf_payslip_generated(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        log_production_json('[{"worker":"Kaleem","product_code":"10*20","quantity":150}]')
        record_advance("Kaleem", 5000, 2026, 6)
        from datetime import date
        today = date.today()
        path = generate_pdf_payslip("Kaleem", today.year, today.month)
        assert path is not None
        assert Path(path).exists()
        Path(path).unlink()

    def test_payslip_no_data(self):
        path = generate_pdf_payslip("UnknownWorker", 2026, 6)
        assert path is None or "No data" in str(path) if isinstance(path, str) else True
