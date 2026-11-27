"""Truy xuất chính sách sàn cho RAG — NHÓM VIẾT. Chỉ dùng thư viện chuẩn.

- embed_texts(texts, task_type): gọi Gemini batchEmbedContents, trả vector đã chuẩn hoá L2.
  Dùng chung cho scripts/policies/embed.py (tài liệu) và search() (câu hỏi).
- search(query, platform, policy_type, k): lọc cứng metadata (platform, policy_type) trước, rồi xếp hạng
  BM25 từ khoá (+ cosine nếu có vector), gộp bằng RRF. Chạy được cả khi chưa có API key embedding.

Dữ liệu: ưu tiên kho GỘP data/policies/{chunks,index}.jsonl (H1, scripts/policies/merge.py);
chưa có thì đọc kho riêng từng sàn: mỗi sàn một kho data/<thư mục sàn>/policies/{chunks,index}.jsonl (bảng sàn → thư mục ở
codebase/policy_paths.py; vd tiktok → data/tiktok_shop/policies), sinh bởi scripts/policies/.
Biến .env: EMBED_API_KEY (không có thì dùng API_KEY khi MODEL_PROVIDER=gemini), EMBED_MODEL, EMBED_DIM,
POLICY_MIN_SCORE (ngưỡng cosine; mặc định 0.62 *(tự ước tính từ 8 câu thử tay: liên quan ≥0.65, câu rác ≤0.59)*, chỉnh sau khi xem điểm trên bộ câu thử).
"""
import collections
import json
import math
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request

import ai  # noqa: F401  (nạp .env)
from policy_paths import MERGED, available_platforms, paths

# EMBED_PROVIDER=local → chạy BAAI/bge-m3 ngay trên máy (sentence-transformers, 1024 chiều, không cần API key).
# Mặc định giữ Gemini. Kho index và câu hỏi phải cùng một model: đổi provider thì embed lại cả 3 sàn.
LOCAL = (os.environ.get("EMBED_PROVIDER") or "").strip().lower() == "local"
EMBED_MODEL = (os.environ.get("EMBED_MODEL") or ("bge-m3" if LOCAL else "gemini-embedding-001")).strip()
EMBED_DIM = int(os.environ.get("EMBED_DIM") or (1024 if LOCAL else 768))
LOCAL_REPO = "BAAI/bge-m3"
MIN_SCORE = float(os.environ.get("POLICY_MIN_SCORE") or 0.62)
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/%s:batchEmbedContents"
BATCH = 100  # giới hạn số request con mỗi lần gọi batch của Gemini


def _api_key():
    key = (os.environ.get("EMBED_API_KEY") or "").strip()
    if not key and (os.environ.get("MODEL_PROVIDER") or "").strip().lower() == "gemini":
        key = (os.environ.get("API_KEY") or "").strip()
    if not key:
        raise RuntimeError("thiếu EMBED_API_KEY trong .env (hoặc MODEL_PROVIDER=gemini + API_KEY)")
    return key


