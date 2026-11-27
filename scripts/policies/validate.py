"""Kiểm tra kho chính sách của một sàn có đúng schema chung không. Chỉ dùng thư viện chuẩn.

    python scripts/policies/validate.py --platform shopee [--dir data/shopee/policies]

Thoát mã 1 nếu có lỗi. Cảnh báo (WARN) không làm fail nhưng cần đọc.
"""
import argparse
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIRS = {"tiktok": "tiktok_shop", "shopee": "shopee", "lazada": "lazada"}
TYPES = {"fee", "voucher", "ads", "return_refund", "settlement"}
MANIFEST_COLS = ["doc_id", "platform", "title", "url", "policy_type", "effective_date", "updated_at", "fetched_at", "content_hash"]
CHUNK_KEYS = {"chunk_id": str, "doc_id": str, "platform": str, "policy_type": str, "section_path": list, "text": str,
              "context_header": str, "token_count": int, "has_table": bool, "has_numbers": bool, "url": str,
              "fetched_at": str, "content_hash": str, "chunker_version": str}
INDEX_KEYS = ["chunk_id", "text_hash", "content_hash", "chunker_version", "embed_model", "dim", "vector"]
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EMBED_OK = {("gemini-embedding-001", 768), ("bge-m3", 1024)}  # model đã được nhóm chấp nhận; cả 3 sàn phải dùng chung một model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True, choices=sorted(DIRS))
    ap.add_argument("--dir", help="mặc định data/<thư mục sàn>/policies")
    a = ap.parse_args()
    d = a.dir or os.path.join(ROOT, "data", DIRS[a.platform], "policies")
    err, warn = [], []

    def need(path):
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            err.append("thiếu hoặc rỗng: %s" % path)
            return False
        return True

    mf, cf, xf = (os.path.join(d, n) for n in ("manifest.csv", "chunks.jsonl", "index.jsonl"))
    ok = [need(mf), need(cf), need(xf)]
    if not all(ok):
        return report(a, err, warn, {})

    with open(mf, "rb") as f:
        if f.read(3) == b"\xef\xbb\xbf":
            err.append("manifest.csv có BOM, lưu lại UTF-8 không BOM")
    with open(mf, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != MANIFEST_COLS:
            err.append("manifest cột sai: %s, cần %s" % (rd.fieldnames, MANIFEST_COLS))
        docs = {r["doc_id"]: r for r in rd}
    for i, r in docs.items():
        if r.get("platform") != a.platform:
            err.append("manifest %s: platform=%r" % (i, r.get("platform")))
        if r.get("policy_type") not in TYPES:
            err.append("manifest %s: policy_type=%r" % (i, r.get("policy_type")))
        if not (r.get("url") or "").startswith("http"):
            err.append("manifest %s: url không hợp lệ" % i)
        if not r.get("content_hash"):
            err.append("manifest %s: thiếu content_hash" % i)
        for k in ("effective_date", "updated_at", "fetched_at"):
            v = r.get(k) or ""
            if v and not DATE.match(v):
                err.append("manifest %s: %s=%r không phải YYYY-MM-DD" % (i, k, v))
        if not (r.get("effective_date") or r.get("updated_at")):
            warn.append("manifest %s: không có effective_date lẫn updated_at" % i)

    chunks = load_jsonl(cf, err)
    ids = set()
    for n, c in enumerate(chunks, 1):
        w = "chunks dòng %d" % n
        for k, t in CHUNK_KEYS.items():
            if k not in c:
                err.append("%s: thiếu %s" % (w, k))
            elif not isinstance(c[k], t) or (t is int and isinstance(c[k], bool)):
                err.append("%s: %s phải là %s, đang là %s" % (w, k, t.__name__, type(c[k]).__name__))
        for k in ("effective_date", "updated_at"):
            if k not in c:
                err.append("%s: thiếu khoá %s (để null nếu không có)" % (w, k))
            elif c[k] is not None and not DATE.match(str(c[k])):
                err.append("%s: %s=%r phải là YYYY-MM-DD hoặc null" % (w, k, c[k]))
        if c.get("platform") != a.platform:
            err.append("%s: platform=%r" % (w, c.get("platform")))
        if c.get("policy_type") not in TYPES:
            err.append("%s: policy_type=%r" % (w, c.get("policy_type")))
        if c.get("doc_id") not in docs:
            err.append("%s: doc_id %r không có trong manifest" % (w, c.get("doc_id")))
        elif docs[c["doc_id"]].get("policy_type") != c.get("policy_type"):
            err.append("%s: policy_type khác manifest" % w)
        if not re.fullmatch(r"%s#\d{3,}" % re.escape(str(c.get("doc_id"))), str(c.get("chunk_id"))):
            err.append("%s: chunk_id %r phải là <doc_id>#NNN" % (w, c.get("chunk_id")))
        if c.get("chunk_id") in ids:
            err.append("%s: chunk_id trùng" % w)
        ids.add(c.get("chunk_id"))
        if not str(c.get("context_header", "")).startswith("["):
            err.append("%s: context_header phải dạng [Sàn · Tiêu đề · …]" % w)
        if isinstance(c.get("text"), str) and not c["text"].strip():
            err.append("%s: text rỗng" % w)
        if isinstance(c.get("token_count"), int) and c["token_count"] > 900:
            warn.append("%s: %d token, chunk quá dài" % (w, c["token_count"]))

    for i in docs:
        if not any(c.get("doc_id") == i for c in chunks):
            err.append("tài liệu %s có trong manifest nhưng 0 chunk" % i)

    index = load_jsonl(xf, err)
    iid, models = set(), set()
    for n, r in enumerate(index, 1):
        w = "index dòng %d" % n
        for k in INDEX_KEYS:
            if k not in r:
                err.append("%s: thiếu %s" % (w, k))
        models.add((r.get("embed_model"), r.get("dim")))
        if (r.get("embed_model"), r.get("dim")) not in EMBED_OK:
            err.append("%s: embed_model/dim = %r/%r, chỉ nhận %s" % (w, r.get("embed_model"), r.get("dim"), sorted(EMBED_OK)))
        v = r.get("vector")
        if not isinstance(v, list) or len(v) != r.get("dim"):
            err.append("%s: vector phải có %s số" % (w, r.get("dim")))
        elif abs(sum(x * x for x in v) - 1) > 0.01:
            err.append("%s: vector chưa chuẩn hoá L2" % w)
        iid.add(r.get("chunk_id"))
    if len(models) > 1:
        err.append("index trộn nhiều model: %s" % sorted(models, key=str))
    if ids - iid:
        err.append("%d chunk chưa có vector (chạy embed.py)" % len(ids - iid))
    if iid - ids:
        err.append("%d vector mồ côi, không có chunk" % len(iid - ids))

    by_type = {}
    for c in chunks:
        by_type.setdefault(c.get("policy_type"), set()).add(c.get("doc_id"))
    for t in sorted(TYPES):
        if not by_type.get(t):
            err.append("thiếu hẳn policy_type=%s (cần ≥1 tài liệu)" % t)
    stats = {t: {"docs": len(by_type.get(t, ())), "chunks": sum(1 for c in chunks if c.get("policy_type") == t)} for t in sorted(TYPES)}
    return report(a, err, warn, stats, len(docs), len(chunks), len(index))


def load_jsonl(path, err):
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as e:
                err.append("%s dòng %d không phải JSON: %s" % (os.path.basename(path), n, e))
    return rows


def report(a, err, warn, stats, nd=0, nc=0, ni=0):
    print("== %s: %d tài liệu · %d chunk · %d vector" % (a.platform, nd, nc, ni))
    for t, s in stats.items():
        print("   %-14s %2d tài liệu · %3d chunk" % (t, s["docs"], s["chunks"]))
    for w in warn[:20]:
        print("WARN", w)
    for e in err[:40]:
        print("LỖI ", e)
    if len(err) > 40:
        print("… và %d lỗi nữa" % (len(err) - 40))
    print("KẾT QUẢ:", "ĐẠT" if not err else "CHƯA ĐẠT (%d lỗi)" % len(err))
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
