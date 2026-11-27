"""TH-1: gộp kho chính sách 3 sàn → data/policies/{chunks.jsonl, index.jsonl, manifest.csv} (hợp đồng H1).

Nguồn: kho riêng của từng sàn data/<thư mục sàn>/policies/{chunks,index,manifest} (codebase/policy_paths.py).
Cả 3 kho đã đúng schema chung (docs/policy-schema.md) và qua scripts/policies/validate.py, nên chỉ cần chép.

Việc script làm:
  - Bỏ trùng: cùng platform + cùng nội dung (bỏ khoảng trắng, chữ thường) → giữ chunk đầu.
  - Chép vector từ index của từng sàn (giữ embed_model, dim). Cả 3 sàn phải cùng một model (kiểm ở cuối).
Sàn chưa có vector thì search_policy dùng BM25.

    python scripts/policies/merge.py
"""
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, paths  # noqa: E402

DATA = os.path.join(ROOT, "data")
OUT = paths("all")

KEYS = ["chunk_id", "doc_id", "platform", "policy_type", "section_path", "text", "context_header", "token_count",
        "has_table", "has_numbers", "effective_date", "updated_at", "url", "fetched_at", "content_hash",
        "chunker_version", "source_chunk_id"]
MANIFEST_KEYS = ["doc_id", "platform", "title", "url", "policy_type", "effective_date", "fetched_at", "n_chunks"]


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── đọc kho riêng của từng sàn ──────────────────────────────────────────────
def _b4(c, title):
    r = {k: c.get(k) for k in KEYS}
    r["source_chunk_id"] = c["chunk_id"]
    r["content_hash"] = r["content_hash"] or _sha(c["text"])
    r["_title"] = title
    return r


def _manifest_titles(platform):
    p = paths(platform)["manifest"]
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8-sig") as f:
        return {r["doc_id"]: r.get("title", "") for r in csv.DictReader(f)}


def platform_chunks(platform):
    titles = _manifest_titles(platform)
    return [_b4(c, titles.get(c["doc_id"], "")) for c in _read_jsonl(paths(platform)["chunks"])]


# ── gộp ─────────────────────────────────────────────────────────────────────
def merge():
    chunks, seen, dropped = [], set(), {}
    for plat, rows in ((p, platform_chunks(p)) for p in ("shopee", "tiktok", "lazada")):
        for c in rows:
            assert c["platform"] == plat, "chunk %s ghi sai platform" % c["chunk_id"]
            k = (plat, _sha(" ".join(c["text"].lower().split())))
            if k in seen or not c["text"].strip():
                dropped[plat] = dropped.get(plat, 0) + 1
                continue
            seen.add(k)
            chunks.append(c)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)), "chunk_id trùng sau khi gộp"

    # vector cũ của từng sàn (index.jsonl theo chunk_id gốc)
    vec_rows = []
    by_src = {}
    for plat in ("shopee", "tiktok", "lazada"):
        for r in _read_jsonl(paths(plat)["index"]):
            by_src[(plat, r["chunk_id"])] = r
    for c in chunks:
        r = by_src.get((c["platform"], c["source_chunk_id"]))
        if r:
            vec_rows.append(dict(r, chunk_id=c["chunk_id"]))

    models = {(r.get("embed_model"), r.get("dim")) for r in vec_rows}
    assert len(models) <= 1, "3 sàn đang dùng nhiều model embedding khác nhau: %s" % sorted(models, key=str)

    os.makedirs(OUT["dir"], exist_ok=True)
    with open(OUT["chunks"], "w", encoding="utf-8", newline="\n") as f:
        for c in chunks:
            f.write(json.dumps({k: c.get(k) for k in KEYS}, ensure_ascii=False) + "\n")
    with open(OUT["index"], "w", encoding="utf-8", newline="\n") as f:
        for r in vec_rows:
            f.write(json.dumps(r) + "\n")

    docs = {}
    for c in chunks:
        d = docs.setdefault(c["doc_id"], {"doc_id": c["doc_id"], "platform": c["platform"], "title": c["_title"],
                                          "url": c["url"], "policy_type": c["policy_type"],
                                          "effective_date": c["effective_date"] or "",
                                          "fetched_at": c["fetched_at"] or "", "n_chunks": 0})
        d["n_chunks"] += 1
    with open(OUT["manifest"], "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_KEYS)
        w.writeheader()
        w.writerows(docs.values())

    print("Đã gộp → %s" % os.path.relpath(OUT["dir"], ROOT))
    for plat in ("shopee", "tiktok", "lazada"):
        n = sum(c["platform"] == plat for c in chunks)
        nv = sum(1 for c in chunks if c["platform"] == plat and (plat, c["source_chunk_id"]) in by_src)
        nd = sum(1 for d in docs.values() if d["platform"] == plat)
        print("  %-7s %4d chunk · %3d bài · bỏ trùng %3d · có vector %4d" % (plat, n, nd, dropped.get(plat, 0), nv))
    return chunks


if __name__ == "__main__":
    merge()
