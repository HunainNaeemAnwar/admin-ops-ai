import json
import sqlite3

from services.production_tools import (
    log_production_json, mark_absent, mark_all_absent,
    update_entry, calc_piece_rate, get_product_info,
)


class TestCalcPieceRate:
    def test_calc_piece_rate_nut(self):
        result = calc_piece_rate("NUT", 300)
        assert result["product_code"] == "NUT"
        assert result["quantity"] == 300
        assert result["gross"] == 150.0
        assert result["tax_amt"] == 4.5
        assert result["net"] == 145.5

    def test_calc_piece_rate_10x20(self):
        result = calc_piece_rate("10*20", 200)
        assert result["gross"] == 150.0
        assert result["net"] == 145.5

    def test_calc_piece_rate_unknown_product(self):
        result = calc_piece_rate("FAKE", 100)
        assert "error" in result

    def test_calc_piece_rate_zero_quantity(self):
        result = calc_piece_rate("NUT", 0)
        assert result["gross"] == 0.0


class TestLogProductionJson:
    def test_single_entry(self):
        result = log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        assert "Kaleem" in result
        assert "300" in result
        assert "NUT" in result

    def test_multiple_entries(self):
        result = log_production_json(
            '[{"worker":"Kaleem","product_code":"NUT","quantity":300},'
            '{"worker":"Naeem","product_code":"10*20","quantity":150}]'
        )
        assert "Kaleem" in result
        assert "Naeem" in result
        assert "300" in result
        assert "150" in result

    def test_invalid_json(self):
        result = log_production_json("not json")
        assert "Invalid" in result

    def test_empty_worker(self):
        result = log_production_json('[{"worker":"","product_code":"NUT","quantity":300}]')
        assert "Invalid" in result

    def test_unknown_product(self):
        result = log_production_json('[{"worker":"Kaleem","product_code":"FAKE","quantity":300}]')
        assert "Unknown product" in result

    def test_zero_quantity(self):
        result = log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":0}]')
        assert "Invalid" in result

    def test_duplicate_entry_update(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        result = log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":500}]')
        assert "updated" in result.lower()

    def test_new_worker_auto_create(self):
        result = log_production_json('[{"worker":"NewGuy","product_code":"NUT","quantity":100}]')
        assert "NewGuy" in result
        from services.database import get_worker_id
        assert get_worker_id("NewGuy") is not None


class TestMarkAbsent:
    def test_mark_absent_single(self):
        result = mark_absent("Kaleem", "2026-06-01")
        assert "Marked" in result
        assert "Kaleem" in result
        assert "2026-06-01" in result

    def test_mark_absent_already_exists(self):
        from services.database import get_db
        mark_absent("Kaleem", "2026-06-01")
        result = mark_absent("Kaleem", "2026-06-01")
        assert "already" in result.lower()

    def test_mark_all_absent(self):
        result = mark_all_absent("2026-06-01")
        assert "Marked absent" in result

    def test_mark_all_absent_twice(self):
        mark_all_absent("2026-06-01")
        result = mark_all_absent("2026-06-01")
        assert "already" in result or "Marked absent" in result


class TestUpdateEntry:
    def test_update_entry(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        from services.database import get_logs_for_date
        from datetime import date
        logs = get_logs_for_date(date.today().isoformat())
        eid = logs[0]["id"]
        result = update_entry(eid, 500, "Correction")
        assert str(eid) in result
        assert "300 -> 500" in result
        assert "Correction" in result

    def test_update_entry_not_found(self):
        result = update_entry(99999, 500)
        assert "not found" in result.lower()

    def test_update_entry_no_reason(self):
        log_production_json('[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')
        from services.database import get_logs_for_date
        from datetime import date
        logs = get_logs_for_date(date.today().isoformat())
        eid = logs[0]["id"]
        result = update_entry(eid, 500)
        assert "300 -> 500" in result


class TestGetProductInfo:
    def test_get_product_info_nut(self):
        info = get_product_info("NUT")
        assert info is not None
        assert info["code"] == "NUT"
        assert info["rate"] > 0

    def test_get_product_info_unknown(self):
        assert get_product_info("FAKE") is None
