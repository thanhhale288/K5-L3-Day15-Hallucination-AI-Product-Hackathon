"""Phần dùng chung của cầu AG-UI và script sinh mẫu: tóm tắt bằng chữ và thông tin công tắc.

Chỉ ghép số có sẵn trong AgentResult / SessionResult. Riêng `switch_info` suy số căn cứ (giá × SL − voucher shop)
từ các dòng phí bắt buộc tính theo tỉ lệ, để giao diện biết tỉ lệ hiện tại của từng công tắc khi chủ shop thử đổi.
`rule_by_id` là `tools._rule_by_id` (bảng phí của nhóm), truyền vào để file này không phụ thuộc đường dẫn import.
"""
from __future__ import annotations

import re

PLATFORM = {"shopee": "Shopee", "tiktok": "TikTok Shop", "lazada": "Lazada"}


def vnd(n) -> str:
    if n is None:
        return "—"
    s = f"{abs(int(n)):,}".replace(",", ".") + "đ"
    return "−" + s if n < 0 else s


# ── Tóm tắt bằng chữ: 1–2 câu, chỉ ghép số có sẵn trong result (không tính thêm) ──
# Chi tiết (từng dòng phí, công tắc, gợi ý, nháp) đã nằm ở panel kết quả, chat không nhắc lại.
def summarize_order(r: dict) -> str:
    d = r.get("decision")
    if d == "refuse":
        return r.get("refusal_reason") or "Mình không hỗ trợ yêu cầu này."
    if d == "ask":
        return r.get("question") or "Mình cần thêm thông tin."
    parts = [f"Lãi thật **{vnd(r.get('profit'))}** mỗi đơn."]
    bad = [ln["name"] for ln in r.get("lines") or []
           if ln.get("type") == "khong_khop" or (ln.get("delta") or 0) != 0]
    if d == "escalate" and bad:
        parts.append(f"Nên hỏi sàn về **{', '.join(bad)}**, mình đã soạn nháp.")
    elif r.get("switches"):
        parts.append(f"**{r['switches'][0]['name']}** ăn lãi nhiều nhất.")
    return " ".join(parts)


def summarize(result: dict) -> str:
    if result.get("kind") == "policy_answer":   # hỏi đáp chính sách: câu đầu của câu trả lời, phần đủ ở panel kết quả
        text = " ".join(str(result.get("answer") or "").split())
        first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
        first = first if len(first) <= 220 else first[:220].rsplit(" ", 1)[0] + "…"
        n = len(result.get("citations") or [])
        return first + (" (%d nguồn, chi tiết bên cạnh)" % n if n else "")
    if "orders" not in result:
        return summarize_order(result)
    pc = result.get("platform_comparison")
    if pc:
        return f"Đã soi {len(result['orders'])} đơn. **{PLATFORM.get(pc['best_platform'])}** lãi nhất cho {pc['product']}."
    return f"Đã soi {len(result['orders'])} đơn, xem từng đơn bên cạnh."


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
