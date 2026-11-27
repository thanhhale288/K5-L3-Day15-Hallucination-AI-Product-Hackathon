"""Hợp đồng H3: 10 công cụ của agent. Huy giữ CHỮ KÝ (tên, tham số, hình dạng output), Thái giữ THÂN HÀM (TH-5).

Không đổi tên, không đổi tham số. Muốn đổi thì báo cả nhóm. Không công cụ nào có tác động ra ngoài:
chỉ đọc dữ liệu hoặc soạn nháp.

Quy ước dùng chung (khớp H4 trong codebase/schema.py):
  - Tiền: số nguyên VNĐ. Khoản trừ ÂM, khoản cộng DƯƠNG.
  - Ngày "YYYY-MM-DD". platform: "shopee" | "tiktok" | "lazada". shop_type: "shop_thuong" | "mall".
  - category: mã ngành như data/fee_engine.CATEGORIES ("thoi_trang", "my_pham", "dien_tu", "nha_cua", "me_be", "thuc_pham").
  - Line (đầu vào các công cụ): dict có ít nhất {"name", "amount"}; thêm "type", "rule_id" nếu đã biết.

TRẠNG THÁI THÂN HÀM (HU-2: chạy luồng với công cụ trả số cố định, không chờ Thái):
  - BẢN TẠM, Thái thay ở TH-5 (bọc data/fee_engine.py, giữ nguyên input/output):
      lookup_fee_rule, expected_amount  → chỉ biết các luật của đơn mẫu DEMO-0412 (Shopee, 12/11/2026)
      search_policy                     → gọi codebase/retrieval.py (kho TikTok đã có; Shopee, Lazada chưa nối → [])
      check_lines_sum, unit_profit, switch_what_if, breakeven_roas, compare_platforms → phép tính đơn giản
  - XONG (không tính số): ask_user, draft_platform_question
"""
from tracing import tool, TOOLS  # noqa: F401  (TOOLS: tên → hàm, agent.py dùng để gọi công cụ)

# ── Dữ liệu cố định cho bản tạm: luật của đơn mẫu DEMO-0412, lấy từ data/fee_engine.py + fee_rules_v0.csv ──
_DEMO_RULES = [
    {"rule_id": "shopee_phi_co_dinh_thoi_trang_shop_thuong_2026-05-08", "fee_key": "phi_co_dinh",
     "ten_hien_thi": "Phí cố định", "ten_cu": "", "loai": "bat_buoc", "base": "gia_sau_voucher_shop",
     "rate": 9.0, "cap_vnd": None, "per_order_vnd": None, "hieu_luc_tu": "2026-05-08", "hieu_luc_den": None,
     "da_doi_chieu": "gia_dinh"},
    {"rule_id": "shopee_phi_xu_ly_giao_dich_shop_thuong_2026-05-01", "fee_key": "phi_xu_ly_giao_dich",
     "ten_hien_thi": "Phí xử lý giao dịch", "ten_cu": "Phí thanh toán", "loai": "bat_buoc",
     "base": "gia_sau_voucher_shop", "rate": 6.0, "cap_vnd": None, "per_order_vnd": None,
     "hieu_luc_tu": "2026-05-01", "hieu_luc_den": None, "da_doi_chieu": "bao_chi"},
    {"rule_id": "shopee_voucher_xtra_2026-05-23", "fee_key": "voucher_xtra", "ten_hien_thi": "Phí Voucher Xtra",
     "ten_cu": "", "loai": "cong_tac", "base": "gia_sau_voucher_shop", "rate": 5.5, "cap_vnd": 50000,
     "per_order_vnd": None, "hieu_luc_tu": "2026-05-23", "hieu_luc_den": None, "da_doi_chieu": "bao_chi"},
    {"rule_id": "shopee_tiep_thi_lien_ket_2026-01-01", "fee_key": "tiep_thi_lien_ket",
     "ten_hien_thi": "Phí tiếp thị liên kết", "ten_cu": "Hoa hồng tiếp thị liên kết", "loai": "cong_tac",
     "base": "theo_shop", "rate": None, "cap_vnd": None, "per_order_vnd": None, "hieu_luc_tu": "2026-01-01",
     "hieu_luc_den": None, "da_doi_chieu": "bao_chi"},
    {"rule_id": "shopee_phi_ha_tang_2025-07-01", "fee_key": "phi_ha_tang", "ten_hien_thi": "Phí hạ tầng",
     "ten_cu": "", "loai": "bat_buoc", "base": "don", "rate": None, "cap_vnd": None, "per_order_vnd": 3000,
     "hieu_luc_tu": "2025-07-01", "hieu_luc_den": None, "da_doi_chieu": "bao_chi"},
    {"rule_id": "shopee_thue_khau_tru_2025-07-01", "fee_key": "thue_khau_tru",
     "ten_hien_thi": "Thuế khấu trừ (GTGT + TNCN)", "ten_cu": "Thuế", "loai": "bat_buoc",
     "base": "gia_sau_voucher_shop", "rate": 1.5, "cap_vnd": None, "per_order_vnd": None,
     "hieu_luc_tu": "2025-07-01", "hieu_luc_den": None, "da_doi_chieu": "gia_dinh"},
]
_DEMO_URL = "https://vccinews.vn/news/shopee-tiktok-shop-tang-manh-phi-san"


