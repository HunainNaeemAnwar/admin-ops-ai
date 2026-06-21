from tools.rejection_tools import log_rejection, get_distribution_for_month
from tools.advance_tools import record_advance, get_advances_summary


class TestLogRejection:
    def test_rejection_basic(self):
        result = log_rejection(2026, 6, "NUT", 80)
        assert "Rejection recorded" in result
        assert "80xNUT" in result
        assert "Eligible" in result

    def test_rejection_with_excluded(self):
        result = log_rejection(2026, 6, "NUT", 80, ["Kaleem", "Naeem"])
        assert "Excluded" in result
        assert "Kaleem" in result
        assert "Naeem" in result

    def test_rejection_unknown_product(self):
        result = log_rejection(2026, 6, "FAKE", 80)
        assert "Unknown product" in result

    def test_rejection_distribution_even(self):
        log_rejection(2026, 6, "NUT", 80)
        dist = get_distribution_for_month(2026, 6)
        assert len(dist) == 1
        assert dist[0]["product_code"] == "NUT"
        assert sum(dist[0]["distribution"].values()) == 80
        # 80 / 8 = 10 each
        for v in dist[0]["distribution"].values():
            assert v == 10

    def test_rejection_distribution_uneven(self):
        log_rejection(2026, 6, "NUT", 10)
        dist = get_distribution_for_month(2026, 6)
        total = sum(dist[0]["distribution"].values())
        assert total == 10

    def test_rejection_with_excluded_distribution(self):
        log_rejection(2026, 6, "NUT", 70, ["Kaleem", "Naeem"])
        dist = get_distribution_for_month(2026, 6)
        d = dist[0]["distribution"]
        assert "Kaleem" not in d
        assert "Naeem" not in d
        assert "Akbar" in d
        assert len(d) == 6  # 8 - 2 excluded
        assert sum(d.values()) == 70

    def test_multiple_rejections(self):
        log_rejection(2026, 6, "NUT", 80)
        log_rejection(2026, 6, "10*20", 40)
        dist = get_distribution_for_month(2026, 6)
        assert len(dist) == 2
        codes = {d["product_code"] for d in dist}
        assert codes == {"NUT", "10*20"}


class TestRecordAdvance:
    def test_advance_basic(self):
        result = record_advance("Kaleem", 5000, 2026, 6, "Personal loan")
        assert "Advance recorded" in result
        assert "Kaleem" in result
        assert "5,000" in result or "5000" in result

    def test_advance_new_worker_auto_create(self):
        result = record_advance("NewWorker", 2000, 2026, 6)
        assert "NewWorker" in result

    def test_advance_total_tracking(self):
        record_advance("Kaleem", 3000, 2026, 6)
        record_advance("Kaleem", 2000, 2026, 6)
        from tools.database import get_total_advances_for_worker_month, get_worker_id
        wid = get_worker_id("Kaleem")
        total = get_total_advances_for_worker_month(wid, 2026, 6)
        assert total == 5000.0

    def test_advance_summary_empty(self):
        summary = get_advances_summary(2026, 6)
        assert "No advances" in summary

    def test_advance_summary_with_data(self):
        record_advance("Kaleem", 5000, 2026, 6)
        record_advance("Naeem", 3000, 2026, 6)
        summary = get_advances_summary(2026, 6)
        assert "Kaleem" in summary
        assert "Naeem" in summary
        assert "8,000" in summary or "8000" in summary
