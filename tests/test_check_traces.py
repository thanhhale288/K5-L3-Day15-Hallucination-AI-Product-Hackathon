"""Test scripts/check_traces.py (TH-8): bộ kiểm phải BẮT được trace thiếu / sai, không chỉ báo ĐẠT."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "codebase"))

import check_traces as C  # noqa: E402
import schema  # noqa: E402

NAMES = C.tool_names()


def _final(cid, **kw):
    r = schema.agent_result(decision="act", platform="shopee", trace_id=cid, **kw)
    return {"kind": "final", "output": json.dumps(r, ensure_ascii=False), "error": ""}


def _model(model="gpt-x", ti=120, to=40):
    return {"kind": "model", "name": "call_model", "model": model, "tokens_in": ti, "tokens_out": to}


class CheckTracesTest(unittest.TestCase):
    def test_good_case(self):
        ev = [_model(), {"kind": "note", "text": "kế hoạch: 1 đơn"},
              {"kind": "tool", "name": "check_lines_sum", "input": "()", "output": "{}"},
              _final("B01", payout=123520, cogs=95000, profit=28520)]
        err, warn, info = C.check_case("B01", ev, NAMES)
        self.assertEqual((err, warn), ([], []))
        self.assertEqual((info["model_calls"], info["tool_calls"], info["tokens_in"]), (1, 1, 120))

    def test_catches_problems(self):
        ev = [_model(ti=0, to=0), {"kind": "tool", "name": "gui_tin_nhan", "input": "()", "output": "{}"},
              {"kind": "tool", "name": "lookup_fee_rule", "input": "()", "error": "KeyError: x"}, _final("B99")]
        err, warn, _ = C.check_case("B01", ev, NAMES)
        text = " ".join(err + warn)
        self.assertIn("L2", text)           # trace_id khác mã câu
        self.assertIn("gui_tin_nhan", text)  # công cụ lạ
        self.assertIn("KeyError", text)      # công cụ lỗi
        self.assertIn("token 0", text)       # model thật mà token 0
        self.assertIn("kế hoạch", text)      # thiếu note kế hoạch

    def test_missing_final_and_bad_shape(self):
        err, _, _ = C.check_case("B01", [_model(), {"kind": "note", "text": "kế hoạch"}], NAMES)
        self.assertTrue(any(e.startswith("L1 thiếu") for e in err))
        bad = {"kind": "final", "output": json.dumps({"decision": "act", "la": 1}), "error": ""}
        err, _, _ = C.check_case("B01", [bad], NAMES)
        self.assertTrue(any(e.startswith("L1 H4") for e in err))

    def test_code_refusal_needs_no_model(self):
        ev = [{"kind": "note", "text": "refuse ở bước lọc (code)"},
              {"kind": "final", "output": json.dumps(schema.agent_result(decision="refuse", refusal_reason="né phí",
                                                                         trace_id="T1")), "error": ""}]
        self.assertEqual(C.check_case("T1", ev, NAMES)[:2], ([], []))


if __name__ == "__main__":
    unittest.main()
