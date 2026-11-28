"""Bước kiểm số của agent (HU-8): mỗi con số trong "việc nên làm" chỉ cần một cách đọc có nguồn."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codebase"))
import agent  # noqa: E402


def unsourced(text, pool):
    return [max(r) for r in agent.token_readings(text) if not any(agent._found(x, pool) for x in r)]


class TestActionNumbers(unittest.TestCase):
    pool = agent.numbers_in({"cap_vnd": 50000, "gain": 7560, "rate": 10, "new_rate": 6, "price": 249000})

    def test_dau_cham_hang_nghin_khong_bi_coi_la_so_bia(self):
        self.assertEqual(unsourced("Voucher Xtra đang chạm trần 50.000đ, giá 249.000đ", self.pool), [])

    def test_ti_le_va_tien(self):
        self.assertEqual(unsourced("Hạ hoa hồng từ 10% xuống 6%, thêm 7.560đ mỗi đơn", self.pool), [])

    def test_so_bia_van_bi_bat(self):
        self.assertEqual(unsourced("Thêm 12.345đ mỗi đơn", self.pool), [12345.0])


if __name__ == "__main__":
    unittest.main()
