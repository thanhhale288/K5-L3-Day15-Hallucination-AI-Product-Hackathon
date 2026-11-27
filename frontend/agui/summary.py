"""Phần dùng chung của cầu AG-UI và script sinh mẫu: tóm tắt bằng chữ và thông tin công tắc.

Chỉ ghép số có sẵn trong AgentResult / SessionResult. Riêng `switch_info` suy số căn cứ (giá × SL − voucher shop)
từ các dòng phí bắt buộc tính theo tỉ lệ, để giao diện biết tỉ lệ hiện tại của từng công tắc khi chủ shop thử đổi.
`rule_by_id` là `tools._rule_by_id` (bảng phí của nhóm), truyền vào để file này không phụ thuộc đường dẫn import.
"""
from __future__ import annotations

PLATFORM = {"shopee": "Shopee", "tiktok": "TikTok Shop", "lazada": "Lazada"}


def vnd(n) -> str:
    if n is None:
        return "—"
    s = f"{abs(int(n)):,}".replace(",", ".") + "đ"
    return "−" + s if n < 0 else s


# ── Tóm tắt bằng chữ: chỉ ghép số có sẵn trong result (không tính thêm) ──
def summarize_order(r: dict) -> str:
    where = f"Đơn {r.get('order_id') or ''} ({PLATFORM.get(r.get('platform'), 'chưa rõ sàn')})".strip()
    d = r.get("decision")
    if d == "refuse":
        return r.get("refusal_reason") or "Mình không hỗ trợ yêu cầu này."
    if d == "ask":
        return f"{where}: {r.get('question') or 'mình cần thêm thông tin.'}"
    parts = [f"{where}: tiền về {vnd(r.get('payout'))}, lãi thật **{vnd(r.get('profit'))}**."]
    sw = (r.get("switches") or [None])[0]
    if sw:
        share = sw.get("share_of_profit")
        parts.append(f"Công tắc ăn nhiều nhất là **{sw['name']}** ({vnd(sw['amount'])}"
                     + (f", {round(share * 100)}% phần lãi" if share is not None else "") + ").")
    bad = [ln["name"] for ln in r.get("lines") or []
           if ln.get("type") == "khong_khop" or (ln.get("delta") or 0) != 0]
    if d == "escalate" and bad:
        parts.append(f"Có {len(bad)} khoản cần hỏi lại sàn: {', '.join(bad)}. Mình đã soạn nháp, bạn đọc lại rồi tự gửi.")
    for a in (r.get("actions") or [])[:1]:
        gain = a.get("gain_per_order")
        parts.append(f"Gợi ý: {a['text']}" + (f" (+{vnd(gain)} mỗi đơn)." if gain else "."))
    return " ".join(parts)


def summarize(result: dict) -> str:
    if "orders" not in result:
        return summarize_order(result)
    lines = [f"Mình đã soi {len(result['orders'])} đơn."]
    pc = result.get("platform_comparison")
    if pc:
        best = next((x for x in pc["rows"] if x["platform"] == pc["best_platform"]), {})
        per = best.get("profit_per_unit", best.get("profit"))
        lines.append(f"Cùng sản phẩm {pc['product']}, **{PLATFORM.get(pc['best_platform'])}** lãi nhất ({vnd(per)} mỗi sản phẩm).")
    lines += ["- " + summarize_order(o) for o in result["orders"]]
    return "\n".join(lines)


def _base_of(o: dict, rule_by_id):
    """Số căn cứ (giá × SL − voucher shop) suy từ các dòng bắt buộc tính theo tỉ lệ trên căn cứ đó
    (vd phí cố định 9% = −17.010đ → 189.000đ). Lấy trung vị (các dòng đã làm tròn nên lệch vài đồng)."""
    seen = []
    for ln in o.get("lines") or []:
        r = rule_by_id(ln.get("rule_id")) if ln.get("rule_id") else None
        if r and r.get("base") == "gia_sau_voucher_shop" and r.get("rate") and not r.get("cap_vnd") \
                and ln.get("delta") == 0 and ln.get("type") == "bat_buoc":
            seen.append(round(-ln["amount"] * 100 / float(r["rate"])))
    return sorted(seen)[len(seen) // 2] if seen else None


def switch_info(result: dict, rule_by_id) -> list:
    """Với mỗi công tắc: tỉ lệ hiện tại (để giao diện đặt sẵn thanh trượt) và căn cứ dùng khi thử đổi."""
    out = []
    for o in result.get("orders") or [result]:
        base = _base_of(o, rule_by_id)
        for ln in o.get("lines") or []:
            if ln.get("type") != "cong_tac":
                continue
            r = rule_by_id(ln.get("rule_id")) if ln.get("rule_id") else None
            rate = round(-ln["amount"] * 100 / base, 1) if base else None
            out.append({"order_id": o.get("order_id"), "switch": ln["name"], "amount": ln["amount"],
                        "current_rate": rate, "base": base, "cap_vnd": (r or {}).get("cap_vnd"),
                        "can_change_rate": bool(base and ln.get("rule_id"))})
    return out
