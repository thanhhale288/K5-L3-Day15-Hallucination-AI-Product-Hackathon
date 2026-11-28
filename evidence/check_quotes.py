"""Kiểm trích dẫn trong evidence/summary.md theo luật R1 / luật dữ liệu. Chỉ thư viện chuẩn.

    python evidence/check_quotes.py

Với mỗi trích dẫn có dạng  N. "…" — … · đăng dd/mm/yyyy · k★ · … (`review_key`):
  1. review_key có trong evidence/reviews/labels-ai.csv; app, ngày đăng, số sao khớp; is_seller_pain = 1
  2. có link Google Play đúng app
  3. tối đa 2 câu
  4. NGUYÊN VĂN: là chuỗi con của nội dung review trong evidence/reviews/raw-label-sheet.csv (file thô, không commit).
     Thiếu file thô thì in "chưa kiểm nguyên văn": người giữ file thô (Hà) chạy lại trên máy mình.
Thoát mã 1 nếu có lỗi; cần ≥ 5 trích dẫn đạt.
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUMMARY = HERE / "summary.md"
LABELS = HERE / "reviews" / "labels-ai.csv"
RAW = HERE / "reviews" / "raw-label-sheet.csv"
LINK = {"Shopee Seller Center": "com.shopee.shopeeseller", "TikTok Shop Seller Center": "com.tiktokshop.seller",
        "Lazada Seller Center": "com.sc.lazada"}
QUOTE = re.compile(r'^\s*\d+\.\s+"(?P<q>.+)"\s*$')
META = re.compile(r"^\s*—\s*\[(?P<app>[^\]]+)\]\((?P<url>[^)]+)\).*?đăng (?P<d>\d{2})/(?P<m>\d{2})/(?P<y>\d{4})"
                  r"\s*·\s*(?P<star>\d)★.*\(`(?P<key>[0-9a-f]{12})`\)")


def norm(s):
    return " ".join(str(s).split())


def sentences(q):
    """Số câu: tách ở . ! ? (một hoặc nhiều) theo sau là khoảng trắng hoặc hết chuỗi; bỏ đoạn rỗng."""
    return len([p for p in re.split(r"[.!?]+(?:\s+|$)", q.strip()) if p.strip()])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    lines = SUMMARY.read_text(encoding="utf-8").splitlines()
    labels = {r["review_key"]: r for r in csv.DictReader(LABELS.open(encoding="utf-8"))}
    raw = {}
    if RAW.exists():
        raw = {r["review_key"]: r for r in csv.DictReader(RAW.open(encoding="utf-8-sig"))}
    quotes = []
    for i, ln in enumerate(lines):
        m = QUOTE.match(ln)
        if m and i + 1 < len(lines) and META.match(lines[i + 1]):
            quotes.append((m.group("q"), META.match(lines[i + 1]).groupdict()))
    n_err, n_ok, n_unverified = 0, 0, 0
    for idx, (q, meta) in enumerate(quotes, 1):
        err = []
        lab = labels.get(meta["key"])
        if lab is None:
            err.append("review_key không có trong labels-ai.csv")
        else:
            date = "%s-%s-%s" % (meta["y"], meta["m"], meta["d"])
            if lab["app"] != meta["app"]:
                err.append("app %r ≠ %r trong labels-ai.csv" % (meta["app"], lab["app"]))
            if lab["date"] != date:
                err.append("ngày đăng %s ≠ %s" % (date, lab["date"]))
            if str(lab["score"]) != meta["star"]:
                err.append("số sao %s ≠ %s" % (meta["star"], lab["score"]))
            if lab.get("is_seller_pain") != "1":
                err.append("is_seller_pain ≠ 1")
        if LINK.get(meta["app"], "?") not in meta["url"]:
            err.append("link không phải trang Google Play của %s" % meta["app"])
        if sentences(q) > 2:
            err.append("dài %d câu (tối đa 2)" % sentences(q))
        verbatim = "chưa kiểm nguyên văn (thiếu evidence/reviews/%s)" % RAW.name
        if raw:
            verbatim = "nguyên văn ✗"
            r = raw.get(meta["key"])
            if r is None:
                err.append("review_key không có trong file thô")
            elif norm(q) not in norm(r["content"]):
                err.append("KHÔNG nguyên văn: không phải chuỗi con của nội dung review")
            else:
                verbatim = "nguyên văn ✓"
        else:
            n_unverified += 1
        status = "LỖI" if err else "ok "
        print("%s %d. %s · %s · %s%s" % (status, idx, meta["key"], meta["app"], verbatim,
                                         (" · " + "; ".join(err)) if err else ""))
        n_err += bool(err)
        n_ok += not err
    print("\n%d trích dẫn · đạt %d · lỗi %d · chưa kiểm nguyên văn %d" % (len(quotes), n_ok, n_err, n_unverified))
    if n_ok < 5:
        print("CHƯA ĐỦ: cần ≥ 5 trích dẫn đạt")
    return 1 if n_err or n_ok < 5 else 0


if __name__ == "__main__":
    sys.exit(main())
