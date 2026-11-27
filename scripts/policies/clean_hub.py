"""B2' · raw-<platform>/<doc_id>.json (từ crawl_hub.py) → <kho sàn>/clean/<doc_id>.md + manifest.csv.

Dùng lại hàm của clean.py (bảng → dòng "Cột: giá trị | …", chuẩn hoá NFC, không sửa số/%/đ/ngày) nên
đầu ra giống hệt kho TikTok. Manifest sắp theo doc_id, ghi lại đúng các tài liệu có trong urls_<platform>.txt.

    python scripts/policies/clean_hub.py --platform shopee
"""
import argparse
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import MANIFEST_COLS, effective_date, to_markdown  # noqa: E402
from common import paths, read_urls  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True)
    a = ap.parse_args()
    P = paths(a.platform)
    os.makedirs(P["clean"], exist_ok=True)

    rows = {}
    for doc_id, ptype, url in read_urls(a.platform):
        path = os.path.join(P["raw"], doc_id + ".json")
        if not os.path.exists(path):
            print("chưa crawl:", doc_id)
            continue
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        _t, md = to_markdown("<article>%s</article>" % raw["html"])
        title = raw["title"].strip()
        if len(md) < 200:
            print("CẢNH BÁO nội dung quá ngắn (%d ký tự):" % len(md), doc_id)
        body = md if md.startswith("# ") else "# %s\n\n%s" % (title, md)
        with open(os.path.join(P["clean"], doc_id + ".md"), "w", encoding="utf-8") as f:
            f.write(body + "\n")
        rows[doc_id] = {
            "doc_id": doc_id, "platform": a.platform, "title": title, "url": url, "policy_type": ptype,
            # ngày trong tiêu đề ("từ ngày 04/06/2026") được ưu tiên hơn ngày trong thân bài
            "effective_date": effective_date(title) or effective_date(md) or "",
            "updated_at": raw.get("updated_at") or "",
            "fetched_at": raw.get("fetched_at") or "", "content_hash": hashlib.sha256(md.encode("utf-8")).hexdigest(),
        }
        print("ok", doc_id, len(md), "ký tự ·", title[:60])

    with open(P["manifest"], "w", newline="", encoding="utf-8") as f:  # UTF-8 không BOM
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: r["doc_id"]):
            w.writerow(r)
    print("manifest:", len(rows), "tài liệu →", P["manifest"])


if __name__ == "__main__":
    main()
