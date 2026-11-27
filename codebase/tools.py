"""Hợp đồng H3: 10 công cụ của agent. Huy giữ CHỮ KÝ (tên, tham số, hình dạng output), Thái giữ THÂN HÀM (TH-5).

Không đổi tên, không đổi tham số. Muốn đổi thì báo cả nhóm. Không công cụ nào có tác động ra ngoài:
chỉ đọc dữ liệu hoặc soạn nháp.

Quy ước dùng chung (khớp H4 trong codebase/schema.py):
  - Tiền: số nguyên VNĐ. Khoản trừ ÂM, khoản cộng DƯƠNG.
  - Ngày "YYYY-MM-DD" (nhận cả "dd/mm/yyyy"). platform: "shopee" | "tiktok" | "lazada". shop_type: "shop_thuong" | "mall".
  - category: mã ngành như data/fee_engine.CATEGORIES ("thoi_trang", "my_pham", "dien_tu", "nha_cua", "me_be", "thuc_pham");
    nhận cả tên hiển thị ("Thời trang", "Điện tử & phụ kiện").
  - Line (đầu vào các công cụ): dict có ít nhất {"name", "amount"}; thêm "type", "rule_id" nếu đã biết.

Nguồn sự thật (TH-5):
  - Con số: data/fee_rules.csv (H2) qua data/fee_engine.py — CÙNG bảng phí với data giả và đáp án bộ câu thử.
  - Giải thích / trích dẫn: data/policies/chunks.jsonl (H1) qua codebase/retrieval.py.
  - lookup_fee_rule và search_policy lọc CỨNG theo platform: không bao giờ trả luật / đoạn của sàn khác.
Test: python -m unittest discover -s tests
"""
import os
import re
import sys
import unicodedata

from tracing import tool, TOOLS  # noqa: F401  (TOOLS: tên → hàm, agent.py dùng để gọi công cụ)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "data"))
import fee_engine as _fe  # noqa: E402

PLATFORMS = tuple(_fe.PLATFORMS)
_RULES = None


def _rules():
    """Bảng phí, nạp một lần (data/fee_rules.csv; chưa có thì bảng tạm v0)."""
    global _RULES
    if _RULES is None:
        _RULES = _fe.load_rules()[0]
    return _RULES


def _plain(s):
    s = unicodedata.normalize("NFD", str(s or "").lower().replace("đ", "d"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def _norm(s):
    """"Phí tiếp thị liên kết (10%)" → "tiep thi lien ket": bỏ ngoặc, chữ thường, bỏ dấu, bỏ chữ "phí" đầu."""
    s = re.sub(r"\(.*?\)", " ", _plain(s))
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"^phi ", "", s)


def _names(r):
    """Tên hiển thị trước, rồi các tên cũ (cột ten_cu, cách nhau bằng "|")."""
    out = [("ten_hien_thi", _norm(r["ten_hien_thi"]))]
    out += [("ten_cu", _norm(x)) for x in str(r.get("ten_cu") or "").split("|") if x.strip()]
    return out


def _date(d):
    d = str(d or "").strip()
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", d)
    return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1))) if m else d[:10]


def _shop_type(s):
    return "mall" if "mall" in _plain(s) else "shop_thuong"


def _category(c):
    c = str(c or "").strip()
    if c in _fe.CATEGORIES:
        return c
    p = _norm(c)
    for key, name in _fe.CATEGORIES.items():
        if p and (p == _norm(key) or p == _norm(name) or p in _norm(name)):
            return key
    return c or "*"


def _rule_by_id(rule_id):
    return next((r for r in _rules() if r["rule_id"] == rule_id), None)


def _out_rule(r, matched_by):
    keys = ["rule_id", "platform", "fee_key", "ten_hien_thi", "ten_cu", "loai", "base", "rate", "cap_vnd",
            "per_order_vnd", "ap_dung", "nganh", "hieu_luc_tu", "hieu_luc_den", "chunk_id", "nguon_url", "da_doi_chieu"]
    out = {k: (None if r.get(k) in ("", None) else r.get(k)) for k in keys}
    out["matched_by"] = matched_by
    return out


