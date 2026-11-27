"""Test thân hàm công cụ (TH-5). Chạy: python -m unittest discover -s tests

- Đơn mẫu H4 (TASK.md) phải ra tiền về 123.520, lãi 28.520.
- lookup_fee_rule / expected_amount khớp đáp án dòng của data giả (data/synthetic/line_answers.csv) —
  cùng bảng phí data/fee_rules.csv, nên tool và đáp án không được lệch nhau.
- Lọc cứng theo sàn: không trả luật / đoạn chính sách của sàn khác.
Không gọi API: search_policy chạy bằng BM25 (vector bị tắt trong test).
"""
import csv
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "codebase"))

import retrieval  # noqa: E402
import tools as T  # noqa: E402

SYN = os.path.join(ROOT, "data", "synthetic")

# Đơn mẫu H4: giá 199.000, voucher shop −10.000 → căn cứ 189.000
H4_DATE, H4_BASE = "2026-11-12", 189_000
H4_LINES = [("Phí cố định", -17_010), ("Phí xử lý giao dịch", -11_340), ("Phí Voucher Xtra", -10_395),
            ("Phí tiếp thị liên kết", -18_900), ("Phí hạ tầng", -3_000), ("Thuế khấu trừ (GTGT + TNCN)", -2_835),
            ("Phí dịch vụ khác", -2_000)]


def _no_vectors(*a, **k):
    raise RuntimeError("test không gọi API embedding")


class TestH4Sample(unittest.TestCase):
    def setUp(self):
        self.lines = []
        for name, amt in H4_LINES:
            r = T.lookup_fee_rule(name, H4_DATE, "shop_thuong", "thoi_trang", "shopee")
            line = {"name": name, "amount": amt, "type": r["loai"] if r else "khong_khop",
                    "rule_id": r and r["rule_id"]}
            if r:
                e = T.expected_amount(r["rule_id"], H4_BASE, amt, 1,
                                      shop_rate=10.0 if r["base"] == "theo_shop" else None)
                line["expected"], line["delta"] = e["expected"], e["delta"]
            self.lines.append(line)

    def test_rules_and_amounts(self):
        by = {x["name"]: x for x in self.lines}
        self.assertIsNone(by["Phí dịch vụ khác"]["rule_id"])
        self.assertEqual(by["Phí Voucher Xtra"]["rule_id"], "shopee_voucher_xtra_2026-05-23")
        self.assertEqual(by["Phí xử lý giao dịch"]["rule_id"], "shopee_phi_xu_ly_giao_dich_shop_thuong_2026-05-01")
        for x in self.lines:
            if x["rule_id"]:
                self.assertEqual(x["delta"], 0, x)

    def test_sum_and_profit(self):
        all_lines = [{"name": "Giá bán", "amount": 199_000}, {"name": "Voucher shop", "amount": -10_000}] + self.lines
        s = T.check_lines_sum(all_lines, 123_520)
        self.assertTrue(s["ok"], s)
        p = T.unit_profit(H4_BASE, self.lines, 95_000)
        self.assertEqual(p["payout"], 123_520)
        self.assertEqual(p["profit"], 28_520)
        self.assertEqual([x["name"] for x in p["switches"]], ["Phí tiếp thị liên kết", "Phí Voucher Xtra"])
        self.assertAlmostEqual(p["switches"][0]["share_of_profit"], 0.663, places=3)

    def test_switch_what_if(self):
        new = T.expected_amount("shopee_tiep_thi_lien_ket_2026-01-01", H4_BASE, shop_rate=6.0)["expected"]
        w = T.switch_what_if(self.lines, "Phí tiếp thị liên kết", new, 28_520)
        self.assertEqual(w["gain_per_order"], 7_560)          # khớp actions[0] trong mẫu H4
        self.assertEqual(w["profit_after"], 36_080)
        self.assertAlmostEqual(w["max_order_drop_pct"], 21.0, places=1)

    def test_missing_cogs(self):
        self.assertIn("error", T.unit_profit(H4_BASE, self.lines, None))


