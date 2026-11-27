"""Embed <kho sàn>/chunks.jsonl bằng Gemini → <kho sàn>/index.jsonl (kho sàn: codebase/policy_paths.py). Tăng dần: chunk không đổi thì không gọi lại API.

Một chunk được coi là "không đổi" khi cùng chunk_id + hash của chuỗi được embed + embed_model + dim.
Gọi qua codebase/retrieval.embed_texts (taskType=RETRIEVAL_DOCUMENT, title=context_header, vector chuẩn hoá L2).

    python scripts/policies/embed.py [--platform tiktok] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, paths  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "codebase"))
import retrieval  # noqa: E402


def text_hash(c):
    """Hash đúng chuỗi được embed → sửa logic chunk mà quên tăng chunker_version vẫn không dùng nhầm vector cũ."""
    return hashlib.sha256((c["context_header"] + "\n" + c["text"]).encode("utf-8")).hexdigest()[:16]


def key(c):
    return (c["chunk_id"], text_hash(c))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="tiktok")
    ap.add_argument("--dry-run", action="store_true", help="chỉ đếm số chunk cần embed, không gọi API")
    a = ap.parse_args()
    P = paths(a.platform)
    with open(P["chunks"], encoding="utf-8") as f:
        chunks = [json.loads(l) for l in f if l.strip()]

    old = {}
    if os.path.exists(P["index"]):
        with open(P["index"], encoding="utf-8") as f:
            for l in f:
                r = json.loads(l)
                if r.get("embed_model") == retrieval.EMBED_MODEL and r.get("dim") == retrieval.EMBED_DIM:
                    old[(r["chunk_id"], r.get("text_hash"))] = r

    todo = [c for c in chunks if key(c) not in old]
    chars = sum(len(c["context_header"]) + 1 + len(c["text"]) for c in todo)
    print("%d chunk · đã có %d · cần embed %d (%d ký tự)" % (len(chunks), len(chunks) - len(todo), len(todo), chars))
    if a.dry_run or not todo:
        if not todo:
            _write(P["index"], chunks, old)
        return

    vectors = retrieval.embed_texts([c["context_header"] + "\n" + c["text"] for c in todo],
                                    task_type="RETRIEVAL_DOCUMENT", titles=[c["context_header"] for c in todo])
    for c, v in zip(todo, vectors):
        old[key(c)] = {"chunk_id": c["chunk_id"], "text_hash": text_hash(c), "content_hash": c["content_hash"],
                       "chunker_version": c["chunker_version"], "embed_model": retrieval.EMBED_MODEL,
                       "dim": retrieval.EMBED_DIM, "vector": [round(x, 6) for x in v]}
    _write(P["index"], chunks, old)
    print("đã embed %d chunk bằng %s (dim %d) → %s" % (len(todo), retrieval.EMBED_MODEL, retrieval.EMBED_DIM, P["index"]))


def _write(index_path, chunks, rows):
    """Chỉ giữ vector của chunk hiện có (chunk đã xoá / đổi nội dung thì bỏ vector cũ)."""
    with open(index_path, "w", encoding="utf-8") as f:
        for c in chunks:
            r = rows.get(key(c))
            if r:
                f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
