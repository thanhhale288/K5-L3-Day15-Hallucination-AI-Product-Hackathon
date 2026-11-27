"""Smoke-test the production search_policy tool on 10 pinned corpus queries.

When no embedding API key is set, codebase.retrieval falls back to BM25. With
a local key, it tests the configured BM25+vector RRF path. No keys are stored
here. Run: python eval/retrieval_smoke.py
"""
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codebase"))
from tools import search_policy  # noqa: E402


CASES = [
    ("Q01", "shopee", "phi co dinh hoa hong co dinh", "shopee-77243#054"),
    ("Q02", "shopee", "phi thanh toan phi xu ly giao dich", "shopee-77243#053"),
    ("Q03", "shopee", "affiliate hoa hong tiep thi lien ket", "shopee-183831#014"),
    ("Q04", "shopee", "voucher ma giam gia dong tai tro", "shopee-166085#004"),
    ("Q05", "tiktok", "phi giao dich don hang giao thanh cong", "tiktok-753295858337537#001"),
    ("Q06", "tiktok", "phi hoa hong nen tang tinh nhu the nao", "tiktok-3396736626312961#014"),
    ("Q07", "tiktok", "phuong thuc tra hang hoan tien phi van chuyen tra hang", "tiktok-1398156382422785#001"),
    ("Q08", "lazada", "phi co dinh lazmall may in di dong", "lazada-phi-co-dinh-lazmall#008"),
    ("Q09", "lazada", "tra hang chi hoan tien", "lazada-hoan-tra-chi-hoan-tien#001"),
    ("Q10", "lazada", "ly do chua nhan thanh toan", "lazada-ly-do-chua-nhan-thanh-toan#001"),
]
ORDER_DATE = "2026-11-12"


def main():
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
    pre_effective = search_policy("phi co dinh lazmall may in di dong", "lazada", "2026-05-01", k=5)
    blocked = "lazada-phi-co-dinh-lazmall#008" not in [h["chunk_id"] for h in pre_effective]
    print(f"DATE_FILTER {'PASS' if blocked else 'FAIL'} effective_date=2026-06-04 order_date=2026-05-01")
    if not blocked:
        raise SystemExit("date filter returned a chunk before its effective date")
    print(f"Top-5 recall: {passed}/{len(CASES)} = {passed / len(CASES):.0%}")
    for platform, (ok, total) in by_platform.items():
        print(f"{platform}: {ok}/{total}")
    key_present = bool(os.environ.get("EMBED_API_KEY") or
                       (os.environ.get("MODEL_PROVIDER", "").lower() == "gemini" and os.environ.get("API_KEY")))
    print("Retrieval path: hybrid BM25+vector configured; query embeddings "
          + ("available by local config" if key_present else "unavailable here, BM25 fallback used"))


if __name__ == "__main__":
    main()