class TestLookup(unittest.TestCase):
    def test_old_name_by_date(self):
        before = T.lookup_fee_rule("Phí thanh toán", "01/03/2026", "shop_thuong", "Thời trang", "shopee")
        after = T.lookup_fee_rule("Phí thanh toán", "2026-11-12", "shop_thuong", "thoi_trang", "shopee")
        self.assertEqual(before["rule_id"], "shopee_phi_thanh_toan_2026-01-01")
        self.assertEqual(after["fee_key"], "phi_xu_ly_giao_dich")
        self.assertEqual(after["matched_by"], "ten_cu")

    def test_rate_changes_on_date(self):
        a = T.lookup_fee_rule("Phí giao dịch", "2026-05-08", "shop_thuong", "my_pham", "tiktok")
        b = T.lookup_fee_rule("Phí giao dịch", "2026-05-09", "shop_thuong", "my_pham", "tiktok")
        self.assertEqual((a["rate"], b["rate"]), (5.0, 6.0))

    def test_platform_isolation(self):
        self.assertIsNone(T.lookup_fee_rule("Phí giao dịch", "2026-11-12", "shop_thuong", "my_pham", "shopee"))
        self.assertIsNone(T.lookup_fee_rule("Phí Voucher Xtra", "2026-11-12", "shop_thuong", "my_pham", "tiktok"))
        self.assertIsNone(T.lookup_fee_rule("Phí cố định", "2026-11-12", "shop_thuong", "my_pham", "amazon"))
        lz = T.lookup_fee_rule("Phí thanh toán", "2026-11-12", "shop_thuong", "my_pham", "lazada")
        self.assertEqual(lz["platform"], "lazada")

    def test_unknown_and_lookalike(self):
        for name in ("Phí xử lý khác", "Phí điều chỉnh", "Khấu trừ khác", ""):
            self.assertIsNone(T.lookup_fee_rule(name, "2026-11-12", "shop_thuong", "my_pham", "shopee"), name)

    def test_tiktok_order_processing_fee(self):
        r = T.lookup_fee_rule("Phí xử lý đơn hàng", "2026-11-12", "shop_thuong", "my_pham", "tiktok")
        self.assertEqual(r["da_doi_chieu"], "chinh_thuc")
        self.assertEqual(T.expected_amount(r["rule_id"], 0)["expected"], -3_000)

    def test_cap(self):
        e = T.expected_amount("shopee_voucher_xtra_2026-05-23", 2_000_000, -60_000)
        self.assertEqual((e["expected"], e["delta"], e["capped"]), (-50_000, -10_000, True))
        e2 = T.expected_amount("shopee_voucher_xtra_2026-05-23", 2_000_000, qty=3)   # trần 50.000 × 3 sp
        self.assertEqual((e2["expected"], e2["capped"]), (-110_000, False))

    def test_theo_shop_needs_rate(self):
        self.assertIn("error", T.expected_amount("shopee_tiep_thi_lien_ket_2026-01-01", 189_000))
        self.assertIn("error", T.expected_amount("khong_co_luat_nay", 1))


