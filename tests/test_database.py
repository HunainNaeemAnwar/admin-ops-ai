from tools.database import (
    get_db, get_worker_id, get_or_create_worker, get_all_workers, get_active_workers,
    get_product_id, get_all_products, get_product_rate,
    log_production, mark_absent, update_entry, get_logs_for_date,
    log_rejection, get_rejections_for_month, get_worker_rejection_share,
    record_advance, get_advances_for_worker_month, get_total_advances_for_worker_month,
    save_payslip, get_payslip,
    get_daily_totals, get_worker_month_production,
)


class TestWorkers:
    def test_get_worker_id_exists(self, worker_ids):
        assert get_worker_id("Kaleem") == worker_ids["Kaleem"]

    def test_get_worker_id_unknown(self):
        assert get_worker_id("Nonexistent") is None

    def test_get_or_create_worker_existing(self, worker_ids):
        assert get_or_create_worker("Kaleem") == worker_ids["Kaleem"]

    def test_get_or_create_worker_new(self):
        wid = get_or_create_worker("NewWorker")
        assert wid is not None
        assert get_worker_id("NewWorker") == wid

    def test_get_all_workers_count(self, worker_ids):
        workers = get_all_workers()
        assert len(workers) >= 8
        names = {w["name"] for w in workers}
        assert "Kaleem" in names
        assert "Naeem" in names

    def test_get_active_workers(self):
        workers = get_active_workers()
        assert len(workers) >= 8


class TestProducts:
    def test_get_product_id(self):
        pid = get_product_id("NUT")
        assert pid is not None

    def test_get_product_id_unknown(self):
        assert get_product_id("FAKE") is None

    def test_get_all_products_count(self):
        prods = get_all_products()
        codes = {p["code"] for p in prods}
        assert len(prods) >= 5
        for c in ["NUT", "10*20", "6*25", "6*30", "10*25"]:
            assert c in codes

    def test_get_product_rate(self):
        assert get_product_rate("NUT") == 0.5
        assert get_product_rate("10*20") == 0.75
        assert get_product_rate("FAKE") is None


class TestDailyLog:
    def test_log_production(self, worker_ids, product_ids):
        eid = log_production(worker_ids["Kaleem"], product_ids["NUT"], 300, "2026-06-01")
        assert eid is not None
        logs = get_logs_for_date("2026-06-01")
        assert len(logs) == 1
        assert logs[0]["quantity"] == 300

    def test_log_production_duplicate(self, worker_ids, product_ids):
        log_production(worker_ids["Kaleem"], product_ids["NUT"], 300, "2026-06-01")
        import sqlite3
        try:
            log_production(worker_ids["Kaleem"], product_ids["NUT"], 300, "2026-06-01")
            assert False, "Should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass

    def test_mark_absent(self, worker_ids, product_ids):
        eid = mark_absent(worker_ids["Kaleem"], "2026-06-01")
        assert eid is not None
        logs = get_logs_for_date("2026-06-01")
        assert len(logs) == 1
        assert logs[0]["status"] == "absent"

    def test_update_entry(self, worker_ids, product_ids):
        eid = log_production(worker_ids["Kaleem"], product_ids["NUT"], 300, "2026-06-01")
        result = update_entry(eid, 500)
        assert result is True
        logs = get_logs_for_date("2026-06-01")
        assert logs[0]["quantity"] == 500

    def test_update_entry_not_found(self):
        result = update_entry(99999, 500)
        assert result is False

    def test_get_logs_for_date_empty(self):
        assert get_logs_for_date("2026-01-01") == []

    def test_get_logs_for_date_multiple(self, worker_ids, product_ids):
        log_production(worker_ids["Kaleem"], product_ids["NUT"], 300, "2026-06-01")
        log_production(worker_ids["Naeem"], product_ids["10*20"], 150, "2026-06-01")
        logs = get_logs_for_date("2026-06-01")
        assert len(logs) == 2

    def test_worker_month_production(self, worker_ids, product_ids):
        log_production(worker_ids["Kaleem"], product_ids["NUT"], 300, "2026-06-01")
        log_production(worker_ids["Kaleem"], product_ids["10*20"], 150, "2026-06-02")
        entries = get_worker_month_production(worker_ids["Kaleem"], 2026, 6)
        assert len(entries) == 2
        codes = {e["product_code"] for e in entries}
        assert "NUT" in codes
        assert "10*20" in codes