def _normalize(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _post(body, retries=4):
    req = urllib.request.Request(
        API_URL % EMBED_MODEL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": _api_key()})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < retries:
                time.sleep(2 ** attempt * 5)
                continue
            raise RuntimeError("Gemini embed lỗi %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))


_local_model = None


def _embed_local(texts):
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(LOCAL_REPO)
        _local_model.max_seq_length = 2048  # chunk dài nhất ~1750 token; bge-m3 hỗ trợ tới 8192
    vecs = _local_model.encode(texts, batch_size=8, normalize_embeddings=True, show_progress_bar=len(texts) > 16)
    return [[float(x) for x in v] for v in vecs]


def embed_texts(texts, task_type="RETRIEVAL_DOCUMENT", titles=None):
    """texts: list[str] → list[list[float]] đã chuẩn hoá L2. task_type: RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY."""
    if LOCAL:  # bge-m3 không cần tiền tố task, dùng chung một đường cho tài liệu và câu hỏi
        return _embed_local(texts)
    out = []
    for i in range(0, len(texts), BATCH):
        reqs = []
        for j, t in enumerate(texts[i:i + BATCH]):
            r = {"model": "models/" + EMBED_MODEL, "content": {"parts": [{"text": t}]},
                 "taskType": task_type, "outputDimensionality": EMBED_DIM}
            if titles and task_type == "RETRIEVAL_DOCUMENT" and titles[i + j]:
                r["title"] = titles[i + j]
            reqs.append(r)
        res = _post({"requests": reqs})
        out.extend(_normalize(e["values"]) for e in res["embeddings"])
    return out


_stores = {}  # platform → (chunks, {chunk_id: vector}, bm25); nạp một lần mỗi sàn
RRF_K = 60     # hằng số Reciprocal Rank Fusion khi có cả BM25 lẫn vector
BM25_MIN_COVER = float(os.environ.get("POLICY_MIN_COVER") or 0.6)  # tỉ lệ từ khoá của câu hỏi phải có trong chunk *(tự ước tính)*
_STOP = set("la cua va cho voi cac nhung mot nay do thi ma de khi nao gi sao bao nhieu co khong duoc bi "
            "toi minh em anh chi ban shop don hang ve tren o tai theo nhu vay the".split())


def _plain(s):
    s = unicodedata.normalize("NFD", str(s or "").lower().replace("đ", "d"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def _terms(s):
    """Âm tiết không dấu (bỏ từ dừng) + cặp âm tiết liền nhau (tiếng Việt: "phi co dinh" → "phi_co", "co_dinh")."""
    words = re.findall(r"[a-z0-9]+", _plain(s))
    uni = [w for w in words if w not in _STOP and (len(w) > 1 or w.isdigit())]
    return uni, uni + ["%s_%s" % (a, b) for a, b in zip(words, words[1:])]


class _BM25:
    def __init__(self, docs, k1=1.4, b=0.75):
        self.k1, self.b = k1, b
        self.tf = [collections.Counter(_terms(d)[1]) for d in docs]
        self.len = [sum(t.values()) for t in self.tf]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 1.0
        df = collections.Counter(t for tf in self.tf for t in tf)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.max_idf = math.log(1 + (n + 0.5) / 0.5)

    def scores(self, query):
        uni, qterms = _terms(query)
        w = {t: self.idf.get(t, self.max_idf) for t in set(uni)}   # từ không có trong kho = hiếm nhất
        total = sum(w.values())
        out = []
        for i, tf in enumerate(self.tf):
            # độ phủ có trọng số IDF: từ hiếm (vd "xtra") nặng hơn từ phổ biến (vd "ha", "noi")
            cover = (sum(w[t] for t in w if t in tf) / total) if total else 0.0
            s = 0.0
            for t in qterms:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            out.append((s, cover))
        return out


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _load(platform):
    """Kho gộp data/policies/ (H1) nếu đã có, lọc CỨNG theo platform; chưa có thì đọc kho riêng của sàn."""
    if platform not in _stores:
        merged = paths(MERGED)
        if os.path.exists(merged["chunks"]):
            chunks = [c for c in _read_jsonl(merged["chunks"]) if c.get("platform") == platform]
            rows = _read_jsonl(merged["index"])
        else:
            chunks = [c for c in _read_jsonl(paths(platform)["chunks"]) if c.get("platform", platform) == platform]
            rows = _read_jsonl(paths(platform)["index"])
        ids = {c["chunk_id"] for c in chunks}
        vectors = {r["chunk_id"]: r["vector"] for r in rows
                   if r["chunk_id"] in ids and r.get("embed_model") == EMBED_MODEL and r.get("dim") == EMBED_DIM}
        bm25 = _BM25([(c.get("context_header") or "") + "\n" + c["text"] for c in chunks])
        _stores[platform] = (chunks, vectors, bm25)
    return _stores[platform]


def search(query, platform="tiktok", policy_type="", k=4, min_score=None):
    """Trả tối đa k chunk liên quan nhất trong kho của platform (và policy_type nếu có). Không có → [].

    Hai đường, gộp bằng RRF:
      - BM25 từ khoá (luôn chạy, không cần API): chunk phải chứa ≥ BM25_MIN_COVER từ khoá của câu hỏi.
      - Vector cosine ≥ min_score (chỉ khi chunk đã có vector đúng EMBED_MODEL/EMBED_DIM và có API key).
    platform="" → tìm trên mọi sàn (available_platforms()); KHÔNG bao giờ trộn khi đã chỉ định sàn.
    "score": cosine nếu có, không thì độ phủ từ khoá (0–1); "via": "bm25" | "vector" | "bm25+vector"."""
    if not str(query or "").strip():
        return []
    plats = [platform] if platform else available_platforms()
    pool, vectors, lexical = [], {}, {}
    for plat in plats:
        chunks, vecs, bm25 = _load(plat)
        vectors.update(vecs)
        for c, (s, cover) in zip(chunks, bm25.scores(query)):
            if policy_type and c.get("policy_type") != policy_type:
                continue
            pool.append(c)
            if s > 0 and cover >= BM25_MIN_COVER:
                lexical[c["chunk_id"]] = (s, cover)
    if not pool:
        return []

    semantic = {}
    if any(c["chunk_id"] in vectors for c in pool):
        try:
            q = embed_texts([query], task_type="RETRIEVAL_QUERY")[0]
            floor = MIN_SCORE if min_score is None else min_score
            for c in pool:
                v = vectors.get(c["chunk_id"])
                if v is not None:
                    s = sum(a * b for a, b in zip(q, v))
                    if s >= floor:
                        semantic[c["chunk_id"]] = s
        except Exception:   # thiếu key / mất mạng → chỉ dùng BM25, không làm hỏng lượt
            semantic = {}

    rank_l = {cid: i for i, cid in enumerate(sorted(lexical, key=lambda x: -lexical[x][0]))}
    rank_v = {cid: i for i, cid in enumerate(sorted(semantic, key=lambda x: -semantic[x]))}
    fused = []
    for c in pool:
        cid = c["chunk_id"]
        if cid not in rank_l and cid not in rank_v:
            continue
        r = sum(1.0 / (RRF_K + rk[cid] + 1) for rk in (rank_l, rank_v) if cid in rk)
        via = "+".join(n for n, rk in (("bm25", rank_l), ("vector", rank_v)) if cid in rk)
        score = semantic[cid] if cid in semantic else lexical[cid][1]
        fused.append((r, score, via, c))
    fused.sort(key=lambda x: -x[0])
    return [{"chunk_id": c["chunk_id"], "platform": c.get("platform"),
             "text": (c.get("context_header") or "") + "\n" + c["text"], "url": c.get("url"),
             "effective_date": c.get("effective_date"), "updated_at": c.get("updated_at"),
             "fetched_at": c.get("fetched_at"), "score": round(score, 4), "via": via}
            for _, score, via, c in fused[:k]]