def _norm(s):
    import re
    s = re.sub(r"\(.*?\)", " ", str(s or "").lower())       # "Phí tiếp thị liên kết (10%)" → bỏ phần trong ngoặc
    return " ".join(s.replace("phí ", "").split())


@tool
def check_lines_sum(lines: list, payout: int) -> dict:
    """Kiểm tổng các dòng có bằng tiền về không.
    Input: lines = MỌI dòng trên chi tiết thanh toán: dòng giá bán (dương), voucher shop (âm) và các khoản phí (âm);
           payout = tiền về hiển thị.
    Output: {"ok": bool, "sum": int, "payout": int, "delta": int}  (delta = payout - sum; ok khi |delta| ≤ 1).
    Không tác động ra ngoài."""
    total = sum(int(x.get("amount") or 0) for x in lines)
    delta = int(payout) - total
    return {"ok": abs(delta) <= 1, "sum": total, "payout": int(payout), "delta": delta}


@tool
def lookup_fee_rule(fee_name: str, order_date: str, shop_type: str, category: str, platform: str):
    """Tìm luật phí đang hiệu lực tại ngày đặt đơn. Hiểu cả tên cũ (vd "Phí thanh toán" → "Phí xử lý giao dịch").
    Lọc cứng theo platform: không bao giờ trả luật của sàn khác.
    Input: fee_name (tên dòng như trên chi tiết thanh toán), order_date, shop_type, category, platform.
    Output: {"rule_id", "platform", "fee_key", "ten_hien_thi", "ten_cu", "loai", "base", "rate", "cap_vnd",
             "per_order_vnd", "hieu_luc_tu", "hieu_luc_den", "chunk_id", "nguon_url", "da_doi_chieu"}
            hoặc None nếu không có luật khớp (dòng đó là "khong_khop").
    Không tác động ra ngoài."""
    # BẢN TẠM (Thái thay, TH-5): chỉ biết luật Shopee của đơn mẫu DEMO-0412.
    if platform != "shopee":
        return None
    key = _norm(fee_name)
    for r in _DEMO_RULES:
        if key in (_norm(r["ten_hien_thi"]), _norm(r["ten_cu"])) and r["hieu_luc_tu"] <= order_date:
            return dict(r, platform="shopee", chunk_id=None, nguon_url=_DEMO_URL)
    return None


