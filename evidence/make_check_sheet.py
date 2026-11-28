#!/usr/bin/env python3
"""HA-4: chọn 30 dòng nhãn AI để người kiểm tay, rồi ghép kết quả kiểm về labels-ai.csv.

  python evidence/make_check_sheet.py          # tạo evidence/reviews/raw-check-30.xlsx (có nguyên văn, KHÔNG commit)
  python evidence/make_check_sheet.py --merge  # chép cột human_check từ file kiểm về labels-ai.csv
  python evidence/count_reviews.py             # mục 5 in tỉ lệ khớp

30 dòng chia theo nhóm (random.Random(2026), chạy lại ra cùng 30 dòng):
  12 · mẫu A, AI nói là pain của người bán     (kiểm có than thật không, nhãn chủ đề đúng không)
   6 · mẫu A, AI nói KHÔNG phải pain           (bộ lọc từ khoá bắt nhầm thật hay AI bỏ sót)
   6 · mẫu B, AI nói là pain                   (từ khoá bỏ sót thật không)
   6 · mẫu B, AI nói KHÔNG phải pain
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = HERE / "reviews" / "labels-ai.csv"
RAW = HERE / "reviews" / "raw-label-sheet.csv"
SHEET = HERE / "reviews" / "raw-check-30.xlsx"  # xlsx để cột content tự xuống dòng
GROUPS = [("co_nhan_tu_khoa", "1", 12), ("co_nhan_tu_khoa", "0", 6),
          ("ngau_nhien_khong_nhan", "1", 6), ("ngau_nhien_khong_nhan", "0", 6)]
COLS = ["stt", "review_key", "app", "score", "content",
        "ai_is_seller_pain", "ai_topic", "ai_mentions_profit", "human_check", "ghi_chu_nguoi_kiem"]


def make() -> None:
    if SHEET.exists() and "--force" not in sys.argv:
        sys.exit(f"{SHEET.name} đã có (có thể đã điền dở). Thêm --force nếu muốn tạo lại từ đầu.")
    labels = list(csv.DictReader(LABELS.open(encoding="utf-8")))
    text = {r["review_key"]: r["content"] for r in csv.DictReader(RAW.open(encoding="utf-8-sig"))}
    rng = random.Random(2026)
    picked = []
    for mau, pain, k in GROUPS:
        pool = sorted((r for r in labels if r["mau"] == mau and r["is_seller_pain"] == pain), key=lambda r: r["review_key"])
        picked += rng.sample(pool, k)
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "kiem-tay"
    ws.append(COLS)
    for i, r in enumerate(picked, 1):
        ws.append([i, r["review_key"], r["app"], int(r["score"]), text[r["review_key"]], r["is_seller_pain"],
                   r["topic"], r["mentions_profit"], r["human_check"], ""])
    widths = {"stt": 5, "review_key": 14, "app": 14, "score": 6, "content": 70, "ai_is_seller_pain": 9,
              "ai_topic": 18, "ai_mentions_profit": 9, "human_check": 24, "ghi_chu_nguoi_kiem": 30}
    for j, c in enumerate(COLS, 1):
        ws.column_dimensions[ws.cell(1, j).column_letter].width = widths[c]
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for cell in ws[1]:
        cell.font = Font(bold=True)
    fill = PatternFill("solid", fgColor="FFF2CC")
    for row in ws.iter_rows(min_row=2, min_col=COLS.index("human_check") + 1, max_col=COLS.index("human_check") + 1):
        row[0].fill = fill
    ws.freeze_panes = "A2"
    wb.save(SHEET)
    print(f"Đã tạo {SHEET.relative_to(HERE.parent)} ({len(picked)} dòng). Mở bằng Excel / Numbers / Google Sheets, điền cột human_check (tô vàng).")


def merge() -> None:
    from openpyxl import load_workbook

    ws = load_workbook(SHEET).active
    head = [c.value for c in ws[1]]
    ki, hi = head.index("review_key"), head.index("human_check")
    checks = {row[ki]: str(row[hi] or "").strip() for row in ws.iter_rows(min_row=2, values_only=True) if row[ki]}
    rows = list(csv.DictReader(LABELS.open(encoding="utf-8")))
    bad = [k for k, v in checks.items() if v and v != "dong_y" and not v.startswith("sua:")]
    if bad:
        sys.exit(f"human_check chỉ nhận 'dong_y' hoặc 'sua:...'. Sai ở: {bad}")
    n = 0
    for r in rows:
        if checks.get(r["review_key"]):
            r["human_check"] = checks[r["review_key"]]
            n += 1
    with LABELS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Đã ghép {n}/{len(checks)} dòng vào {LABELS.relative_to(HERE.parent)}.")


if __name__ == "__main__":
    merge() if "--merge" in sys.argv else make()
