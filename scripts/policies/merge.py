"""TH-1: gộp kho chính sách 3 sàn → data/policies/{chunks.jsonl, index.jsonl, manifest.csv} (hợp đồng H1).

Nguồn (mỗi sàn một schema khác nhau, script chuẩn hoá về schema B4 trong crawl-spec.md):
  - TikTok Shop: data/tiktok_shop/policies/{chunks,index,manifest}  — đã đúng B4, có vector Gemini 768.
  - Shopee:      data/shopee_policy/seller/{chunks,documents}.jsonl — schema rag/pipeline.py
                 (chunk_id, content, title, source_url, section, category, n_tokens); chưa có vector trong repo.
  - Lazada:      data/lazada/policies/chunk_lazada.json (mảng JSON, đã đúng B4) + manifest.csv; chưa có vector.

Chuẩn hoá:
  - chunk_id dạng `doc_id#nnn` (B4). Shopee "shopee-vn-77243-c001" → "shopee-77243#001"; id gốc giữ ở `source_chunk_id`.
  - Đủ khoá B4: chunk_id, doc_id, platform, policy_type, section_path, text, context_header, token_count,
    has_table, has_numbers, effective_date, updated_at, url, fetched_at, content_hash, chunker_version.
  - policy_type Shopee suy từ tiêu đề bài (fee | voucher | ads | return_refund | settlement | other).
  - effective_date Shopee: câu "hiệu lực từ dd/mm/yyyy" đầu tiên trong bài, không có thì null.
  - Bỏ trùng: cùng platform + cùng nội dung (bỏ khoảng trắng, chữ thường) → giữ chunk đầu.
Vector: chép từ index của từng sàn (giữ embed_model, dim). Sàn chưa có vector thì search_policy dùng BM25;
embed thêm bằng: python scripts/policies/embed.py --platform all

    python scripts/policies/merge.py
"""
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, paths  # noqa: E402

DATA = os.path.join(ROOT, "data")
SHOPEE_DIR = os.path.join(DATA, "shopee_policy", "seller")
LAZADA_JSON = os.path.join(paths("lazada")["dir"], "chunk_lazada.json")
OUT = paths("all")

KEYS = ["chunk_id", "doc_id", "platform", "policy_type", "section_path", "text", "context_header", "token_count",
        "has_table", "has_numbers", "effective_date", "updated_at", "url", "fetched_at", "content_hash",
        "chunker_version", "source_chunk_id"]
MANIFEST_KEYS = ["doc_id", "platform", "title", "url", "policy_type", "effective_date", "fetched_at", "n_chunks"]


def _plain(s):
    s = unicodedata.normalize("NFD", str(s or "").lower().replace("đ", "d"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Shopee ──────────────────────────────────────────────────────────────────
SHOPEE_TYPES = [  # (từ khoá không dấu trong tiêu đề / danh mục, policy_type) — khớp đầu tiên thắng
    ("tra hang", "return_refund"), ("hoan tien", "return_refund"), ("tranh chap", "return_refund"),
    ("ma giam gia", "voucher"), ("ma uu dai", "voucher"), ("khach hang than thiet", "voucher"),
    ("tiep thi lien ket", "ads"), ("hien thi", "ads"), ("san pham hot", "ads"), ("shopee live", "ads"),
    ("trung bay", "ads"),
    ("thue", "settlement"), ("hoa don", "settlement"), ("cho vay", "settlement"), ("quick funds", "settlement"),
    ("spaylater", "settlement"),
    ("goi dich vu", "fee"), ("phi van chuyen", "fee"), ("goi san giao nhanh", "fee"), ("phi", "fee"),
]
_DATE = re.compile(r"hieu luc (?:ke )?(?:tu )?(?:ngay )?(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})")


def _shopee_type(title, category):
    t = _plain(title + " " + category)
    for kw, ptype in SHOPEE_TYPES:
        if kw in t:
            return ptype
    return "other"


def _shopee_effective(content):
    m = _DATE.search(_plain(content))
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    return "%04d-%02d-%02d" % (y, mo, d) if 1 <= mo <= 12 and 1 <= d <= 31 else None


def shopee_chunks():
    docs = {d["doc_id"]: d for d in _read_jsonl(os.path.join(SHOPEE_DIR, "documents.jsonl"))}
    out = []
    for c in _read_jsonl(os.path.join(SHOPEE_DIR, "chunks.jsonl")):
        m = re.match(r"(shopee-vn-(\d+))-c(\d+)$", c["chunk_id"])
        src_doc, art, no = (m.group(1), m.group(2), int(m.group(3))) if m else (c["chunk_id"], c["chunk_id"], 0)
        doc = docs.get(src_doc, {})
        text = c["content"]
        section = [x for x in (c.get("title"), c.get("section")) if x]
        out.append({
            "chunk_id": "shopee-%s#%03d" % (art, no), "doc_id": "shopee-%s" % art, "platform": "shopee",
            "policy_type": _shopee_type(c.get("title", ""), c.get("category", "")),
            "section_path": section, "text": text,
            "context_header": "[Shopee · %s]" % " > ".join(section),
            "token_count": c.get("n_tokens"), "has_table": "|" in text,
            "has_numbers": bool(re.search(r"\d+([.,]\d+)?\s*(%|đ|vnd|vnđ|đồng)", text.lower())),
            "effective_date": _shopee_effective(doc.get("content", "")), "updated_at": None,
            "url": c.get("source_url") or doc.get("source_url"),
            "fetched_at": (doc.get("fetched_at") or "")[:10] or None,
            "content_hash": _sha(text), "chunker_version": "shopee-rag-pipeline-600",
            "source_chunk_id": c["chunk_id"], "_title": c.get("title", ""),
        })
    return out


# ── TikTok Shop, Lazada (đã đúng B4) ────────────────────────────────────────
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


def tiktok_chunks():
    titles = _manifest_titles("tiktok")
    return [_b4(c, titles.get(c["doc_id"], "")) for c in _read_jsonl(paths("tiktok")["chunks"])]


def lazada_chunks():
    rows = _read_jsonl(paths("lazada")["chunks"])
    if not rows and os.path.exists(LAZADA_JSON):
        with open(LAZADA_JSON, encoding="utf-8") as f:
            rows = json.load(f)
    titles = _manifest_titles("lazada")
    return [_b4(c, titles.get(c["doc_id"], "")) for c in rows]


# ── gộp ─────────────────────────────────────────────────────────────────────
def merge():
    chunks, seen, dropped = [], set(), {}
    for plat, rows in (("shopee", shopee_chunks()), ("tiktok", tiktok_chunks()), ("lazada", lazada_chunks())):
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
