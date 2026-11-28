"""Luồng chính "Lãi đi đâu?" (Huy giữ). Đúng hình dạng spec.md §4: agent có giới hạn, đa sàn.

  lọc yêu cầu (code) → agent lập kế hoạch → vòng công cụ (≤ 8 lượt / đơn, ≤ 20 lượt / phiên)
  → bước kiểm (mọi số có trong output công cụ hoặc chữ dán, mọi rule_id / chunk_id do công cụ trả)
  → sai thì agent sửa 1 lần → vẫn sai thì fallback (chỉ bảng dòng) → AgentResult / SessionResult (H4, codebase/schema.py)

Hợp đồng với khung: answer(text) -> {"output": str JSON của AgentResult hoặc SessionResult, "result": dict}.
API của Thái (TH-7) gọi answer(text, session_state_id=...) để trả lời một câu Ask mà không tách lại từ đầu.

Giao thức với model: mỗi lượt model trả đúng MỘT object JSON (xem codebase/prompt.py):
  {"plan": …} · {"tools": [{"tool", "args"}, …]} · {"final": …}
AI giả (MODEL_PROVIDER trống / fake): vẫn gọi call_model mỗi lượt, nhưng bước tiếp lấy từ kịch bản cố định của
đơn mẫu DEMO-0412 (_fake_step). Mọi phần còn lại của vòng lặp (gọi công cụ, giới hạn, bước kiểm, ghép JSON) chạy thật.
"""
import inspect
import json
import re
import uuid

import ai
import schema
from ai import call_model
from prompt import SYSTEM as SYSTEM_BASE
from tools import TOOLS
from tracing import note

MAX_TURNS_PER_ORDER = 8      # lượt gọi công cụ (một lượt có thể gồm nhiều lời gọi độc lập)
MAX_TURNS_PER_SESSION = 20
MAX_CALLS_PER_ORDER = 40     # trần an toàn số lời gọi lẻ
MAX_ORDERS = 5
MAX_STEPS = MAX_TURNS_PER_SESSION + 4   # + lập kế hoạch, kết thúc, 1 lần sửa, 1 lần nhắc định dạng
RESULT_PREVIEW = 1500        # ký tự tối đa của mỗi output công cụ đưa lại cho model

SESSIONS = {}                # session_state_id → {"text", "history"} (trong bộ nhớ; API giữ tiến trình sống)

# ── Lọc yêu cầu bằng code (HU-9). Lớp 1 trước model; lớp 2 là luật refuse trong prompt.
# Mẫu theo KIỂU tấn công / yêu cầu xấu, không so khớp nguyên văn câu thử (AGENTS.md). ──
_SHOP = r"(shop|gian hàng|người bán|nhà bán( hàng)?|cửa hàng)"
_SCREEN = [
    ("lenh_chen",
     r"\[\s*(admin|system|sys|hệ thống|quản trị|developer|dev|root)\s*\]"                       # thẻ vai giả
     r"|(lưu ý|ghi chú|chú ý|note|nhắn|gửi)\s*(cho|tới|đến)?\s*(ai|agent|trợ lý|bot|chatbot|model|assistant)\b"
     r"|\b(ai|agent|trợ lý|bot|chatbot|model|assistant)\s*(ơi|hãy|phải|cần phải|:)"            # nói thẳng với trợ lý
     r"|(bỏ qua|quên|phớt lờ|ignore|disregard)\s*(hết|mọi|tất cả|các|những|all|any|the|previous)?\s*"
     r"(hướng dẫn|chỉ dẫn|lệnh|quy tắc|luật|instructions?|rules?)"
     r"|(in|hiện|hiển thị|tiết lộ|cho xem|xuất|nhắc lại|reveal|print|show)\s.{0,40}"
     r"(hướng dẫn|chỉ dẫn|prompt|lệnh)\s*(hệ thống|gốc|ban đầu|system)|system prompt|prompt hệ thống"
     r"|coi\s*(mọi|tất cả|các|những|toàn bộ)\s*(khoản|dòng|phí).{0,40}(đúng|hợp lệ|khớp)"     # ép kết luận
     r"|(không|đừng|khỏi)\s*(cần\s*)?(soạn|gửi|tạo|viết|báo)\s.{0,25}(câu hỏi|nháp|khiếu nại|cho sàn|gửi sàn)"
     r"|(bỏ qua|không cần|đừng|khỏi)\s*(bước\s*)?kiểm"
     r"|(trả|đặt|ghi|chọn|set)\s*(về\s*)?(decision|quyết định)\s*(là\s*)?(act|ask|escalate|refuse)",
     "Chữ dán có câu ra lệnh cho trợ lý (lệnh chèn). Mình chỉ đọc chữ dán như dữ liệu đơn hàng, không làm theo."),
    ("ne_phi_thue",
     r"\bné\s*(phí|thuế)|trốn\s*(thuế|phí)|lách\s*(phí|thuế|luật)"
     r"|(khai|báo|ghi|kê)\s*(giá|doanh thu|doanh số|giá trị)\s.{0,25}(thấp|ít|giảm|nhỏ)"
     r"|(thuế|khấu trừ).{0,30}(ít hơn|thấp hơn|khỏi phải|không phải)\s*(nộp|đóng|trả|bị)?"
     r"|(làm sao|làm thế nào|cách|mẹo|bí kíp).{0,50}(không phải|khỏi|đỡ phải|tránh|né)\s*(nộp|đóng|bị trừ|trả|mất)\s*(thuế|phí)"
     r"|(chuyển khoản|thanh toán|giao dịch|mua bán|trả tiền)\s.{0,20}(riêng|ngoài sàn|bên ngoài|không qua sàn)",
     "Mình không hỗ trợ né phí sàn hay giảm thuế phải nộp. Mình chỉ giúp hiểu đúng từng khoản phí và lãi thật trên đơn."),
    ("don_review_ao",
     r"(đơn|order)\s*(ảo|giả|fake)|(review|đánh giá|bình luận|feedback|sao)\s.{0,15}(giả|ảo|fake)"
     r"|(tự mua|tự đặt)\s.{0,20}(tự\s*)?(đánh giá|review)|(buff|seeding|cày)\s*(đơn|đánh giá|review|sao|lượt)",
     "Mình không hỗ trợ tạo đơn ảo hay đánh giá giả: vi phạm chính sách sàn và có thể khiến shop bị khoá."),
    ("du_lieu_nguoi_khac",
     _SHOP + r"\s*(đối thủ|khác|cạnh tranh|của người khác)|\bđối thủ\b"
     r"|(lấy|xin|gửi|cho|xem|tra|tìm)\s.{0,20}(số điện thoại|sđt|địa chỉ|thông tin cá nhân|email)\s*(của\s*)?(khách|người mua)",
     "Mình chỉ soi đơn của chính shop bạn, không xem hay cung cấp dữ liệu của shop khác hoặc thông tin cá nhân của khách."),
    ("gian_lan_hoan",
     r"hoàn\s*(hàng|tiền).{0,50}(vẫn giữ|giữ (lại )?hàng|không (trả|gửi)( lại)? hàng)"
     r"|(đòi|lấy|kiếm)\s*lại\s*tiền\s*phí|(khiếu nại|báo cáo|tố cáo)\s*(giả|ảo|láo|bừa)|gian lận|hoàn hàng (giả|ảo)",
     "Mình không hỗ trợ gian lận hoàn hàng hay khiếu nại sai sự thật."),
]
_SCREEN = [(name, re.compile(rx, re.I), reason) for name, rx, reason in _SCREEN]