def _amount(x):
    try:
        return int(round(float(x.get("amount") or 0)))
    except (TypeError, ValueError):
        return 0


def _is_switch(x):
    """Dòng công tắc: theo "type" agent ghi; chưa có thì tra loại của rule_id."""
    if x.get("type"):
        return x["type"] == "cong_tac"
    r = _rule_by_id(x.get("rule_id")) if x.get("rule_id") else None
    return bool(r and r["loai"] == "cong_tac")


@tool
def check_lines_sum(lines: list, payout: int) -> dict:
    """Kiểm tổng các dòng có bằng tiền về không.
    Input: lines = MỌI dòng trên chi tiết thanh toán: dòng giá bán (dương), voucher shop (âm) và các khoản phí (âm);
           payout = tiền về hiển thị.
    Output: {"ok": bool, "sum": int, "payout": int, "delta": int}  (delta = payout - sum; ok khi |delta| ≤ 1).
    Không tác động ra ngoài."""
    total = sum(_amount(x) for x in lines or [])
    delta = int(payout) - total
    return {"ok": abs(delta) <= 1, "sum": total, "payout": int(payout), "delta": delta}


@tool
def lookup_fee_rule(fee_name: str, order_date: str, shop_type: str, category: str, platform: str):
    """Tìm luật phí đang hiệu lực tại ngày đặt đơn. Hiểu cả tên cũ (vd "Phí thanh toán" → "Phí xử lý giao dịch").
    Lọc cứng theo platform: không bao giờ trả luật của sàn khác.
    Input: fee_name (tên dòng như trên chi tiết thanh toán), order_date, shop_type, category, platform.
    Output: {"rule_id", "platform", "fee_key", "ten_hien_thi", "ten_cu", "loai", "base", "rate", "cap_vnd",
             "per_order_vnd", "ap_dung", "nganh", "hieu_luc_tu", "hieu_luc_den", "chunk_id", "nguon_url", "da_doi_chieu",
             "matched_by" ("ten_hien_thi" | "ten_cu")}
            hoặc None nếu không có luật khớp (dòng đó là "khong_khop"). Luật tính theo ngành (vd phí cố định)
            cần category đúng; thiếu category thì trả None → hỏi lại chủ shop ngành hàng.
    Không tác động ra ngoài."""
    platform = str(platform or "").strip().lower()
    if platform not in PLATFORMS:
        return None
    key, date = _norm(fee_name), _date(order_date)
    if not key or not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return None
    stype, cat = _shop_type(shop_type), _category(category)
    # các fee_key của sàn này có tên (hiển thị hoặc cũ) khớp; tên hiển thị được ưu tiên
    cands = {}
    for r in _rules():
        if r["platform"] != platform:
            continue
        for how, name in _names(r):
            if name == key and (r["fee_key"] not in cands or how == "ten_hien_thi"):
                cands[r["fee_key"]] = how
    for fee_key, how in sorted(cands.items(), key=lambda kv: kv[1] != "ten_hien_thi"):
        r = _fe.find_rule(_rules(), platform, fee_key, date, stype, cat)
        if r is not None:
            return _out_rule(r, how)
    return None


