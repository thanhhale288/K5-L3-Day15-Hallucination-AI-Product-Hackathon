#!/usr/bin/env python3
"""Cào review Google Play của app NGƯỜI BÁN (bằng chứng pain — đào data, rubric R1).

Cách chọn mẫu (ghi TRƯỚC khi đếm, xem evidence/data-mining.md §1):
  N review MỚI NHẤT mỗi app (mặc định 300), ngôn ngữ vi, quốc gia vn, tính tại ngày chạy.
  Không lọc theo số sao → mẫu số = tất cả review lấy về của app đó.

Quyền riêng tư (luật đề: không chép tên người viết):
  - KHÔNG lưu userName, userImage. reviewId được băm (sha1, 12 ký tự) chỉ để khử trùng.
  - SĐT/email lọt trong nội dung bị che thành [đã che].
  - File nội dung đầy đủ đặt tên raw-*.csv → .gitignore đã chặn (evidence/**/raw-*).
    Chỉ commit manifest.csv + số đã đếm + ≤2 câu trích mỗi review (kèm link, ngày xem).

Cột `goi_y_nhan` là gợi ý theo từ khoá cho nhanh, KHÔNG phải nhãn. Nhóm gán tay vào
cột `nhan` (raw-label-sheet.csv), rồi đếm x/N trên cột `nhan`.

Cài: python -m pip install google-play-scraper   (đã ghi trong requirements.txt)
Chạy (từ gốc repo):
  python evidence/crawl_reviews.py               # 300 review mới nhất × 3 app
  python evidence/crawl_reviews.py --n 1000
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path

try:
    from google_play_scraper import Sort, reviews
except ImportError:
    raise SystemExit("Thiếu thư viện: python -m pip install google-play-scraper")

APPS = {  # appId đã kiểm bằng google_play_scraper.app() ngày 27/11/2026
    "com.shopee.shopeeseller": "Shopee Seller Center",
    "com.tiktokshop.seller": "TikTok Shop Seller Center",
    "com.sc.lazada": "Lazada Seller Center",
}

# Nhãn theo plan. Từ khoá chỉ để GỢI Ý (bỏ dấu không xử lý → viết cả hai dạng).
LABEL_KEYWORDS = {
    "phi_san": ["phí", "chiết khấu", "hoa hồng", "phí cố định", "phí thanh toán",
                "phí dịch vụ", "thu phí", "tăng phí", "phí sàn", "phi san"],
    "doi_soat_kho_hieu": ["đối soát", "doi soat", "tiền về", "tien ve", "rút tiền", "rut tien",
                          "số dư", "so du", "thanh toán chậm", "chưa nhận được tiền", "doanh thu",
                          "báo cáo", "lợi nhuận", "trừ tiền", "bị trừ", "ví", "giữ tiền"],
    "quang_cao": ["quảng cáo", "quang cao", "ads", "đấu thầu", "roas", "chạy qc", " qc "],
    "voucher": ["voucher", "mã giảm", "khuyến mãi", "khuyen mai", "flash sale", "freeship",
                "giảm giá", "trợ giá"],
    "hoan_hang": ["hoàn hàng", "hoan hang", "trả hàng", "tra hang", "hoàn tiền", "hoan tien",
                  "bom hàng", "bom hang", "khiếu nại", "đổi trả", "giao thất bại"],
}
PII = [re.compile(r"(\+?84|0)(\d[\s.\-]?){8,10}\d"), re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")]


def mask(text: str) -> str:
    for p in PII:
        text = p.sub("[đã che]", text)
    return text.replace("\r", " ").replace("\n", " ").strip()


_PATTERNS = {lab: re.compile(r"(?<!\w)(" + "|".join(re.escape(k.strip()) for k in kws) + r")(?!\w)")
             for lab, kws in LABEL_KEYWORDS.items()}


def suggest(text: str) -> str:
    t = text.lower().replace("miễn phí", "")      # "miễn phí" không phải than phí
    hits = [lab for lab, pat in _PATTERNS.items() if pat.search(t)]
    return ";".join(hits) or "khac"


def fetch(app_id: str, n: int) -> list[dict]:
    out, token = [], None
    while len(out) < n:
        batch, token = reviews(app_id, lang="vi", country="vn", sort=Sort.NEWEST,
                               count=min(200, n - len(out)), continuation_token=token)
        out += batch
        if not batch or token is None or token.token is None:
            break
        time.sleep(1.0)                      # lịch sự với server
    return out[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="số review mới nhất mỗi app")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "reviews"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    rows, manifest = [], []
    for app_id, name in APPS.items():
        got = fetch(app_id, a.n)
        dates = [r["at"].date().isoformat() for r in got]
        manifest.append({"app_id": app_id, "app_name": name,
                         "link": f"https://play.google.com/store/apps/details?id={app_id}&hl=vi&gl=VN",
                         "crawled_on": today, "requested": a.n, "got": len(got),
                         "oldest_review": min(dates) if dates else "", "newest_review": max(dates) if dates else ""})
        for r in got:
            content = mask(r.get("content") or "")
            rows.append({
                "app": name,
                "review_key": hashlib.sha1(r["reviewId"].encode()).hexdigest()[:12],
                "date": r["at"].date().isoformat(),
                "score": r["score"],
                "thumbs_up": r.get("thumbsUpCount", 0),
                "app_version": r.get("reviewCreatedVersion") or "",
                "has_dev_reply": int(bool(r.get("replyContent"))),
                "content": content,
                "goi_y_nhan": suggest(content),
                "nhan": "",                       # NHÓM GÁN TAY
                "ghi_chu": "",
            })
        print(f"{name:28s} {len(got):4d} review  ({manifest[-1]['oldest_review']} → {manifest[-1]['newest_review']})")

    fields = list(rows[0]) if rows else []
    with (out / "raw-label-sheet.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0])); w.writeheader(); w.writerows(manifest)

    print(f"\nĐã ghi {out}/raw-label-sheet.csv (không commit) và manifest.csv (commit được)")
    print("\nGỢI Ý theo từ khoá (chưa phải số bằng chứng — phải gán tay cột `nhan` rồi mới đếm):")
    for name in APPS.values():
        sub = [r for r in rows if r["app"] == name]
        if not sub:
            continue
        c = Counter(l for r in sub for l in r["goi_y_nhan"].split(";"))
        low = sum(r["score"] <= 2 for r in sub)
        print(f"  {name} (N={len(sub)}, ≤2 sao {low}): " +
              " · ".join(f"{k} {v}" for k, v in c.most_common()))


if __name__ == "__main__":
    main()