class TestAgainstSyntheticAnswers(unittest.TestCase):
    """Mọi dòng có luật trong đáp án data giả: lookup ra đúng rule_id, expected_amount ra đúng số."""

    def test_all_lines(self):
        with open(os.path.join(SYN, "orders.csv"), encoding="utf-8") as f:
            orders = {o["order_id"]: o for o in csv.DictReader(f)}
        with open(os.path.join(SYN, "line_answers.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        checked = 0
        for x in rows:
            if not x["rule_id"]:
                r = T.lookup_fee_rule(x["ten_dong"], orders[x["order_id"]]["order_date"], "shop_thuong", "*",
                                      orders[x["order_id"]]["platform"])
                self.assertIsNone(r, x)                     # dòng lạ không được gán luật
                continue
            o = orders[x["order_id"]]
            r = T.lookup_fee_rule(x["ten_dong"], o["order_date"], o["shop_type"], o["nganh"], o["platform"])
            self.assertIsNotNone(r, x)
            self.assertEqual(r["rule_id"], x["rule_id"], x)
            if r["base"] in ("theo_shop", "voucher_dong_tai_tro"):
                continue                                     # căn cứ / tỉ lệ không có trong orders.csv
            base = int(o["gia_ban"]) * int(o["qty"]) - int(o["voucher_shop"] or 0)
            e = T.expected_amount(r["rule_id"], base, int(x["amount_vnd"]), int(o["qty"]))
            self.assertEqual(e["expected"], int(x["expected_vnd"]), x)
            self.assertEqual(e["delta"], int(x["delta_vnd"]), x)
            checked += 1
        self.assertGreater(checked, 900)


class TestCompare(unittest.TestCase):
    def test_compare_platforms(self):
        orders = [
            {"platform": "shopee", "order_id": "A", "product": "SP-031", "price": 189_000, "qty": 1,
             "lines": [{"name": "Phí cố định", "amount": -17_010, "type": "bat_buoc"},
                       {"name": "Phí tiếp thị liên kết", "amount": -18_900, "type": "cong_tac"}]},
            {"platform": "tiktok", "order_id": "B", "product": "SP-031", "price": 378_000, "qty": 2,
             "lines": [{"name": "Phí giao dịch", "amount": -22_680, "type": "bat_buoc"},
                       {"name": "Phí Voucher Extra", "amount": -18_900, "type": "cong_tac"}]},
        ]
        c = T.compare_platforms(orders, 95_000)
        self.assertEqual([r["profit"] for r in c["rows"]], [58_090, 146_420])
        self.assertEqual(c["best_platform"], "tiktok")
        self.assertEqual(c["rows"][0]["top_switch"], "Phí tiếp thị liên kết")
        self.assertIn("error", T.compare_platforms(orders[:1], 95_000))

    def test_breakeven(self):
        self.assertEqual(T.breakeven_roas(0.25)["breakeven_roas"], 4.0)
        self.assertEqual(T.breakeven_roas(25)["breakeven_roas"], 4.0)
        self.assertIsNone(T.breakeven_roas(0)["breakeven_roas"])


class TestSearchPolicy(unittest.TestCase):
    def setUp(self):
        self._orig = retrieval.embed_texts
        retrieval.embed_texts = _no_vectors

    def tearDown(self):
        retrieval.embed_texts = self._orig

    def test_platform_filter_and_date(self):
        for plat, q in (("shopee", "phí xử lý giao dịch"), ("tiktok", "phí giao dịch"), ("lazada", "phí cố định LazMall")):
            hits = T.search_policy(q, plat, "2026-11-12")
            self.assertTrue(hits, plat)
            self.assertTrue(all(h["chunk_id"].startswith(plat + "-") for h in hits), hits)
            self.assertTrue(all(not h["effective_date"] or h["effective_date"] <= "2026-11-12" for h in hits))
        # đoạn LazMall hiệu lực 04/06/2026 không được trả cho đơn đặt trước ngày đó
        early = T.search_policy("phí cố định LazMall", "lazada", "2026-05-01")
        self.assertFalse(any(h["effective_date"] == "2026-06-04" for h in early))

    def test_no_guess(self):
        self.assertEqual(T.search_policy("cách nấu phở bò", "shopee", "2026-11-12"), [])
        self.assertEqual(T.search_policy("phí giao dịch", "amazon", "2026-11-12"), [])

    def test_fee_rules_chunks_exist_on_same_platform(self):
        import json
        with open(os.path.join(ROOT, "data", "policies", "chunks.jsonl"), encoding="utf-8") as f:
            plat = {c["chunk_id"]: c["platform"] for c in map(json.loads, f)}
        for r in T._rules():
            if r.get("chunk_id"):
                self.assertEqual(plat.get(r["chunk_id"]), r["platform"], r["rule_id"])


if __name__ == "__main__":
    unittest.main()