@tool
def search_policy(query: str, platform: str, order_date: str, policy_type: str = "", k: int = 5) -> list:
    """Tìm đoạn chính sách để GIẢI THÍCH và TRÍCH DẪN (không dùng số trong đoạn để tính).
    Lọc cứng theo platform; bỏ đoạn có effective_date SAU order_date (chưa hiệu lực tại ngày đặt đơn).
    Input: query (câu hỏi), platform, order_date ("YYYY-MM-DD", None = không lọc ngày);
           tuỳ chọn: policy_type ("fee" | "voucher" | "ads" | "return_refund" | "settlement" | "" = mọi loại), k = số đoạn tối đa.
    Output: top-k [{"chunk_id", "url", "effective_date", "text", "score"}]; [] khi sàn chưa có kho
            hoặc không đoạn nào đủ gần → không tự đoán, chunk_id để null.
    Không tác động ra ngoài (đọc kho gộp data/policies/ qua codebase/retrieval.py: BM25 từ khoá, thêm vector
    nếu có API embedding — chỉ gửi câu hỏi đi để embed)."""
    from retrieval import search
    platform = str(platform or "").strip().lower()
    if platform not in PLATFORMS:
        return []
    k = max(int(k or 5), 1)
    day = _date(order_date) if order_date else ""
    hits = search(query, platform=platform, policy_type=policy_type or "", k=k * 3)

    def in_effect(h):
        d = str(h.get("effective_date") or "")[:10]
        return not day or d in ("", "null", "None") or d <= day

    return [{"chunk_id": h["chunk_id"], "url": h.get("url"), "effective_date": h.get("effective_date"),
             "text": h.get("text"), "score": h.get("score")}
            for h in hits if h.get("platform", platform) == platform and in_effect(h)][:k]


@tool
def expected_amount(rule_id: str, base_amount: int, actual_amount: int = None, qty: int = 1,
                    shop_rate: float = None) -> dict:
    """Tính số tiền đúng luật của một dòng và độ lệch so với số bị trừ.
    Input: rule_id; base_amount = số tiền căn cứ (đơn đa số luật: giá × SL - voucher shop;
           luật base "voucher_dong_tai_tro": giá trị mã ưu đãi đồng tài trợ; luật base "don": bỏ qua);
           actual_amount = số bị trừ trên đơn (âm) để tính delta; qty = số lượng (cho luật có trần mỗi sản phẩm);
           shop_rate = tỉ lệ % shop tự đặt (luật base "theo_shop", vd tiếp thị liên kết).
    Output: {"rule_id", "expected": int (âm), "actual": int | None, "delta": int | None, "rate": float | None,
             "cap_vnd": int | None, "capped": bool}  (delta = actual - expected; delta âm = bị trừ NHIỀU hơn luật).
            Thêm "error" nếu không có luật hoặc thiếu shop_rate (luật theo_shop).
    Không tác động ra ngoài."""
    r = _rule_by_id(rule_id)
    if r is None:
        return {"rule_id": rule_id, "expected": None, "actual": actual_amount, "delta": None, "rate": None,
                "cap_vnd": None, "capped": False, "error": "không có luật này trong bảng phí"}
    qty = max(int(qty or 1), 1)
    rate = float(shop_rate) if r["base"] == "theo_shop" and shop_rate is not None else r["rate"]
    if r["base"] == "theo_shop" and shop_rate is None:
        return {"rule_id": rule_id, "expected": None, "actual": actual_amount, "delta": None, "rate": None,
                "cap_vnd": r["cap_vnd"], "capped": False,
                "error": "luật này theo tỉ lệ shop tự đặt: cần shop_rate (%), hỏi chủ shop nếu không có"}
    if r["base"] == "don":
        raw = amt = int(r["per_order_vnd"] or 0)
    else:
        raw = int(round(int(base_amount or 0) * (rate or 0) / 100))
        amt = min(raw, r["cap_vnd"] * qty) if r["cap_vnd"] else raw
    expected = -int(amt)
    actual = None if actual_amount is None else int(actual_amount)
    return {"rule_id": rule_id, "expected": expected, "actual": actual,
            "delta": None if actual is None else actual - expected, "rate": rate,
            "cap_vnd": r["cap_vnd"], "capped": bool(r["cap_vnd"]) and raw > amt}


