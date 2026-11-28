#!/usr/bin/env python3
"""Sinh JSON mẫu đúng hợp đồng H4 (`codebase/schema.py`) để frontend làm trước khi có agent thật.

Mọi con số do công cụ của nhóm tính (`codebase/tools.py`, bọc `data/fee_engine.py`), đầu vào là
`data/synthetic/orders.csv` + `order_lines.csv` + `pastes.jsonl`. KHÔNG đọc file đáp án (*_answers.csv).
Đây là "agent giả bằng tay": thứ tự gọi công cụ cố định, không có LLM. Câu từ chối là chữ mẫu.

  python frontend/samples/make_samples.py      # ghi lại frontend/samples/*.json + index.json
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "codebase"))
import schema  # noqa: E402
import tools  # noqa: E402

sys.path.insert(0, str(ROOT / "frontend" / "agui"))
from summary import summarize, switch_info  # noqa: E402

OUT = Path(__file__).resolve().parent
SYN = ROOT / "data" / "synthetic"

ORDERS = {r["order_id"]: r for r in csv.DictReader((SYN / "orders.csv").open(encoding="utf-8"))}
LINES = defaultdict(list)
for r in csv.DictReader((SYN / "order_lines.csv").open(encoding="utf-8")):
    LINES[r["order_id"]].append(r)
PASTES = {}
for raw in (SYN / "pastes.jsonl").open(encoding="utf-8"):
    p = json.loads(raw)
    PASTES.setdefault(tuple(p["order_ids"]), p)


def call(fn, *a, **kw):
    """Gọi phần thân của @tool (bỏ lớp ghi trace, vì đây không phải một lượt chạy)."""
    return getattr(fn, "__wrapped__", fn)(*a, **kw)


def soi(order_id: str, trace: str) -> dict:
    o = ORDERS[order_id]
    qty = int(o["qty"])
    base = int(o["gia_ban"]) * qty - int(o["voucher_shop"] or 0)
    lines = []
    for ln in LINES[order_id]:
        amt = int(ln["amount_vnd"])
        r = call(tools.lookup_fee_rule, ln["ten_dong"], o["order_date"], o["shop_type"], o["nganh"], o["platform"])
        if r is None:
            lines.append({"name": ln["ten_dong"], "amount": amt, "type": "khong_khop"})
            continue
        if r["base"] == "theo_shop":  # tỉ lệ shop tự đặt: suy từ chính dòng đó
            e = call(tools.expected_amount, r["rule_id"], base, amt, qty, shop_rate=round(-amt * 100 / base, 2))
        elif r["base"] == "voucher_dong_tai_tro":  # giá trị mã không có trong chữ dán → không kiểm được
            e = {"expected": amt, "delta": 0}
        else:
            e = call(tools.expected_amount, r["rule_id"], base, amt, qty)
        lines.append({"name": ln["ten_dong"], "amount": amt, "type": r["loai"], "rule_id": r["rule_id"],
                      "expected": e["expected"], "delta": e["delta"], "chunk_id": r["chunk_id"] or None,
                      "source_url": r["nguon_url"] or None})

    res = dict(platform=o["platform"], order_id=order_id, order_date=o["order_date"], lines=lines,
               payout=int(o["payout"]), trace_id=trace)
    if not o["gia_von"]:
        return schema.agent_result(decision="ask", **res, question=(
            f"Giá vốn của \"{o['ten_sp']}\" là bao nhiêu? Chưa có giá vốn thì chưa tính được lãi thật."))

    up = call(tools.unit_profit, base, lines, int(o["gia_von"]) * qty)
    res.update(cogs=up["cogs"], profit=up["profit"], switches=up["switches"])
    actions = []
    for s in up["switches"][:2]:
        x = next(ln for ln in lines if ln["name"] == s["name"])
        rate = round(-x["amount"] * 100 / base)
        if x["rule_id"] and "lien_ket" in x["rule_id"] and rate > 6:
            new = call(tools.expected_amount, x["rule_id"], base, None, qty, shop_rate=6)["expected"]
            w = call(tools.switch_what_if, lines, s["name"], new, up["profit"])
            actions.append({"text": f"Hạ hoa hồng tiếp thị liên kết từ {rate}% xuống 6%",
                            "gain_per_order": w["gain_per_order"]})
        else:
            w = call(tools.switch_what_if, lines, s["name"], 0, up["profit"])
            drop = w["max_order_drop_pct"]
            actions.append({"text": f"Thử tắt {s['name']}" + (
                f": chỉ lợi nếu số đơn giảm dưới {drop:.0f}%" if drop is not None else ""),
                "gain_per_order": w["gain_per_order"]})
    res["actions"] = actions

    bad = [ln for ln in lines if ln["type"] == "khong_khop" or (ln.get("delta") or 0) != 0]
    if bad:
        x = bad[0]
        d = call(tools.draft_platform_question, order_id, x["name"], x.get("expected"), x["amount"])
        return schema.agent_result(decision="escalate", **res, draft_to_platform=d["draft"])
    return schema.agent_result(decision="act", **res)


def session(order_ids: list[str], trace: str) -> dict:
    orders = [soi(oid, f"{trace}/{i}") for i, oid in enumerate(order_ids, 1)]
    o0 = ORDERS[order_ids[0]]
    cmp_in = [{"platform": r["platform"], "order_id": r["order_id"], "product": o0["product_id"],
               "price": int(ORDERS[r["order_id"]]["gia_ban"]) * int(ORDERS[r["order_id"]]["qty"])
               - int(ORDERS[r["order_id"]]["voucher_shop"] or 0),
               "qty": int(ORDERS[r["order_id"]]["qty"]), "lines": r["lines"]} for r in orders]
    pc = call(tools.compare_platforms, cmp_in, int(o0["gia_von"]))
    return schema.session_result(orders, platform_comparison=pc, session_state_id=None, trace_id=trace)


def find(pred) -> str:
    for oid in ORDERS:
        if oid.startswith(("SHP", "TTS", "LZD")) and pred(oid):
            return oid
    raise SystemExit("không tìm thấy đơn phù hợp")


def is_escalate_delta(oid: str) -> bool:
    o = ORDERS[oid]
    if not o["gia_von"] or o["status"] != "hoan_tat":
        return False
    r = soi(oid, "x")
    return r["decision"] == "escalate" and any((ln["delta"] or 0) != 0 for ln in r["lines"])


def import_demo() -> None:
    """Màn import (HA-14): chạy data/import_export.py trên bộ file demo giả lập, chép phan_tich.json về đây.
    Đây là data giả "Shop Demo", được commit; export thật của shop thì không (data/imported/ bị gitignore)."""
    import glob
    import subprocess
    out = ROOT / "data" / "imported" / "demo"
    files = sorted(glob.glob(str(ROOT / "data" / "demo_import" / "*_don_hang_*.xlsx")))
    subprocess.run([sys.executable, str(ROOT / "data" / "import_export.py"), *files,
                    "--cogs", str(ROOT / "data" / "demo_import" / "gia_von_mau.xlsx"), "--out", str(out)],
                   check=True, stdout=subprocess.DEVNULL)
    (OUT / "import-thang-11.json").write_text((out / "phan_tich.json").read_text(encoding="utf-8"), encoding="utf-8")
    print("import-thang-11.json       (data/import_export.py)")


def main() -> None:
    refuse_paste = PASTES[()]["text"]
    esc = find(lambda oid: ORDERS[oid]["platform"] == "shopee" and is_escalate_delta(oid))
    ask = find(lambda oid: not ORDERS[oid]["gia_von"] and ORDERS[oid]["status"] == "hoan_tat")
    trio = ["LZD-261101-0005", "SHP-261101-0006", "TTS-261101-0005"]
    samples = [
        ("demo-0412.json", "Shopee · có dòng phí lạ", ("DEMO-0412",), soi("DEMO-0412", "mau/0001")),
        ("act-lazada.json", "Lazada · affiliate ăn lãi", ("LZD-260324-0049",),
         soi("LZD-260324-0049", "mau/0006")),
        ("escalate-lech-luat.json", "Shopee · phí cố định lệch luật", (esc,), soi(esc, "mau/0002")),
        ("session-3-san.json", "Cùng sản phẩm, 3 sàn", tuple(trio), session(trio, "mau/0003")),
        ("ask-thieu-gia-von.json", "Thiếu giá vốn", (ask,), soi(ask, "mau/0004")),
        ("refuse.json", "Yêu cầu né thuế", (), schema.agent_result(
            decision="refuse", trace_id="mau/0005", refusal_reason=(
                "Mình không hỗ trợ khai giá thấp để giảm thuế khấu trừ. Mình có thể soi các khoản phí "
                "trên đơn để bạn biết khoản nào chỉnh được hợp lệ."))),
    ]
    index = []
    for name, label, ids, data in samples:
        errs = (schema.validate_session_result if "orders" in data else schema.validate_agent_result)(data)
        assert not errs, f"{name}: {errs}"
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        paste = refuse_paste if not ids else PASTES.get(ids, {}).get("text")
        index.append({"file": name, "label": label, "order_ids": list(ids), "decision": data["decision"],
                      "paste": paste, "summary": summarize(data),
                      "switch_info": switch_info(data, tools._rule_by_id)})
        print(f"{name:26s} {data['decision']:9s} {' '.join(ids)}")
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    import_demo()
    d = samples[0][3]
    assert (d["payout"], d["profit"]) == (123_520, 28_520), "DEMO-0412 phải ra 123.520 / 28.520"


if __name__ == "__main__":
    main()