@tool
def search_policy(query: str, platform: str, order_date: str, policy_type: str = "", k: int = 5) -> list:
    """Tìm đoạn chính sách để GIẢI THÍCH và TRÍCH DẪN (không dùng số trong đoạn để tính).
    Lọc cứng theo platform; bỏ đoạn có effective_date SAU order_date (chưa hiệu lực tại ngày đặt đơn).
    Input: query (câu hỏi), platform, order_date ("YYYY-MM-DD", None = không lọc ngày);
           tuỳ chọn: policy_type ("fee" | "voucher" | "ads" | "return_refund" | "settlement" | "" = mọi loại), k = số đoạn tối đa.
    Output: top-k [{"chunk_id", "url", "effective_date", "text", "score"}]; [] khi sàn chưa có kho
            hoặc không đoạn nào đủ gần → không tự đoán, chunk_id để null.
    Không tác động ra ngoài (đọc data/<thư mục sàn>/policies/ qua codebase/retrieval.py, gọi API embedding cho câu hỏi)."""
    from retrieval import search   # kho từng sàn: codebase/policy_paths.py
    hits = search(query, platform=platform, policy_type=policy_type, k=max(int(k), 1) * 3)

    def in_effect(h):
        d = str(h.get("effective_date") or "")[:10]
        return not order_date or d in ("", "null", "None") or d <= order_date

    return [{"chunk_id": h["chunk_id"], "url": h.get("url"), "effective_date": h.get("effective_date"),
             "text": h.get("text"), "score": h.get("score")} for h in hits if in_effect(h)][:max(int(k), 1)]


@tool
def expected_amount(rule_id: str, base_amount: int, actual_amount: int = None, qty: int = 1,
                    shop_rate: float = None) -> dict:
    """Tính số tiền đúng luật của một dòng và độ lệch so với số bị trừ.
    Input: rule_id; base_amount = số tiền căn cứ (đơn đa số luật: giá × SL - voucher shop);
           actual_amount = số bị trừ trên đơn (âm) để tính delta; qty = số lượng (cho luật có trần mỗi sản phẩm);
           shop_rate = tỉ lệ % shop tự đặt (luật base "theo_shop", vd tiếp thị liên kết).
    Output: {"rule_id", "expected": int (âm), "actual": int | None, "delta": int | None, "rate": float | None,
             "cap_vnd": int | None, "capped": bool}  (delta = actual - expected).
    Không tác động ra ngoài."""
    # BẢN TẠM (Thái thay bằng fee_engine.amount_for, TH-5): chỉ biết luật của đơn mẫu DEMO-0412.
    r = next((x for x in _DEMO_RULES if x["rule_id"] == rule_id), None)
    if r is None:
        return {"rule_id": rule_id, "expected": None, "actual": actual_amount, "delta": None, "rate": None,
                "cap_vnd": None, "capped": False, "error": "không có luật này trong bảng phí"}
    rate = shop_rate if r["base"] == "theo_shop" else r["rate"]
    if r["base"] == "don":
        amt, capped = r["per_order_vnd"] or 0, False
    else:
        amt = round(int(base_amount) * (rate or 0) / 100)
        capped = bool(r["cap_vnd"]) and amt > r["cap_vnd"] * qty
        amt = min(amt, r["cap_vnd"] * qty) if r["cap_vnd"] else amt
    expected = -int(amt)
    delta = None if actual_amount is None else int(actual_amount) - expected
    return {"rule_id": rule_id, "expected": expected, "actual": actual_amount, "delta": delta, "rate": rate,
            "cap_vnd": r["cap_vnd"], "capped": capped}


@tool
def unit_profit(price: int, lines: list, cogs: int) -> dict:
    """Tiền về và lãi thật của một đơn, phần lãi mà từng công tắc ăn mất.
    Input: price = giá bán × số lượng - voucher shop (dương; voucher shop không phải dòng phí, nó giảm số căn cứ);
           lines = các khoản phí bị trừ (âm, có "type"); cogs = giá vốn cả đơn (giá vốn 1 sp × số lượng).
    Output: {"payout": int, "cogs": int, "profit": int,
             "switches": [{"name", "amount" (dương), "share_of_profit"}] lớn nhất trước}.
    Không tác động ra ngoài."""
    # BẢN TẠM (Thái thay, TH-5): phép tính đơn giản.
    payout = int(price) + sum(int(x.get("amount") or 0) for x in lines)
    profit = payout - int(cogs)
    sw = [{"name": x["name"], "amount": -int(x["amount"]),
           "share_of_profit": round(-int(x["amount"]) / profit, 3) if profit > 0 else None}
          for x in lines if x.get("type") == "cong_tac" and int(x.get("amount") or 0) < 0]
    sw.sort(key=lambda s: -s["amount"])
    return {"payout": payout, "cogs": int(cogs), "profit": profit, "switches": sw}


