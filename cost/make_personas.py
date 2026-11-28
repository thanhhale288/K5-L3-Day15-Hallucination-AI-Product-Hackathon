#!/usr/bin/env python3
"""TH-9 (Hà làm thay Thái): sinh cost/personas.yaml cho `python run.py simulate`.

  python cost/make_personas.py          # ghi đè cost/personas.yaml (seed cố định, chạy lại ra cùng file)

Đầu vào của từng persona lấy từ data/synthetic/pastes.jsonl (chữ dán giả lập, agent được đọc).
Không đọc file đáp án (*_answers.csv). Chữ dán chọn theo dấu hiệu trên chính chữ dán:
  soi_1_don      đơn một sàn, có dòng giá vốn, không có khoản lạ
  so_3_san       nhiều đơn, đủ 3 sàn (cùng sản phẩm)
  thieu_gia_von  đơn không có dòng giá vốn → agent hỏi (Ask); lượt 2 dán lại kèm giá vốn
  dong_la        đơn có khoản lạ ("Phí dịch vụ khác"…) → thường Escalate

Bộ đọc YAML của khung chỉ nhận chuỗi một dòng, nên xuống dòng trong chữ dán đổi thành " | ".
Khung không giữ phiên giữa hai lượt (mỗi lượt gọi answer() riêng), nên lượt "làm tiếp" của thieu_gia_von
được mô phỏng bằng cách dán lại đơn kèm giá vốn, và hai lượt lấy ngẫu nhiên từ cùng một bộ đầu vào.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASTES = ROOT / "data" / "synthetic" / "pastes.jsonl"
OUT = ROOT / "cost" / "personas.yaml"
PER_POOL = 8  # số chữ dán mỗi persona
COGS_REPLY = "Giá vốn: 120.000đ"  # câu trả lời Ask chỉ để đo token (tự ước tính)

HAS_COGS = re.compile(r"vốn", re.I)
ODD_LINE = re.compile(r"phí dịch vụ khác|phí khác|khoản khác|điều chỉnh", re.I)


def one_line(text: str) -> str:
    s = " | ".join(x.strip() for x in text.strip().splitlines() if x.strip())
    assert '"' not in s and "#" not in s, "chữ dán có ký tự bộ đọc YAML của khung không nhận"
    return s


def pools(rows: list[dict], rng: random.Random) -> dict[str, list[str]]:
    don = [r for r in rows if r["kind"] == "don"]
    by = {
        "soi_1_don": [r for r in don if HAS_COGS.search(r["text"]) and not ODD_LINE.search(r["text"])],
        "so_3_san": [r for r in rows if r["kind"] == "nhieu_don" and len({i[:3] for i in r["order_ids"]}) == 3],
        "thieu_gia_von": [r for r in don if not HAS_COGS.search(r["text"])],
        "dong_la": [r for r in don if ODD_LINE.search(r["text"])],
    }
    out = {}
    for name, rs in by.items():
        rs = sorted(rs, key=lambda r: r["paste_id"])
        picked = rng.sample(rs, min(PER_POOL, len(rs)))
        texts = [one_line(r["text"]) for r in picked]
        if name == "thieu_gia_von":  # lượt 2: dán lại kèm giá vốn
            texts += [t + " | " + COGS_REPLY for t in texts]
        out[name] = texts
    return out


PERSONAS = [
    # name, share, uses/tháng, lượt/phiên, mô tả
    ("soi_1_don", 0.45, 6, 1, "dán 1 đơn vừa về tiền, đủ giá vốn"),
    ("so_3_san", 0.20, 4, 1, "dán 3 đơn cùng sản phẩm ở 3 sàn để so"),
    ("thieu_gia_von", 0.20, 8, 2, "quên giá vốn → agent hỏi → trả lời rồi làm tiếp"),
    ("dong_la", 0.15, 8, 1, "đơn có khoản lạ → agent soạn nháp hỏi sàn"),
]

PERSONA_SOURCE = (
    "(tự ước tính) theo câu chuyện 3 kịch bản ở cost/cost-estimate.md mục 1 (HA-12): shop đa sàn soát đơn 4–8 lần / tháng, "
    "khoảng 1/3 phiên có Ask hoặc Escalate; tỉ lệ từng kiểu chưa có số đo trên shop thật"
)

PRICES = [
    ("deepseek-chat (V4 Flash)", 0.14, 0.28,
     "giá input không cache, như trang https://api-docs.deepseek.com/quick_start/pricing hiện trong kết quả tìm kiếm 28/11/2026 · "
     "trang chính thức không mở được từ máy nhóm (kết nối bị từ chối), cần mở trình duyệt đối chiếu"),
    ("deepseek-v4.1-flash giờ cao điểm", 0.30, 1.20,
     "trang tổng hợp bên thứ ba qua tìm kiếm 28/11/2026, vd https://developer.puter.com/tutorials/deepseek-api-pricing/ · cần đối chiếu"),
    ("deepseek-v4-pro", 1.32, 3.96,
     "trang tổng hợp bên thứ ba qua tìm kiếm 28/11/2026 (giá sau đợt tăng 16/08/2026), "
     "vd https://karozieminski.substack.com/p/deepseek-v4-pricing-verified-discrepancy-2026 · cần đối chiếu"),
]


def main() -> None:
    rows = [json.loads(line) for line in PASTES.open(encoding="utf-8")]
    inputs = pools(rows, random.Random(2026))
    lines = [
        "# Mô phỏng chi phí khi dùng thật (TH-9, Hà làm thay Thái). FILE SINH TỰ ĐỘNG:",
        "#   python cost/make_personas.py   → sửa số / nguồn trong script đó, đừng sửa tay ở đây.",
        "# Chạy: python run.py simulate --rate-from eval/run-2.csv",
        "# Mọi số có nguồn hoặc ghi rõ (tự ước tính). Đầu vào lấy từ data/synthetic/pastes.jsonl (không đọc file đáp án).",
        "",
        "sessions: 50",
        "seed: 42",
        "",
        "users:  # số shop dùng / tháng ở 3 kịch bản",
        "  low: 1800",
        "  base: 9000",
        "  high: 27000",
        '  source: "~601.800 shop có đơn năm 2025 (Metric, CONTEXT.md) × 30% bán ≥2 sàn (tự ước tính) × 1% / 5% / 15% dùng '
        '(tự ước tính) — câu chuyện 3 kịch bản ở cost/cost-estimate.md mục 1"',
        "",
        "personas:",
    ]
    for name, share, uses, turns, desc in PERSONAS:
        lines += [
            f"  - name: {name}  # {desc}",
            f"    share: {share}",
            f"    uses_per_month: {uses}",
            f"    turns_per_session: {turns}",
            f'    source: "{PERSONA_SOURCE}"',
            "    inputs:",
        ]
        lines += [f'      - "{t}"' for t in inputs[name]]
    lines += ["", "prices:  # USD / 1 triệu token, tính MỌI token vào theo giá không cache (thận trọng)"]
    for model, inp, outp, src in PRICES:
        lines += [f"  - model: {model}", f"    input: {inp}", f"    output: {outp}", f'    source: "{src}"']
    lines += [
        "",
        "usd_to_vnd:",
        "  rate: 25000",
        '  source: "(tự ước tính) làm tròn, chưa lấy tỷ giá ngân hàng ngày chạy"',
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {OUT.relative_to(ROOT)}: " + ", ".join(f"{k} {len(v)} đầu vào" for k, v in inputs.items()))


if __name__ == "__main__":
    main()