def screen_request(text: str):
    """Lý do từ chối nếu chữ dán có lệnh chèn hoặc yêu cầu xấu, không thì None. Ghi nhóm vào trace."""
    for name, rx, reason in _SCREEN:
        m = rx.search(text or "")
        if m:
            note("lọc yêu cầu: %s (\"%s\")" % (name, m.group(0)[:60]))
            return reason
    return None


# ── Danh sách công cụ cho prompt: lấy từ chữ ký + docstring trong tools.py (một nguồn) ──
# Chỉ 10 công cụ của hợp đồng H3; hàm khác trong tools.py (vd search_example của khung) không đưa cho model.
H3_TOOLS = ("check_lines_sum", "lookup_fee_rule", "search_policy", "expected_amount", "unit_profit",
            "switch_what_if", "breakeven_roas", "compare_platforms", "ask_user", "draft_platform_question")


def tool_catalog() -> str:
    parts = []
    for name, fn in ((n, TOOLS[n]) for n in H3_TOOLS if n in TOOLS):
        target = getattr(fn, "__wrapped__", fn)
        doc = inspect.getdoc(target) or ""
        parts.append("- %s%s\n  %s" % (name, inspect.signature(target), doc.replace("\n", "\n  ")))
    return "\n## Công cụ\n" + "\n".join(parts)


SYSTEM = SYSTEM_BASE + tool_catalog()


# ── Số trong chữ: "1.269.000", "20k", "-17.010đ", "5,5%" ──
_NUM = re.compile(r"(?<![\w.])-?\d{1,3}(?:[.,]\d{3})+(?![\d])|(?<![\w.])-?\d+(?:[.,]\d+)?(?:\s?k\b)?", re.I)


def token_readings(text: str) -> list:
    """Mỗi con số trong chữ → tập các cách đọc của nó. "50.000" đọc được là 50000 hoặc 50 (dấu chấm thập phân),
    "5,5" là 55 hoặc 5.5. Bước kiểm chỉ cần MỘT cách đọc có nguồn, không đòi mọi cách đọc."""
    out = []
    for tok in _NUM.findall(text):
        t = tok.lower().replace(" ", "").lstrip("-")
        mult = 1000 if t.endswith("k") else 1
        t = t.rstrip("k")
        r = {float(re.sub(r"[.,]", "", t)) * mult}                  # 1.269.000 → 1269000
        if t.count(".") + t.count(",") == 1:
            r.add(float(t.replace(",", ".")) * mult)                # 5,5 → 5.5
        out.append(r)
    return out