@tool
def unit_profit(price: int, lines: list, cogs: int) -> dict:
    """Tiền về và lãi thật của một đơn, phần lãi mà từng công tắc ăn mất.
    Input: price = giá bán × số lượng - voucher shop (dương; voucher shop không phải dòng phí, nó giảm số căn cứ);
           lines = các khoản phí bị trừ (âm, có "type"); cogs = giá vốn cả đơn (giá vốn 1 sp × số lượng).
    Output: {"payout": int, "cogs": int, "profit": int, "margin": float | None,
             "switches": [{"name", "amount" (dương), "share_of_profit"}] lớn nhất trước}
            (share_of_profit = tiền công tắc ÷ lãi thật; None khi lãi ≤ 0). Thiếu cogs → {"error"}: hỏi lại chủ shop.
    Không tác động ra ngoài."""
    payout = int(price) + sum(_amount(x) for x in lines or [])
    if cogs is None or str(cogs).strip() == "":
        return {"payout": payout, "cogs": None, "profit": None, "margin": None, "switches": [],
                "error": "thiếu giá vốn: hỏi lại chủ shop trước khi tính lãi"}
    profit = payout - int(cogs)
    sw = [{"name": x.get("name"), "amount": -_amount(x),
           "share_of_profit": round(-_amount(x) / profit, 3) if profit > 0 else None}
          for x in lines or [] if _is_switch(x) and _amount(x) < 0]
    sw.sort(key=lambda s: -s["amount"])
    return {"payout": payout, "cogs": int(cogs), "profit": profit,
            "margin": round(profit / int(price), 4) if int(price) > 0 else None, "switches": sw}


@tool
def switch_what_if(lines: list, switch: str, new_value: int, profit: int = None) -> dict:
    """Nếu đổi một công tắc thì lãi mỗi đơn thay đổi bao nhiêu.
    Input: lines = các khoản trừ của đơn; switch = tên dòng công tắc (đúng "name" trong lines);
           new_value = số tiền MỚI của dòng đó (âm; 0 = tắt), lấy từ expected_amount với tỉ lệ mới;
           profit = lãi hiện tại mỗi đơn (để tính số đơn được phép giảm).
    Output: {"switch", "old_amount", "new_amount", "gain_per_order", "profit_after": int | None,
             "max_order_drop_pct": float | None}
            (max_order_drop_pct: số đơn được phép giảm tối đa bao nhiêu % mà tổng lãi không thấp hơn trước
             = gain ÷ lãi sau khi đổi × 100; None khi đổi xong không lợi hơn).
    Không tác động ra ngoài."""
    line = next((x for x in lines or [] if x.get("name") == switch), None) or \
        next((x for x in lines or [] if _norm(x.get("name")) == _norm(switch)), None)
    if line is None:
        return {"switch": switch, "error": "không có dòng này trong lines"}
    old, new = _amount(line), int(new_value)
    if new > 0:
        new = -new                                   # khoản trừ luôn âm
    gain = new - old
    after = None if profit is None else int(profit) + gain
    if gain <= 0 or after is None or after <= 0:
        drop = None
    elif int(profit) <= 0:
        drop = 100.0                                 # đang lỗ → sau khi đổi có lãi, mất đơn nào cũng không tệ hơn
    else:
        drop = round(gain / after * 100, 1)
    return {"switch": line.get("name"), "old_amount": old, "new_amount": new, "gain_per_order": gain,
            "profit_after": after, "max_order_drop_pct": drop}


@tool
def breakeven_roas(margin_before_ads: float) -> dict:
    """ROAS hoà vốn = 1 ÷ biên lãi trước quảng cáo.
    Input: margin_before_ads = biên lãi trước quảng cáo dạng tỉ lệ (0 < m ≤ 1), vd 0.25 (nhận cả 25 nghĩa là 25%).
    Output: {"margin_before_ads": float, "breakeven_roas": float | None} (None nếu biên lãi ≤ 0).
    Không tác động ra ngoài."""
    m = float(margin_before_ads)
    if m > 1:
        m = m / 100                                  # 25 → 0,25
    return {"margin_before_ads": m, "breakeven_roas": round(1 / m, 2) if m > 0 else None}


