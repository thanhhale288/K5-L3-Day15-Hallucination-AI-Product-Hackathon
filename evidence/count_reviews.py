#!/usr/bin/env python3
"""Đếm x/N từ nhãn review (HA-4). Chạy lại phải ra cùng số.

  python evidence/count_reviews.py            # in bảng số, dùng cho evidence/data-mining.md và summary.md

Đầu vào: evidence/reviews/labels-ai.csv (nhãn, không chứa nguyên văn review — được commit).
Tổng 900 và số review không có nhãn từ khoá lấy từ evidence/reviews/raw-label-sheet.csv nếu có (không commit);
không có file thô thì dùng hằng số đã ghi ở dưới.

Mẫu:
  A = mọi review mà bộ lọc từ khoá gợi ý có nhãn tiền (goi_y_nhan khác "khac").
  B = 100 review ngẫu nhiên (random.Random(42)) trong số review bộ lọc gắn "khac", để đo phần từ khoá bỏ sót.
"Pain về tiền" = is_seller_pain=1 VÀ topic có ít nhất một trong MONEY.
Nhãn do AI gán (labeler = ai:…); cột human_check để người kiểm điền dong_y / sua:<nhãn đúng>.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = HERE / "reviews" / "labels-ai.csv"
RAW = HERE / "reviews" / "raw-label-sheet.csv"
MONEY = ["phi_san", "tien_ve_doi_soat", "hoan_tra", "quang_cao", "voucher_khuyen_mai"]
APPS = ["Shopee Seller Center", "TikTok Shop Seller Center", "Lazada Seller Center"]


def xn(x: int, n: int) -> str:
    return f"{x}/{n} ({x / n * 100:.1f}%)".replace(".", ",") if n else f"{x}/0"


def main() -> None:
    rows = list(csv.DictReader(LABELS.open(encoding="utf-8")))
    if RAW.exists():
        raw = list(csv.DictReader(RAW.open(encoding="utf-8-sig")))
        total, unflagged = len(raw), sum(1 for r in raw if r["goi_y_nhan"] == "khac")
        per_app_total = Counter(r["app"] for r in raw)
    else:
        total, unflagged = 900, 784
        per_app_total = Counter({a: 300 for a in APPS})

    for r in rows:
        r["topics"] = set(r["topic"].split(";"))
        r["money"] = r["is_seller_pain"] == "1" and bool(r["topics"] & set(MONEY))

    A = [r for r in rows if r["mau"] == "co_nhan_tu_khoa"]
    B = [r for r in rows if r["mau"] == "ngau_nhien_khong_nhan"]
    a_money = [r for r in A if r["money"]]
    b_money = [r for r in B if r["money"]]

    print(f"Tổng review: {total} · bộ lọc từ khoá gắn nhãn tiền: {len(A)} · không nhãn: {unflagged}\n")
    print("1. Độ đúng của bộ lọc từ khoá")
    print(f"   Mẫu A — có nhãn từ khoá, pain về tiền thật: {xn(len(a_money), len(A))}")
    print(f"   Mẫu B — không nhãn, vẫn là pain về tiền: {xn(len(b_money), len(B))}")
    est = len(a_money) + round(len(b_money) / len(B) * unflagged)
    print(f"   Ước lượng pain về tiền trên {total}: {len(a_money)} + {len(b_money)}/{len(B)} × {unflagged} "
          f"≈ {est} ({est / total * 100:.1f}%) *(ước lượng từ mẫu B, n nhỏ)*\n".replace(".", ",", 1))

    print(f"2. Theo nhãn, trong {len(a_money)} review pain về tiền đã xác nhận (mẫu A, một review có thể nhiều nhãn)")
    for t in MONEY:
        k = sum(1 for r in a_money if t in r["topics"])
        print(f"   {t:20s} {xn(k, len(a_money))}  · trên {total}: {xn(k, total)}")
    prof = sum(1 for r in a_money if r["mentions_profit"] == "1")
    print(f"   nói rõ lỗ / lãi mỏng  {xn(prof, len(a_money))}\n")

    print("3. Theo app (mẫu A đã xác nhận, mẫu số = 300 review mỗi app)")
    for app in APPS:
        m = [r for r in a_money if r["app"] == app]
        fee = [r for r in m if "phi_san" in r["topics"]]
        print(f"   {app:28s} pain về tiền {xn(len(m), per_app_total[app])} · phí sàn {xn(len(fee), per_app_total[app])}")

    low = [r for r in a_money if int(r["score"]) <= 3]
    print(f"\n4. Pain về tiền trong review ≤ 3 sao: {len(low)} (mẫu số ≤ 3 sao lấy ở data thô)")
    checked = [r for r in rows if r["human_check"]]
    agree = sum(1 for r in checked if r["human_check"] == "dong_y")
    print(f"\n5. Người kiểm: {len(checked)} dòng đã kiểm, đồng ý {agree}" +
          (f" ({agree / len(checked) * 100:.0f}%)" if checked else " — CHƯA KIỂM, cần ≥ 30 dòng"))


if __name__ == "__main__":
    main()
