"""Smoke-test the production search_policy tool on 10 pinned corpus queries.

The corpus contains local BGE-M3 vectors. This smoke uses BM25+vector RRF when
the local encoder is installed and configured; otherwise production retrieval
falls back to BM25. No keys are stored here. Run: python eval/retrieval_smoke.py
"""
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codebase"))
from tools import search_policy  # noqa: E402
import retrieval as retrieval_backend  # noqa: E402


CASES = [
    ("Q01", "shopee", "phi co dinh hoa hong co dinh", "shopee-21087#001"),
    ("Q02", "shopee", "phi thanh toan phi xu ly giao dich", "shopee-2150#003"),
    ("Q03", "shopee", "affiliate hoa hong tiep thi lien ket", "shopee-183831#013"),
    ("Q04", "shopee", "voucher ma giam gia dong tai tro", "shopee-26053#003"),
    ("Q05", "tiktok", "phi giao dich don hang giao thanh cong", "tiktok-753295858337537#001"),
    ("Q06", "tiktok", "phi hoa hong nen tang tinh nhu the nao", "tiktok-3396736626312961#013"),
    ("Q07", "tiktok", "phuong thuc tra hang hoan tien phi van chuyen tra hang", "tiktok-1398156382422785#005"),
    ("Q08", "lazada", "phi co dinh lazmall ty le theo nganh hang", "lazada-1000149707#001"),
    ("Q09", "lazada", "tra hang chi hoan tien", "lazada-1000149692#001"),
    ("Q10", "lazada", "ly do chua nhan thanh toan", "lazada-1000149640#001"),
]
ORDER_DATE = "2026-11-12"


def main():
    try:
        probe = retrieval_backend.embed_texts(["kiem tra encoder policy"], task_type="RETRIEVAL_QUERY")[0]
        query_encoder_ready = len(probe) == 1024
    except Exception:
        query_encoder_ready = False

    by_platform = {p: [0, 0] for p in ("shopee", "tiktok", "lazada")}
    passed = 0
    for case_id, platform, query, target in CASES:
        hits = search_policy(query, platform, ORDER_DATE, k=5)
        ids = [h["chunk_id"] for h in hits]
        ok = target in ids
        passed += int(ok)
        by_platform[platform][1] += 1
        by_platform[platform][0] += int(ok)
        rank = ids.index(target) + 1 if ok else "-"
        wrong_platform = [cid for cid in ids if not cid.startswith(platform + "-")]
        if wrong_platform:
            raise SystemExit(f"{case_id}: search_policy leaked another platform: {wrong_platform}")
        print(f"{case_id} {'PASS' if ok else 'FAIL'} platform={platform} target={target} rank={rank}")
        if not ok:
            raise SystemExit(f"{case_id}: target chunk was not found in production top-5")

    # An explicitly effective-dated Lazada fee chunk must not be returned for
    # an order placed before that rate became effective.
    pre_effective = search_policy("phi co dinh lazmall ty le theo nganh hang", "lazada", "2026-05-01", k=5)
    blocked = "lazada-1000149707#001" not in [h["chunk_id"] for h in pre_effective]
    print(f"DATE_FILTER {'PASS' if blocked else 'FAIL'} effective_date=2026-06-04 order_date=2026-05-01")
    if not blocked:
        raise SystemExit("date filter returned a chunk before its effective date")
    print(f"Top-5 recall: {passed}/{len(CASES)} = {passed / len(CASES):.0%}")
    for platform, (ok, total) in by_platform.items():
        print(f"{platform}: {ok}/{total}")
    index_path = ROOT / "data" / "policies" / "index.jsonl"
    with index_path.open(encoding="utf-8") as f:
        indexed = [json.loads(line) for line in f if line.strip()]
    vector_count = sum(row.get("embed_model") == "bge-m3" and row.get("dim") == 1024
                       and len(row.get("vector", [])) == 1024 for row in indexed)
    encoder_installed = importlib.util.find_spec("sentence_transformers") is not None
    runtime_compatible = (retrieval_backend.LOCAL and retrieval_backend.EMBED_MODEL == "bge-m3"
                          and retrieval_backend.EMBED_DIM == 1024 and encoder_installed and query_encoder_ready)
    print(f"Index: {vector_count} compatible BGE-M3 vectors; sentence-transformers installed={encoder_installed}")
    print(f"Query encoder ready={query_encoder_ready}")
    print("Retrieval path: " + ("BM25+vector RRF" if runtime_compatible
                              else "BM25 fallback (configure EMBED_PROVIDER=local and install sentence-transformers)"))


if __name__ == "__main__":
    main()
