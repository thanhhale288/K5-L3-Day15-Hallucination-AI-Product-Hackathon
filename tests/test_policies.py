"""Test kho chính sách: effective_date mức chunk phải có căn cứ trong chính text. Chạy: python -m unittest discover -s tests"""
import csv
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "policies"))

from clean import chunk_effective_date  # noqa: E402

POL = os.path.join(ROOT, "data", "policies")


class TestChunkEffectiveDate(unittest.TestCase):
    def test_single_date(self):
        d, q = chunk_effective_date("Khoản phí này sẽ bắt đầu được thu từ ngày 27 tháng 10 năm 2025, giờ Việt Nam.")
        self.assertEqual(d, "2025-10-27")
        self.assertIn("27 tháng 10 năm 2025", q)
        self.assertEqual(chunk_effective_date("Có hiệu lực từ ngày **01/07/2025**.")[0], "2025-07-01")

    def test_multi_period_is_skipped(self):
        # bảng nhiều kỳ: gán một ngày sẽ giấu mức phí cũ khỏi đơn đặt trước ngày đó
        t = "Phí suất từ ngày 20/10/2026 | Nhà bán hàng Mall · Từ 3-08-2026: 15.0% | Từ 20-10-2026: 12.5%"
        self.assertEqual(chunk_effective_date(t), (None, None))
        self.assertEqual(chunk_effective_date("Áp dụng từ 01/05/2026, trước đó (đến 30/04/2026) là 4,91%."), (None, None))

    def test_no_date_no_guess(self):
        self.assertEqual(chunk_effective_date("Phí Xử Lý Giao Dịch áp dụng cho mọi đơn thành công."), (None, None))
        self.assertEqual(chunk_effective_date("Cập nhật 2026-11-27. Updated at 27/11/2026"), (None, None))


class TestEvidenceFile(unittest.TestCase):
    def test_every_filled_date_has_quote_in_chunk(self):
        with open(os.path.join(POL, "chunks.jsonl"), encoding="utf-8") as f:
            ch = {c["chunk_id"]: c for c in map(json.loads, f)}
        with open(os.path.join(POL, "effective_date_evidence.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(rows)
        for r in rows:
            c = ch.get(r["chunk_id"])
            if c is None:            # chunk trùng nội dung đã bị merge.py bỏ, căn cứ vẫn nằm ở kho sàn
                continue
            self.assertEqual(c["effective_date"], r["effective_date"], r["chunk_id"])
            self.assertIn(r["can_cu"], " ".join(c["text"].split()), r["chunk_id"])
            self.assertEqual(chunk_effective_date(c["text"])[0], r["effective_date"], r["chunk_id"])


if __name__ == "__main__":
    unittest.main()
