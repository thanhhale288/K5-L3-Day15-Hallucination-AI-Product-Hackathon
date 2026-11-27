"""Truy xuất chính sách sàn cho RAG — NHÓM VIẾT. Chỉ dùng thư viện chuẩn.

- embed_texts(texts, task_type): gọi Gemini batchEmbedContents, trả vector đã chuẩn hoá L2.
  Dùng chung cho scripts/policies/embed.py (tài liệu) và search() (câu hỏi).
- search(query, platform, policy_type, k): lọc metadata trước, rồi xếp theo cosine.

Dữ liệu: mỗi sàn một kho riêng data/<thư mục sàn>/policies/{chunks,index}.jsonl (bảng sàn → thư mục ở
codebase/policy_paths.py; vd tiktok → data/tiktok_shop/policies), sinh bởi scripts/policies/.
Biến .env: EMBED_API_KEY (không có thì dùng API_KEY khi MODEL_PROVIDER=gemini), EMBED_MODEL, EMBED_DIM,
POLICY_MIN_SCORE (ngưỡng cosine; mặc định 0.62 *(tự ước tính từ 8 câu thử tay: liên quan ≥0.65, câu rác ≤0.59)*, chỉnh sau khi xem điểm trên bộ câu thử).
"""
import json
import math
import os
import time
import urllib.error
import urllib.request

import ai  # noqa: F401  (nạp .env)
from policy_paths import available_platforms, paths

EMBED_MODEL = (os.environ.get("EMBED_MODEL") or "gemini-embedding-001").strip()
EMBED_DIM = int(os.environ.get("EMBED_DIM") or 768)
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


def embed_texts(texts, task_type="RETRIEVAL_DOCUMENT", titles=None):
    """texts: list[str] → list[list[float]] đã chuẩn hoá L2. task_type: RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY."""
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


_stores = {}  # platform → (chunks, {chunk_id: vector}); nạp một lần mỗi sàn


def _load(platform):
    if platform not in _stores:
        p = paths(platform)
        chunks, vectors = [], {}
        if os.path.exists(p["chunks"]) and os.path.exists(p["index"]):
            with open(p["chunks"], encoding="utf-8") as f:
                chunks = [json.loads(line) for line in f if line.strip()]
            with open(p["index"], encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]
            vectors = {r["chunk_id"]: r["vector"] for r in rows
                       if r.get("embed_model") == EMBED_MODEL and r.get("dim") == EMBED_DIM}
        _stores[platform] = (chunks, vectors)
    return _stores[platform]


def search(query, platform="tiktok", policy_type="", k=4, min_score=None):
    """Trả tối đa k chunk có cosine ≥ min_score, trong kho của platform (và policy_type nếu có). Không có → [].
    platform="" → tìm trên mọi sàn đã có kho (available_platforms())."""
    pool, vectors = [], {}
    for plat in ([platform] if platform else available_platforms()):
        chunks, vecs = _load(plat)
        vectors.update(vecs)
        pool.extend(c for c in chunks
                    if c["chunk_id"] in vecs and (not policy_type or c["policy_type"] == policy_type))
    if not pool or not query.strip():
        return []
    q = embed_texts([query], task_type="RETRIEVAL_QUERY")[0]
    floor = MIN_SCORE if min_score is None else min_score
    scored = []
    for c in pool:
        s = sum(a * b for a, b in zip(q, vectors[c["chunk_id"]]))
        if s >= floor:
            scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    return [{"chunk_id": c["chunk_id"], "text": c["context_header"] + "\n" + c["text"], "url": c["url"],
             "effective_date": c.get("effective_date"), "updated_at": c.get("updated_at"), "fetched_at": c.get("fetched_at"), "score": round(s, 4)}
            for s, c in scored[:k]]
