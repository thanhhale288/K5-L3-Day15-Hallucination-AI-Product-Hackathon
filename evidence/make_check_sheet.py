#!/usr/bin/env python3
"""HA-4: chọn 30 dòng nhãn AI để người kiểm tay, rồi ghép kết quả kiểm về labels-ai.csv.

  python evidence/make_check_sheet.py          # tạo evidence/reviews/raw-check-30.csv (có nguyên văn, KHÔNG commit)
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
SHEET = HERE / "reviews" / "raw-check-30.csv"
GROUPS = [("co_nhan_tu_khoa", "1", 12), ("co_nhan_tu_khoa", "0", 6),
          ("ngau_nhien_khong_nhan", "1", 6), ("ngau_nhien_khong_nhan", "0", 6)]
COLS = ["stt", "review_key", "app", "score", "content",
        "ai_is_seller_pain", "ai_topic", "ai_mentions_profit", "human_check", "ghi_chu_nguoi_kiem"]


def make() -> None:
    labels = list(csv.DictReader(LABELS.open(encoding="utf-8")))
    text = {r["review_key"]: r["content"] for r in csv.DictReader(RAW.open(encoding="utf-8-sig"))}
    rng = random.Random(2026)
    picked = []
    for mau, pain, k in GROUPS:
        pool = sorted((r for r in labels if r["mau"] == mau and r["is_seller_pain"] == pain), key=lambda r: r["review_key"])
        picked += rng.sample(pool, k)
    with SHEET.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        for i, r in enumerate(picked, 1):
            w.writerow({"stt": i, "review_key": r["review_key"], "app": r["app"], "score": r["score"],
                        "content": text[r["review_key"]], "ai_is_seller_pain": r["is_seller_pain"],
                        "ai_topic": r["topic"], "ai_mentions_profit": r["mentions_profit"],
                        "human_check": r["human_check"], "ghi_chu_nguoi_kiem": ""})
    print(f"Đã tạo {SHEET.relative_to(HERE.parent)} ({len(picked)} dòng). Mở bằng Excel / Google Sheets, điền cột human_check.")


def merge() -> None:
    checks = {r["review_key"]: r["human_check"].strip() for r in csv.DictReader(SHEET.open(encoding="utf-8-sig"))}
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
