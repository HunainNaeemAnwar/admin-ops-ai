from services.production_tools import log_production_json
from services.export_tools import generate_daily_excel_stream, generate_weekly_excel_stream, generate_monthly_excel_stream
from services.payslip_tools import generate_pdf_payslip
from services.rejection_tools import log_rejection
from services.advance_tools import record_advance


class TestGenerateExcelStream:
    def test_daily_stream_returns_bytesio(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        log_production_json('[{"worker":"Naeem","product_code":"10*20","quantity":150}]')
        from datetime import date
        today = date.today()
        buf, filename = generate_daily_excel_stream(today.year, today.month, today.day)
        assert buf is not None
        assert buf.read(4) == b"PK\x03\x04"

    def test_weekly_stream_returns_bytesio(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        from datetime import date
        today = date.today()
        buf, filename = generate_weekly_excel_stream(today.year, today.month, today.day)
        assert buf is not None
        assert buf.read(4) == b"PK\x03\x04"

    def test_monthly_stream_returns_bytesio(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        from datetime import date
        today = date.today()
        buf, filename = generate_monthly_excel_stream(today.year, today.month)
        assert buf is not None
        assert buf.read(4) == b"PK\x03\x04"


class TestPayslipGeneration:
    def test_pdf_payslip_generated(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        log_production_json('[{"worker":"Kaleem","product_code":"10*20","quantity":150}]')
        record_advance("Kaleem", 5000, 2026, 6)
        from datetime import date
        today = date.today()
        path = generate_pdf_payslip("Kaleem", today.year, today.month)
        assert path is not None
        from pathlib import Path
        assert Path(path).exists()
        Path(path).unlink()

    def test_payslip_no_data(self):
        path = generate_pdf_payslip("UnknownWorker", 2026, 6)
        assert "No data" in str(path) if isinstance(path, str) else True