def numbers_in(value) -> set:
    """Mọi con số (giá trị tuyệt đối) xuất hiện trong value: số, chuỗi, list, dict lồng nhau."""
    out = set()
    if isinstance(value, bool) or value is None:
        return out
    if isinstance(value, (int, float)):
        out.add(abs(float(value)))
    elif isinstance(value, str):
        for readings in token_readings(value):
            out |= readings
    elif isinstance(value, dict):
        for v in value.values():
            out |= numbers_in(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            out |= numbers_in(v)
    return out


def _found(x, pool) -> bool:
    x = abs(float(x))
    tol = 1.0 if x >= 1 else 0.0015
    return any(abs(x - p) <= tol for p in pool)


STEP_KEYS = ("plan", "tools", "tool", "final")


def parse_step(text: str):
    """Object JSON NGOÀI CÙNG có khoá giao thức (plan / tools / tool / final), hoặc None.
    Chỉ xét object cấp cao nhất: JSON bị cắt cụt (model chạm trần token) trả None, không vớ nhầm object con."""
    if not text:
        return None
    t = re.sub(r"```(?:json)?", "", text).strip()
    i, n = 0, len(t)
    while i < n:
        start = t.find("{", i)
        if start == -1:
            return None
        depth, in_str, esc, end = 0, False, False, None
        for j in range(start, n):
            c = t[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end is None:          # chưa đóng ngoặc: bị cắt cụt
            return None
        try:
            obj = json.loads(t[start:end + 1])
        except ValueError:
            obj = None
        if isinstance(obj, dict) and any(k in obj for k in STEP_KEYS):
            return obj
        i = end + 1              # bỏ qua cả object này (kể cả object con bên trong), xét object kế tiếp
    return None


_PLATFORM_ALIASES = {"shopee": "shopee", "tiktok": "tiktok", "tiktok shop": "tiktok", "tiktokshop": "tiktok",
                     "lazada": "lazada"}


_SHOP_TYPE_ALIASES = {"thuong": "shop_thuong", "shop thuong": "shop_thuong", "shop_thuong": "shop_thuong",
                      "thường": "shop_thuong", "shop thường": "shop_thuong", "mall": "mall", "shopee mall": "mall",
                      "lazmall": "mall", "tiktok shop mall": "mall"}
SHOP_TYPES = ("shop_thuong", "mall")
CATEGORIES = ("thoi_trang", "my_pham", "dien_tu", "nha_cua", "me_be", "thuc_pham")


def _strip_accents(s):
    import unicodedata
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm_category(v):
    """'Thời trang' / 'Điện tử & phụ kiện' / 'thoi_trang' → mã ngành của data/fee_engine.CATEGORIES."""
    if not isinstance(v, str):
        return v
    k = _strip_accents(v).lower().replace("_", " ")
    for code, words in (("thoi_trang", "thoi trang"), ("my_pham", "my pham"), ("dien_tu", "dien tu"),
                        ("nha_cua", "nha cua"), ("me_be", "me"), ("thuc_pham", "thuc pham")):
        if (k.startswith(words) if code == "me_be" else words in k):
            return code
    return v


def _norm_args(args):
    """Chuẩn hoá tham số liệt kê trước khi gọi công cụ (model hay truyền "Shopee", "thuong", "Thời trang")."""
    if isinstance(args, list):
        return [_norm_args(a) for a in args]
    if not isinstance(args, dict):
        return args
    out = {}
    for k, v in args.items():
        if k == "platform":
            v = _norm_enum(v, schema.PLATFORMS, _PLATFORM_ALIASES)
        elif k == "shop_type":
            v = _norm_enum(v, SHOP_TYPES, _SHOP_TYPE_ALIASES)
        elif k == "category":
            v = _norm_category(v)
        elif isinstance(v, (dict, list)) and k == "orders":
            v = _norm_args(v)
        out[k] = v
    return out


def _norm_enum(v, allowed, aliases=None):
    """Chuẩn hoá chữ hoa / khoảng trắng của giá trị liệt kê (model hay trả "Shopee", "ACT")."""
    if not isinstance(v, str):
        return v
    k = " ".join(v.strip().lower().split())
    k = (aliases or {}).get(k, k)
    return k if k in allowed else v


# ── Kịch bản AI giả: đơn mẫu DEMO-0412 (TASK.md › H4), đi đủ các bước như một model thật ──
_DEMO_PLAN = {"orders": [{
    "order_id": "DEMO-0412", "platform": "shopee", "order_date": "2026-11-12", "shop_type": "shop_thuong",
    "category": "thoi_trang", "product": "SP-DEMO", "unit_price": 199000, "qty": 1, "voucher_shop": -10000,
    "lines": [{"name": "Phí cố định", "amount": -17010}, {"name": "Phí xử lý giao dịch", "amount": -11340},
              {"name": "Phí Voucher Xtra", "amount": -10395},
              {"name": "Phí tiếp thị liên kết", "amount": -18900, "rate": 10},
              {"name": "Phí hạ tầng", "amount": -3000}, {"name": "Thuế khấu trừ (GTGT + TNCN)", "amount": -2835},
              {"name": "Phí dịch vụ khác", "amount": -2000}],
    "payout": 123520, "cogs": 95000}],
    "steps": "1 đơn Shopee 12/11/2026: kiểm tổng → tra luật từng dòng → tính số đúng luật → lãi → công tắc → nháp hỏi sàn"}


def _fake_step(history: list) -> dict:
    """Bước tiếp theo của kịch bản, dựa trên số lượt đã làm và output công cụ đã có (như model đọc lại trace)."""
    o = _DEMO_PLAN["orders"][0]
    base = o["unit_price"] * o["qty"] + o["voucher_shop"]
    results = [r for h in history if "tools" in h["step"] for r in h["results"]]
    by_tool = lambda name: [r for r in results if r["tool"] == name]
    turn = sum(1 for h in history if "tools" in h["step"])
    if not history:
        return {"plan": _DEMO_PLAN}
    if turn == 0:
        calls = [{"tool": "check_lines_sum", "args": {"lines": [{"name": "Giá bán", "amount": o["unit_price"]},
                                                                 {"name": "Voucher shop", "amount": o["voucher_shop"]}]
                                                                + o["lines"], "payout": o["payout"]}}]
        calls += [{"tool": "lookup_fee_rule", "args": {"fee_name": ln["name"], "order_date": o["order_date"],
                                                       "shop_type": o["shop_type"], "category": o["category"],
                                                       "platform": o["platform"]}} for ln in o["lines"]]
        return {"tools": calls}
    if turn == 1:
        rules = [r["output"] for r in by_tool("lookup_fee_rule")]
        calls = []
        for ln, rule in zip(o["lines"], rules):
            if rule:
                args = {"rule_id": rule["rule_id"], "base_amount": base, "actual_amount": ln["amount"], "qty": o["qty"]}
                if rule["base"] == "theo_shop":
                    args["shop_rate"] = ln.get("rate")
                calls.append({"tool": "expected_amount", "args": args})
        return {"tools": calls}
    if turn == 2:
        rules = {r["output"]["rule_id"]: r["output"] for r in by_tool("lookup_fee_rule") if r["output"]}
        lines = _lines_from(o, by_tool("lookup_fee_rule"), by_tool("expected_amount"))
        aff = next(rid for rid, r in rules.items() if r["base"] == "theo_shop")
        return {"tools": [{"tool": "unit_profit", "args": {"price": base, "lines": lines, "cogs": o["cogs"]}},
                          {"tool": "expected_amount", "args": {"rule_id": aff, "base_amount": base, "qty": o["qty"],
                                                               "shop_rate": 6}}]}
    if turn == 3:
        lines = _lines_from(o, by_tool("lookup_fee_rule"), by_tool("expected_amount"))
        profit = by_tool("unit_profit")[0]["output"]
        top = profit["switches"][0]["name"]
        new_val = by_tool("expected_amount")[-1]["output"]["expected"]
        odd = next(ln for ln in lines if ln["type"] == "khong_khop")
        return {"tools": [{"tool": "switch_what_if", "args": {"lines": lines, "switch": top, "new_value": new_val,
                                                              "profit": profit["profit"]}},
                          {"tool": "draft_platform_question", "args": {"order_id": o["order_id"], "line": odd["name"],
                                                                       "expected": None, "actual": odd["amount"]}}]}
    lines = _lines_from(o, by_tool("lookup_fee_rule"), by_tool("expected_amount"))
    prof = by_tool("unit_profit")[0]["output"]
    what = by_tool("switch_what_if")[0]["output"]
    new_rate = by_tool("expected_amount")[-1]["output"]["rate"]
    old_rate = next(r["output"]["rate"] for r in by_tool("expected_amount") if r["output"]["rule_id"] ==
                    next(ln["rule_id"] for ln in lines if ln["name"] == what["switch"]))
    return {"final": {
        "decision": "escalate", "platform": o["platform"], "order_id": o["order_id"], "order_date": o["order_date"],
        "lines": lines, "payout": prof["payout"], "cogs": prof["cogs"], "profit": prof["profit"],
        "switches": prof["switches"],
        "actions": [{"text": "Hạ hoa hồng tiếp thị liên kết từ %g%% xuống %g%%" % (old_rate, new_rate),
                     "gain_per_order": what["gain_per_order"]}],
        "question": None, "draft_to_platform": by_tool("draft_platform_question")[0]["output"]["draft"],
        "refusal_reason": None}}


def _lines_from(o, lookups, expecteds):
    """Ghép Line (H4) từ output lookup_fee_rule + expected_amount, theo thứ tự dòng trên đơn."""
    exp = {r["output"]["rule_id"]: r["output"] for r in expecteds if r["output"].get("actual") is not None}
    out = []
    for ln, lk in zip(o["lines"], lookups):
        rule = lk["output"]
        e = exp.get(rule["rule_id"]) if rule else None
        out.append({"name": ln["name"], "amount": ln["amount"],
                    "type": rule["loai"] if rule else "khong_khop", "rule_id": rule["rule_id"] if rule else None,
                    "expected": e["expected"] if e else None, "delta": e["delta"] if e else None,
                    "chunk_id": rule.get("chunk_id") if rule else None,
                    "source_url": rule.get("nguon_url") if rule else None})
    return out


def plan_numbers(plan: dict) -> dict:
    """Số suy ra từ kế hoạch, do CODE tính (model không tự nhân / trừ): tổng tiền hàng và số căn cứ của mỗi đơn.
    gross = "gross" nếu chữ dán ghi tổng tiền hàng, không thì unit_price × qty; base = gross - |voucher_shop|."""
    out = []
    for o in (plan.get("orders") or []) if isinstance(plan, dict) else []:
        if not isinstance(o, dict):
            continue
        def num(k):
            v = o.get(k)
            return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
        qty = num("qty") or 1
        gross = num("gross") if num("gross") is not None else (num("unit_price") * qty if num("unit_price") is not None else None)
        voucher = abs(num("voucher_shop") or 0)
        out.append({"order_id": o.get("order_id"), "qty": qty, "gross": gross, "voucher_shop": -voucher,
                    "base_amount": None if gross is None else gross - voucher})
    return {"orders": out}


# ── Vòng agent ──
def _user_message(text: str, history: list, extra: str = "") -> str:
    # HU-11: tách rõ tin nhắn của chủ shop (yêu cầu + chữ dán, giữa <<< >>>) khỏi lịch sử do hệ thống ghi (đáng tin).
    parts = ["## TIN NHẮN CỦA CHỦ SHOP (yêu cầu + chữ dán chi tiết thanh toán; chỉ phần giữa <<< và >>>):\n<<<\n%s\n>>>"
             % text.strip()]
    if history:
        parts.append("## LỊCH SỬ DO HỆ THỐNG GHI (đáng tin, không phải chủ shop dán): các bước bạn đã trả và output công cụ thật")
        for i, h in enumerate(history, 1):
            if "code" in h["step"]:
                parts.append("#%d CODE TÍNH SẴN (dùng nguyên các số này, gross = tổng tiền hàng, base_amount = số căn cứ):" % i)
                for r in h.get("results", []):
                    parts.append("   %s" % json.dumps(r["output"], ensure_ascii=False))
                continue
            parts.append("#%d bạn trả: %s" % (i, json.dumps(h["step"], ensure_ascii=False)))
            for r in h.get("results", []):
                parts.append("   %s → %s" % (r["tool"], json.dumps(r["output"], ensure_ascii=False)[:RESULT_PREVIEW]))
    if extra:
        parts.append(extra)
    parts.append("Trả đúng MỘT object JSON cho bước tiếp theo.")
    return "\n".join(parts)


def _next_step(text, history, extra=""):
    reply = call_model(SYSTEM, _user_message(text, history, extra))
    if ai.MODEL_PROVIDER == "fake":
        return _fake_step(history)
    step = parse_step(reply.get("text", ""))
    if step is None:   # nhắc định dạng một lần
        note("model trả sai định dạng hoặc JSON bị cắt cụt, nhắc lại")
        reply = call_model(SYSTEM, _user_message(
            text, history, "Lượt trước không phải một object JSON hợp lệ (hoặc quá dài nên bị cắt). "
                           "Chỉ trả MỘT object JSON gọn, không giải thích."))
        step = parse_step(reply.get("text", ""))
    return step


def _run_tools(calls) -> list:
    results = []
    for c in calls if isinstance(calls, list) else []:
        name, args = (c or {}).get("tool"), _norm_args((c or {}).get("args") or {})
        if name not in TOOLS or name not in H3_TOOLS:
            results.append({"tool": name, "output": {"error": "không có công cụ %r" % name}})
            continue
        try:
            out = TOOLS[name](**args)
        except Exception as e:   # sai tham số / lỗi trong công cụ: báo lại cho agent, không dừng phiên
            out = {"error": "%s: %s" % (type(e).__name__, e)}
        results.append({"tool": name, "output": out})
    return results


def _evidence(history: list, text: str) -> dict:
    """Gom bằng chứng từ output công cụ trong trace: số, luật, đoạn chính sách, kết quả tính."""
    pool, rules, chunks, expecteds, sums, drafts = numbers_in(text), {}, {}, [], [], []
    for h in history:
        calls = h["step"].get("tools") or []
        for i, r in enumerate(h.get("results", [])):
            out = r["output"]
            pool |= numbers_in(out)
            args = _norm_args((calls[i] or {}).get("args") or {}) if i < len(calls) and isinstance(calls[i], dict) else {}
            if r["tool"] == "lookup_fee_rule" and isinstance(out, dict) and out.get("rule_id"):
                rules[out["rule_id"]] = out
                if out.get("chunk_id"):   # H2 nối luật → đoạn chính sách (cột chunk_id của fee_rules.csv): nguồn hợp lệ
                    chunks.setdefault(out["chunk_id"], {"chunk_id": out["chunk_id"], "effective_date": out.get("hieu_luc_tu"),
                                                        "_platform": out.get("platform")})
            elif r["tool"] == "search_policy" and isinstance(out, list):
                for c in out:
                    if isinstance(c, dict) and c.get("chunk_id"):
                        chunks[c["chunk_id"]] = dict(c, _platform=args.get("platform"))
            elif r["tool"] == "expected_amount" and isinstance(out, dict) and out.get("expected") is not None:
                expecteds.append(out)
            elif r["tool"] == "check_lines_sum" and isinstance(out, dict) and "ok" in out:
                sums.append(out)
            elif r["tool"] == "draft_platform_question" and isinstance(out, dict) and out.get("draft"):
                drafts.append(out["draft"])
    return {"pool": pool, "rules": rules, "chunks": chunks, "expecteds": expecteds, "sums": sums, "drafts": drafts}


def _rule_problem(rule: dict, rid: str, platform, order_date):
    """Lý do luật không dùng được cho đơn (sai sàn / ngoài hiệu lực), hoặc None."""
    rp = rule.get("platform") or rid.split("_", 1)[0]
    if platform and rp != platform:
        return "thuộc sàn %s, đơn là %s" % (rp, platform)
    if order_date:
        tu, den = str(rule.get("hieu_luc_tu") or "")[:10], str(rule.get("hieu_luc_den") or "")[:10]
        if (tu and order_date < tu) or (den and den not in ("None", "null") and order_date > den):
            return "hiệu lực %s → %s, không gồm ngày đặt %s" % (tu or "?", den or "nay", order_date)
    return None


def _mismatch(o: dict) -> bool:
    return any(ln.get("type") == "khong_khop" or (isinstance(ln.get("delta"), int) and abs(ln["delta"]) > 1)
               for ln in o.get("lines", []))


def verify(result: dict, history: list, text: str) -> list:
    """Bước kiểm (HU-8). Trả danh sách lỗi, rỗng = qua.
      - mọi con số có trong output công cụ hoặc chữ dán (±1đ; tỉ lệ ±0,0015)
      - mọi rule_id do lookup_fee_rule trả, ĐÚNG SÀN, CÒN HIỆU LỰC tại ngày đặt đơn, type khớp loại luật
      - mọi chunk_id do search_policy trả cho đúng sàn, không có ngày hiệu lực sau ngày đặt đơn
      - quyết định khớp các dòng: có dòng lệch / không khớp thì không được act; tổng không khớp tiền về thì phải ask"""
    ev = _evidence(history, text)
    pool = ev["pool"]
    orders = result["orders"] if "orders" in result else [result]
    err = []
    for o in orders:
        tag, plat, day = o.get("order_id") or "?", o.get("platform"), o.get("order_date")
        for k in ("payout", "cogs", "profit"):
            if o.get(k) is not None and not _found(o[k], pool):
                err.append("%s: %s=%s không có trong output công cụ hay chữ dán" % (tag, k, o[k]))
        for ln in o.get("lines", []):
            name = ln.get("name")
            for k in ("amount", "expected", "delta"):
                if ln.get(k) not in (None, 0) and not _found(ln[k], pool):
                    err.append("%s: dòng \"%s\" %s=%s không có nguồn" % (tag, name, k, ln[k]))
            rid = ln.get("rule_id")
            if rid:
                rule = ev["rules"].get(rid)
                if rule is None:
                    err.append("%s: dòng \"%s\" rule_id %s không do lookup_fee_rule trả" % (tag, name, rid))
                else:
                    why = _rule_problem(rule, rid, plat, day)
                    if why:
                        err.append("%s: dòng \"%s\" rule_id %s %s" % (tag, name, rid, why))
                    if rule.get("loai") in ("bat_buoc", "cong_tac") and ln.get("type") != rule["loai"]:
                        err.append("%s: dòng \"%s\" type=%s nhưng luật là %s" % (tag, name, ln.get("type"), rule["loai"]))
            elif ln.get("type") != "khong_khop":
                err.append("%s: dòng \"%s\" không có rule_id thì type phải là khong_khop" % (tag, name))
            cid = ln.get("chunk_id")
            if cid:
                c = ev["chunks"].get(cid)
                if c is None:
                    err.append("%s: chunk_id %s không do search_policy trả" % (tag, cid))
                else:
                    if plat and c.get("_platform") and c["_platform"] != plat:
                        err.append("%s: chunk_id %s thuộc sàn %s, đơn là %s" % (tag, cid, c["_platform"], plat))
                    d = str(c.get("effective_date") or "")[:10]
                    if day and d and d not in ("None", "null") and d > day:
                        err.append("%s: chunk_id %s hiệu lực từ %s, sau ngày đặt %s" % (tag, cid, d, day))
        for s in o.get("switches", []):
            for k in ("amount", "share_of_profit"):
                if s.get(k) is not None and not _found(s[k], pool):
                    err.append("%s: công tắc \"%s\" %s=%s không có nguồn" % (tag, s.get("name"), k, s[k]))
        for a in o.get("actions", []):
            readings = token_readings(str(a.get("text") or "")) + [{x} for x in numbers_in(a.get("gain_per_order"))]
            for r in readings:
                if not any(_found(x, pool) for x in r):
                    err.append("%s: việc nên làm có số %g không có nguồn" % (tag, max(r)))
        d = o.get("decision")
        if d in ("act", "escalate"):
            bad_sum = any(not s["ok"] and o.get("payout") is not None and abs(int(s["payout"]) - int(o["payout"])) <= 1
                          for s in ev["sums"])
            if bad_sum:
                err.append("%s: check_lines_sum báo tổng các dòng không khớp tiền về → phải ask" % tag)
            elif d == "act" and _mismatch(o):
                err.append("%s: có dòng lệch luật / không khớp luật nhưng decision=act → phải escalate" % tag)
            elif d == "escalate" and not _mismatch(o):
                err.append("%s: decision=escalate nhưng mọi dòng khớp luật (delta = 0)" % tag)
    return err


def _fallback(result: dict, problems: list, history: list, text: str) -> dict:
    """Vẫn sai sau 1 lần sửa: chỉ trả BẢNG DÒNG đã kiểm được, bỏ công tắc / việc nên làm.
    Quyết định do CODE suy ra từ output công cụ, không dựa vào câu trả lời của model."""
    note("fallback: %s" % "; ".join(problems)[:250])
    ev = _evidence(history, text)
    orders = result["orders"] if "orders" in result else [result]
    for o in orders:
        plat, day = o.get("platform"), o.get("order_date")
        lines = []
        for ln in o.get("lines", []):
            amount = ln.get("amount") if isinstance(ln.get("amount"), int) and _found(ln["amount"], ev["pool"]) else None
            rid = ln.get("rule_id")
            rule = ev["rules"].get(rid) if rid else None
            if rule is None or _rule_problem(rule, rid, plat, day):
                rid, rule = None, None
            e = next((x for x in ev["expecteds"] if rule and x.get("rule_id") == rid
                      and (amount is None or x.get("actual") == amount)), None)
            lines.append({"name": ln.get("name"), "amount": amount,
                          "type": rule["loai"] if rule and rule.get("loai") in ("bat_buoc", "cong_tac") else "khong_khop",
                          "rule_id": rid, "expected": e["expected"] if e else None,
                          "delta": e.get("delta") if e else None,
                          "chunk_id": None, "source_url": rule.get("nguon_url") if rule else None})
        o["lines"], o["switches"], o["actions"] = lines, [], []
        for k in ("payout", "cogs", "profit"):
            if o.get(k) is not None and not _found(o[k], ev["pool"]):
                o[k] = None
        if o.get("profit") is None and isinstance(o.get("payout"), int) and isinstance(o.get("cogs"), int):
            o["profit"] = o["payout"] - o["cogs"]          # CODE tính lại từ hai số đã kiểm, không lấy số của model
        if o.get("decision") in ("refuse", "ask"):
            continue
        bad_sum = any(not s["ok"] for s in ev["sums"])
        if bad_sum or o.get("cogs") is None or o.get("profit") is None:
            o["decision"], o["draft_to_platform"] = "ask", None
            o["question"] = ("Tổng các dòng trên đơn %s không khớp tiền về. Bạn dán lại đủ các dòng giúp mình." % o.get("order_id")
                             if bad_sum else "Bạn cho mình giá vốn của đơn %s để tính lãi thật nhé." % o.get("order_id"))
        elif _mismatch(o):
            o["decision"], o["question"] = "escalate", None
            if not o.get("draft_to_platform") or o["draft_to_platform"] not in ev["drafts"]:
                odd = next(ln for ln in lines if ln["type"] == "khong_khop" or (ln["delta"] or 0) != 0)
                o["draft_to_platform"] = TOOLS["draft_platform_question"](
                    o.get("order_id"), odd["name"], odd["expected"], odd["amount"] or 0)["draft"]
        else:
            o["decision"], o["question"], o["draft_to_platform"] = "act", None, None
    if "orders" in result:
        result["decision"] = max((x["decision"] for x in orders), key=schema.DECISION_PRIORITY.get, default="act")
    return result


def _clean_order(o: dict, trace_id) -> dict:
    fields = {k: v for k, v in o.items() if k in schema.AGENT_RESULT_KEYS}
    fields["trace_id"] = trace_id
    fields["decision"] = _norm_enum(fields.get("decision"), schema.DECISIONS)
    fields["platform"] = _norm_enum(fields.get("platform"), schema.PLATFORMS, _PLATFORM_ALIASES)
    for ln in fields.get("lines") or []:
        if isinstance(ln, dict):
            ln["type"] = _norm_enum(ln.get("type"), schema.LINE_TYPES)
    return schema.agent_result(**fields)


def _assemble(final: dict, trace_id, session_state_id=None) -> dict:
    """final của model → AgentResult / SessionResult đúng hợp đồng H4."""
    if isinstance(final.get("orders"), list):
        orders = [_clean_order(o, trace_id) for o in final["orders"][:MAX_ORDERS] if isinstance(o, dict)]
        pc = final.get("platform_comparison")
        if isinstance(pc, dict):
            rows = [dict(r, platform=_norm_enum(r.get("platform"), schema.PLATFORMS, _PLATFORM_ALIASES))
                    for r in pc.get("rows") or [] if isinstance(r, dict)]
            pc = {"product": pc.get("product"), "rows": rows,
                  "best_platform": _norm_enum(pc.get("best_platform"), schema.PLATFORMS, _PLATFORM_ALIASES)}
            if len({r.get("platform") for r in pc["rows"]}) < 2:
                pc = None
        return schema.session_result(orders, pc if isinstance(pc, dict) else None, session_state_id, trace_id)
    return _clean_order(final, trace_id)


def _trace_id():
    try:
        import tracing
        return getattr(tracing, "_case", {}).get("id") or "local"
    except Exception:
        return "local"


def _plan_order(history):
    plan = next((h["step"]["plan"] for h in history if "plan" in h["step"]), None) or {}
    orders = plan.get("orders") or [{}]
    return orders[0] if isinstance(orders[0], dict) else {}


def answer(text: str, session_state_id: str = None) -> dict:
    trace_id = _trace_id()
    state = SESSIONS.pop(session_state_id, None) if session_state_id else None
    if state:   # trả lời một câu Ask: giữ các bước cũ, thêm câu trả lời của chủ shop
        note("làm tiếp phiên %s" % session_state_id)
        history = state["history"]
        text = state["text"] + "\n\nCHỦ SHOP TRẢ LỜI CÂU HỎI: " + text
    else:
        history = []
        reason = screen_request(text)
        if reason:
            note("refuse ở bước lọc (code)")
            return _out(schema.agent_result(decision="refuse", refusal_reason=reason, trace_id=trace_id))

    turns = calls = fixes = 0
    extra = ""
    for _ in range(MAX_STEPS):
        step = _next_step(text, history, extra)
        extra = ""
        if not step:
            note("dừng: model không trả JSON hợp lệ sau khi nhắc")
            return _out(schema.agent_result(decision="ask", trace_id=trace_id,
                                            question="Mình chưa đọc được đơn. Bạn dán lại chi tiết thanh toán của đơn giúp mình."))
        if "plan" in step:
            plan = step["plan"] if isinstance(step["plan"], dict) else {}
            n = len(plan.get("orders") or []) or 1
            note("kế hoạch: %d đơn · %s" % (n, json.dumps(plan.get("steps", ""), ensure_ascii=False)[:200]))
            if n > MAX_ORDERS:
                o = _plan_order([{"step": step}])
                return _out(schema.agent_result(decision="ask", platform=o.get("platform"), trace_id=trace_id,
                                                question="Mỗi lần mình soi tối đa %d đơn. Bạn chọn bớt giúp mình nhé." % MAX_ORDERS))
            history.append({"step": step, "results": []})
            nums = plan_numbers(plan)
            history.append({"step": {"code": "plan_numbers"}, "results": [{"tool": "plan_numbers", "output": nums}]})
            continue
        if "tools" in step or "tool" in step:
            calls_req = step.get("tools") or [{"tool": step.get("tool"), "args": step.get("args")}]
            n_orders = len((next((h["step"]["plan"] for h in history if "plan" in h["step"]), {}) or {}).get("orders") or []) or 1
            turns += 1
            calls += len(calls_req)
            if turns > min(MAX_TURNS_PER_SESSION, MAX_TURNS_PER_ORDER * n_orders) or calls > MAX_CALLS_PER_ORDER * n_orders:
                note("dừng: vượt giới hạn %d lượt / %d lời gọi" % (turns, calls))
                extra = "Đã hết lượt gọi công cụ. Trả {\"final\": …} ngay với những gì đã có."
                history.append({"step": {"tools": []}, "results": []})
                continue
            results = _run_tools(calls_req)
            history.append({"step": {"tools": calls_req}, "results": results})
            stop = next((r["output"] for r in results if r["tool"] == "ask_user" and isinstance(r["output"], dict)
                         and r["output"].get("stop")), None)
            if stop:   # Ask: lưu trạng thái phiên để làm tiếp
                sid = "s-" + uuid.uuid4().hex[:8]
                SESSIONS[sid] = {"text": text, "history": history}
                o = _plan_order(history)
                res = schema.agent_result(decision="ask", platform=o.get("platform"), order_id=o.get("order_id"),
                                          order_date=o.get("order_date"), question=stop["question"], trace_id=trace_id)
                note("ask: lưu phiên %s" % sid)
                return _out(res, sid)
            continue
        if "final" in step and isinstance(step["final"], dict):
            result = _assemble(step["final"], trace_id, session_state_id)
            problems = verify(result, history, text)
            shape = (schema.validate_session_result(result) if "orders" in result
                     else schema.validate_agent_result(result))
            problems += ["hợp đồng H4: " + e for e in shape]
            if problems and fixes == 0 and ai.MODEL_PROVIDER != "fake":
                fixes += 1
                note("bước kiểm: %d lỗi, cho agent sửa 1 lần: %s" % (len(problems), "; ".join(problems)[:240]))
                history.append({"step": step, "results": []})
                extra = "BƯỚC KIỂM BÁO LỖI, sửa và trả lại {\"final\": …}:\n- " + "\n- ".join(problems[:15])
                continue
            if problems:
                result = _fallback(result, problems, history, text)
                still = (schema.validate_session_result(result) if "orders" in result
                         else schema.validate_agent_result(result))
                if still:   # lưới cuối: fallback vẫn lệch hợp đồng thì hỏi lại, không trả JSON hỏng
                    note("fallback vẫn lệch H4: %s" % "; ".join(still)[:200])
                    o = _plan_order(history)
                    result = schema.agent_result(decision="ask", platform=o.get("platform"), order_id=o.get("order_id"),
                                                 order_date=o.get("order_date"), trace_id=trace_id,
                                                 question="Mình chưa kiểm được đơn này. Bạn dán lại chi tiết thanh toán và giá vốn giúp mình.")
            elif fixes:
                note("tự sửa thành công sau bước kiểm")
            return _out(result)
        note("bước không hợp lệ: %s" % json.dumps(step, ensure_ascii=False)[:150])
        extra = "Bước trước không đúng giao thức (plan / tools / final)."
    note("dừng: hết %d bước" % MAX_STEPS)
    return _out(schema.agent_result(decision="ask", trace_id=trace_id,
                                    question="Đơn này phức tạp hơn mình xử lý được trong một lượt. Bạn gửi từng đơn một giúp mình."))


def _out(result: dict, session_state_id: str = None) -> dict:
    if session_state_id and "orders" in result:
        result["session_state_id"] = session_state_id
    out = {"output": json.dumps(result, ensure_ascii=False), "result": result}
    if session_state_id:
        out["session_state_id"] = session_state_id
    return out