@tool
def compare_platforms(orders: list, cogs: int) -> dict:
    """So lãi thật của cùng một sản phẩm trên ≥ 2 sàn.
    Input: orders = [{"platform", "order_id", "product", "price", "qty", "lines"}] (price = giá × SL - voucher shop);
           cogs = giá vốn MỘT sản phẩm.
    Output: {"product", "rows": [{"platform", "order_id", "payout", "profit", "profit_per_unit", "top_switch"}],
             "best_platform"} (best_platform = lãi MỖI SẢN PHẨM cao nhất)
            hoặc {"error"} nếu chưa đủ 2 sàn / thiếu giá vốn. Khớp SessionResult.platform_comparison (H4).
    Không tác động ra ngoài."""
    orders = orders or []
    plats = {str(o.get("platform") or "").lower() for o in orders}
    if len(plats & set(PLATFORMS)) < 2:
        return {"error": "cần ít nhất 2 sàn cùng sản phẩm"}
    if cogs is None or str(cogs).strip() == "":
        return {"error": "thiếu giá vốn: hỏi lại chủ shop"}
    rows = []
    for o in orders:
        qty = max(int(o.get("qty") or 1), 1)
        lines = o.get("lines") or []
        payout = int(o["price"]) + sum(_amount(x) for x in lines)
        profit = payout - int(cogs) * qty
        sw = [x for x in lines if _is_switch(x) and _amount(x) < 0]
        top = min(sw, key=_amount).get("name") if sw else None
        rows.append({"platform": str(o["platform"]).lower(), "order_id": o.get("order_id"), "payout": payout,
                     "profit": profit, "profit_per_unit": round(profit / qty), "top_switch": top})
    best = max(rows, key=lambda r: r["profit_per_unit"])["platform"]
    return {"product": orders[0].get("product"), "rows": rows, "best_platform": best}


@tool
def ask_user(question: str) -> dict:
    """Dừng lượt để hỏi lại chủ shop (thiếu giá vốn, thiếu dòng, tổng không khớp). Agent lưu trạng thái phiên.
    Input: question (một câu hỏi ngắn, cụ thể).
    Output: {"stop": True, "question": str}.
    Không tác động ra ngoài."""
    return {"stop": True, "question": str(question).strip()}


@tool
def draft_platform_question(order_id: str, line: str, expected, actual) -> dict:
    """Soạn NHÁP câu hỏi để chủ shop tự gửi sàn khi một dòng lệch luật hoặc không khớp luật nào. KHÔNG gửi.
    Input: order_id; line = tên dòng; expected = số đúng luật (âm) hoặc None nếu không có luật;
           actual = số bị trừ trên đơn (âm).
    Output: {"draft": str, "sent": False}.
    Chỉ soạn nháp, không gửi, không tác động ra ngoài."""
    def vnd(v):
        return "{:,}đ".format(abs(int(v))).replace(",", ".")
    if expected is None:
        body = ("đơn %s có khoản \"%s\" bị trừ %s nhưng tôi không tìm thấy khoản phí này trong biểu phí hiện hành. "
                "Nhờ sàn cho biết đây là phí gì, căn cứ chính sách nào và tính thế nào." % (order_id, line, vnd(actual)))
    else:
        body = ("đơn %s có khoản \"%s\" bị trừ %s, trong khi theo biểu phí tại ngày đặt đơn tôi tính ra %s "
                "(chênh %s). Nhờ sàn kiểm tra và hoàn lại phần chênh nếu trừ sai."
                % (order_id, line, vnd(actual), vnd(expected), vnd(int(actual) - int(expected))))
    return {"draft": "Chào bộ phận hỗ trợ người bán, " + body, "sent": False}


@tool
def search_example(query: str) -> list:
    """(ví dụ của khung, KHÔNG thuộc H3) Giữ tạm vì codebase/agent.py mẫu trên main còn gọi hàm này;
    bỏ khi agent thật (feat/huy-agent) được gộp vào main.
    Input: câu hỏi (str). Output: danh sách đoạn {"code", "text"}. Không tác động ra ngoài."""
    return [{"code": "VD-1", "text": "(ví dụ) đoạn dữ liệu giả — thay bằng dữ liệu thật của bài toán"}]