class TestRejections:
    def test_log_rejection(self, product_ids):
        rid = log_rejection(2026, 6, product_ids["NUT"], 100, [])
        assert rid is not None

    def test_get_rejections_for_month(self, product_ids):
        log_rejection(2026, 6, product_ids["NUT"], 100, [])
        rejs = get_rejections_for_month(2026, 6)
        assert len(rejs) == 1
        assert rejs[0]["total_qty"] == 100

    def test_get_worker_rejection_share(self, product_ids):
        log_rejection(2026, 6, product_ids["NUT"], 80, [])
        shares = get_worker_rejection_share("Kaleem", 2026, 6)
        assert shares["NUT"] == 10

    def test_get_worker_rejection_share_with_excluded(self, product_ids):
        log_rejection(2026, 6, product_ids["NUT"], 80, ["Kaleem"])
        shares = get_worker_rejection_share("Kaleem", 2026, 6)
        assert shares["NUT"] == 0

    def test_rejection_uneven_distribution(self, product_ids):
        log_rejection(2026, 6, product_ids["NUT"], 17, [])
        # 17 pieces / 8 workers = 2 each, 1 remainder → Akbar (first alpha) gets 3
        shares = get_worker_rejection_share("Akbar", 2026, 6)
        assert shares["NUT"] == 3


class TestAdvances:
    def test_record_advance(self, worker_ids):
        aid = record_advance(worker_ids["Kaleem"], 5000, 2026, 6, "Test advance")
        assert aid is not None

    def test_get_advances_for_worker_month(self, worker_ids):
        record_advance(worker_ids["Kaleem"], 5000, 2026, 6, "")
        advances = get_advances_for_worker_month(worker_ids["Kaleem"], 2026, 6)
        assert len(advances) == 1
        assert advances[0]["amount"] == 5000

    def test_get_total_advances(self, worker_ids):
        record_advance(worker_ids["Kaleem"], 3000, 2026, 6, "")
        record_advance(worker_ids["Kaleem"], 2000, 2026, 6, "")
        total = get_total_advances_for_worker_month(worker_ids["Kaleem"], 2026, 6)
        assert total == 5000.0

    def test_advances_different_workers(self, worker_ids):
        record_advance(worker_ids["Kaleem"], 5000, 2026, 6, "")
        record_advance(worker_ids["Naeem"], 3000, 2026, 6, "")
        assert get_total_advances_for_worker_month(worker_ids["Kaleem"], 2026, 6) == 5000.0
        assert get_total_advances_for_worker_month(worker_ids["Naeem"], 2026, 6) == 3000.0

    def test_no_advances(self, worker_ids):
        total = get_total_advances_for_worker_month(worker_ids["Kaleem"], 2026, 6)
        assert total == 0.0


class TestPayslips:
    def test_save_and_get_payslip(self, worker_ids):
        save_payslip(worker_ids["Kaleem"], 2026, 6, 10000, 300, 500, 2000, 7200)
        slip = get_payslip(worker_ids["Kaleem"], 2026, 6)
        assert slip is not None
        assert slip["gross_total"] == 10000
        assert slip["tax_total"] == 300
        assert slip["net_payable"] == 7200

    def test_update_payslip(self, worker_ids):
        save_payslip(worker_ids["Kaleem"], 2026, 6, 10000, 300, 500, 2000, 7200)
        save_payslip(worker_ids["Kaleem"], 2026, 6, 12000, 360, 500, 2500, 8640)
        slip = get_payslip(worker_ids["Kaleem"], 2026, 6)
        assert slip["gross_total"] == 12000

    def test_payslip_not_found(self, worker_ids):
        assert get_payslip(worker_ids["Kaleem"], 2026, 6) is None