@tool
def switch_what_if(lines: list, switch: str, new_value: int, profit: int = None) -> dict:
    """Nếu đổi một công tắc thì lãi mỗi đơn thay đổi bao nhiêu.
    Input: lines = các khoản trừ của đơn; switch = tên dòng công tắc (đúng "name" trong lines);
           new_value = số tiền MỚI của dòng đó (âm; 0 = tắt), lấy từ expected_amount với tỉ lệ mới;
           profit = lãi hiện tại mỗi đơn (để tính số đơn được phép giảm).
    Output: {"switch", "old_amount", "new_amount", "gain_per_order", "profit_after": int | None,
             "max_order_drop_pct": float | None}
            (max_order_drop_pct: số đơn được phép giảm tối đa bao nhiêu % mà tổng lãi không thấp hơn trước).
    Không tác động ra ngoài."""
    # BẢN TẠM (Thái thay, TH-5): phép tính đơn giản.
    line = next((x for x in lines if x.get("name") == switch), None)
    if line is None:
        return {"switch": switch, "error": "không có dòng này trong lines"}
    old = int(line["amount"])
    gain = int(new_value) - old
    after = None if profit is None else int(profit) + gain
    drop = round(gain / after * 100, 1) if after and after > 0 and gain > 0 else None
    return {"switch": switch, "old_amount": old, "new_amount": int(new_value), "gain_per_order": gain,
            "profit_after": after, "max_order_drop_pct": drop}


@tool
def breakeven_roas(margin_before_ads: float) -> dict:
    """ROAS hoà vốn = 1 ÷ biên lãi trước quảng cáo.
    Input: margin_before_ads = biên lãi trước quảng cáo dạng tỉ lệ (0 < m ≤ 1), vd 0.25.
    Output: {"margin_before_ads": float, "breakeven_roas": float | None} (None nếu biên lãi ≤ 0).
    Không tác động ra ngoài."""
    m = float(margin_before_ads)
    return {"margin_before_ads": m, "breakeven_roas": round(1 / m, 2) if m > 0 else None}


@tool
def compare_platforms(orders: list, cogs: int) -> dict:
    """So lãi thật của cùng một sản phẩm trên ≥ 2 sàn.
    Input: orders = [{"platform", "order_id", "product", "price", "qty", "lines"}] (price = giá × SL - voucher shop);
           cogs = giá vốn MỘT sản phẩm.
    Output: {"product", "rows": [{"platform", "order_id", "profit", "top_switch"}], "best_platform"}
            hoặc {"error"} nếu chưa đủ 2 sàn. Khớp SessionResult.platform_comparison (H4).
    Không tác động ra ngoài."""
    # BẢN TẠM (Thái thay, TH-5): phép tính đơn giản trên số đơn đưa vào.
    if len({o.get("platform") for o in orders}) < 2:
        return {"error": "cần ít nhất 2 sàn cùng sản phẩm"}
    rows = []
    for o in orders:
        payout = int(o["price"]) + sum(int(x.get("amount") or 0) for x in o.get("lines", []))
        sw = [x for x in o.get("lines", []) if x.get("type") == "cong_tac"]
        top = min(sw, key=lambda x: int(x["amount"]))["name"] if sw else None
        rows.append({"platform": o["platform"], "order_id": o.get("order_id"),
                     "profit": payout - int(cogs) * int(o.get("qty") or 1), "top_switch": top})
    best = max(rows, key=lambda r: r["profit"])["platform"]
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
