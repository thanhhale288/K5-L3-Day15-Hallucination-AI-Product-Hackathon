"""Điền effective_date cho chunk còn null, CHỈ khi chính text của chunk nêu ngày hiệu lực (clean.chunk_effective_date).

Sửa tại chỗ data/<thư mục sàn>/policies/chunks.jsonl (chỉ trường effective_date; không đổi chunk_id, text, vector),
ghi căn cứ từng ngày vào data/policies/effective_date_evidence.csv, rồi chạy lại merge.py để cập nhật kho gộp.
Nguồn không nêu ngày → giữ null. Không suy từ fetched_at hay updated_at.

    python scripts/policies/fill_effective_date.py [--dry-run]
    python scripts/policies/merge.py
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import chunk_effective_date  # noqa: E402
from common import ROOT, paths  # noqa: E402

PLATFORMS = ["shopee", "tiktok", "lazada"]
EVIDENCE = os.path.join(ROOT, "data", "policies", "effective_date_evidence.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = []
    for plat in PLATFORMS:
        path = paths(plat)["chunks"]
        with open(path, encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f if line.strip()]
        n_null = n_fill = 0
        for c in chunks:
            if c.get("effective_date"):
                continue
            n_null += 1
            day, quote = chunk_effective_date(c["text"])
            if day:
                c["effective_date"] = day
                n_fill += 1
                rows.append({"chunk_id": c["chunk_id"], "platform": plat, "effective_date": day,
                             "url": c.get("url"), "can_cu": quote})
        print("%-7s chunk thiếu ngày %3d · điền có căn cứ %2d · vẫn null %3d" % (plat, n_null, n_fill, n_null - n_fill))
        if not a.dry_run and n_fill:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                for c in chunks:
                    f.write(json.dumps(c, ensure_ascii=False) + "\n")
    if not a.dry_run:
        old = []
        if os.path.exists(EVIDENCE):        # giữ căn cứ của lần chạy trước (chunk đó giờ không còn null)
            with open(EVIDENCE, encoding="utf-8") as f:
                old = [r for r in csv.DictReader(f) if r["chunk_id"] not in {x["chunk_id"] for x in rows}]
        with open(EVIDENCE, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["chunk_id", "platform", "effective_date", "url", "can_cu"])
            w.writeheader()
            w.writerows(sorted(old + rows, key=lambda r: r["chunk_id"]))
        print("căn cứ → %s (%d dòng)" % (os.path.relpath(EVIDENCE, ROOT), len(old) + len(rows)))


if __name__ == "__main__":
    main()
