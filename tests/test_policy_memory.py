"""Hỏi đáp chính sách (PolicyAnswer) và trí nhớ hội thoại của agent (Hà, 28/11). Không gọi model."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "codebase"))
import agent  # noqa: E402
import schema  # noqa: E402

HIT = {"chunk_id": "shopee-27540#020", "url": "https://banhang.shopee.vn/x", "effective_date": "2026-05-23",
       "text": "Phí Voucher Xtra 5.5% giá trị mỗi sản phẩm, tối đa 50.000Đ/sản phẩm.", "score": 0.9}
HISTORY = [{"step": {"tools": [{"tool": "search_policy", "args": {"query": "voucher xtra", "platform": "shopee"}}]},
            "results": [{"tool": "search_policy", "output": [HIT]}]}]


def final(answer, citations):
    return {"policy_answer": {"answer": answer, "citations": citations}}


class PolicyAnswerTest(unittest.TestCase):
    def test_dung_doan_trich_thi_hop_le(self):
        r, problems = agent._policy_result(final("Shopee: Voucher Xtra 5.5%, tối đa 50.000đ mỗi sản phẩm.", [HIT["chunk_id"]]),
                                           HISTORY, "t1")
        self.assertEqual(problems, [])
        self.assertEqual(schema.validate_policy_answer(r), [])
        self.assertEqual(r["citations"][0]["platform"], "shopee")       # sàn lấy từ lời gọi search_policy
        self.assertEqual(r["citations"][0]["url"], HIT["url"])          # url lấy từ output công cụ, không từ model

    def test_bat_chunk_khong_co_trong_ket_qua_tim(self):
        _, problems = agent._policy_result(final("Shopee: 5.5%.", ["shopee-bia#001"]), HISTORY, "t1")
        self.assertTrue(any("không có trong output search_policy" in p for p in problems))

    def test_bat_so_khong_co_trong_doan_trich(self):
        _, problems = agent._policy_result(final("Shopee: Voucher Xtra 7%, tối đa 80.000đ.", [HIT["chunk_id"]]), HISTORY, "t1")
        self.assertTrue(any("không có trong đoạn chính sách" in p for p in problems))

    def test_fallback_tra_nguyen_doan_trich(self):
        r = agent._policy_fallback(HISTORY, "t1")
        self.assertEqual(schema.validate_policy_answer(r), [])
        self.assertIn("50.000", r["answer"])
        self.assertEqual(r["citations"][0]["chunk_id"], HIT["chunk_id"])
        empty = agent._policy_fallback([], "t1")
        self.assertEqual(empty["citations"], [])


class MemoryTest(unittest.TestCase):
    def test_tin_nhan_cu_la_bang_chung_ket_qua_cu_thi_khong(self):
        memory = [{"user": "Phí cố định: -17.010đ", "agent": "act shopee DEMO-0412 · lãi 28520"}]
        block, user_text = agent._memory_block(memory)
        self.assertIn("HỘI THOẠI TRƯỚC", block)
        self.assertIn("17.010", user_text)        # chữ dán cũ của chủ shop: được coi là dữ liệu đầu vào
        self.assertNotIn("28520", user_text)      # số trong kết quả cũ của agent: không phải bằng chứng

    def test_khong_co_tri_nho_thi_khong_them_gi(self):
        self.assertEqual(agent._memory_block(None), ("", ""))

    def test_giu_toi_da_so_luot(self):
        memory = [{"user": "câu %d" % i, "agent": ""} for i in range(agent.MEMORY_TURNS + 3)]
        block, _ = agent._memory_block(memory)
        self.assertNotIn("câu 0", block)
        self.assertIn("câu %d" % (agent.MEMORY_TURNS + 2), block)

    def test_tom_tat_ket_qua(self):
        pa = schema.policy_answer("Voucher Xtra 5.5%.", [dict(HIT, platform="shopee")], "t1")
        self.assertIn("trả lời chính sách", agent.memory_summary(pa))
        order = schema.agent_result(decision="act", platform="shopee", order_id="DEMO-0412", profit=28520, cogs=95000)
        self.assertIn("DEMO-0412", agent.memory_summary(order))


if __name__ == "__main__":
    unittest.main()
