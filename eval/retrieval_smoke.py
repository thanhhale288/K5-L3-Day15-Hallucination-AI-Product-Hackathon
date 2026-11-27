"""Offline top-5 corpus smoke test (lexical baseline, not production search).

Loads the current raw chunks for all three platforms, filters by platform and
by effective_date only where that metadata exists, then checks pinned gold
chunk IDs against token-overlap top-5. It does not call embeddings or
codebase.tools.search_policy. Run: python eval/retrieval_smoke.py
"""
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "shopee": (ROOT / "data" / "shopee_policy" / "seller" / "chunks.jsonl", "content"),
    "tiktok": (ROOT / "data" / "tiktok_shop" / "policies" / "chunks.jsonl", "text"),
    "lazada": (ROOT / "data" / "lazada" / "policies" / "chunk_lazada.json", "text"),
}
CASES = [
    ("Q01", "shopee", "Shopee phí cố định hoa hồng cố định người bán", "shopee-vn-77243-c054", None),
    ("Q02", "shopee", "Shopee mục phí thanh toán khoản phí và khấu trừ giao dịch", "shopee-vn-77243-c052", None),
    ("Q03", "shopee", "Shopee tiếp thị liên kết affiliate hoa hồng người bán", "shopee-vn-183831-c008", None),
    ("Q04", "shopee", "Shopee chương trình voucher mã ưu đãi đồng tài trợ phí", "shopee-vn-166085-c004", None),
    ("Q05", "tiktok", "TikTok Shop phí giao dịch sau khi đơn giao thành công", "tiktok-753295858337537#001", None),
    ("Q06", "tiktok", "TikTok Shop phí hoa hồng nền tảng tính theo ngành hàng", "tiktok-3396736626312961#001", None),
    ("Q07", "tiktok", "TikTok Shop quy trình trả hàng hoàn tiền người bán", "tiktok-1398156382422785#001", None),
    ("Q08", "lazada", "Lazada phí cố định LazMall máy in di động", "lazada-phi-co-dinh-lazmall#008", "2026-11-12"),
    ("Q09", "lazada", "Lazada trả hàng nhà bán hàng quy trình chỉ hoàn tiền", "lazada-hoan-tra-chi-hoan-tien#001", None),
    ("Q10", "lazada", "Lazada lý do nhà bán hàng chưa nhận thanh toán", "lazada-ly-do-chua-nhan-thanh-toan#001", None),
]


def tokens(value):
    value = unicodedata.normalize("NFD", value.lower())
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return set(re.findall(r"[a-z0-9]+", value))


def load_chunks():
    result = {}
    for platform, (path, text_key) in FILES.items():
        if path.suffix == ".json":
            rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        elif path.exists():
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            rows = []
        normalized = []
        for row in rows:
            section = row.get("section_path", [])
            if isinstance(section, list):
                section = " ".join(section)
            normalized.append({
                "chunk_id": row["chunk_id"],
                "text": row.get(text_key, ""),
                "metadata": " ".join(str(row.get(k, "") or "") for k in ("title", "section", "category", "context_header"))
                            + " " + str(section),
                "effective_date": row.get("effective_date"),
            })
        result[platform] = normalized
    return result


def main():
    stores = load_chunks()
    passed = 0
    by_platform = {p: [0, 0] for p in FILES}
    missing_date = {p: sum(not c["effective_date"] for c in chunks) for p, chunks in stores.items()}
    for case_id, platform, query, target_id, order_date in CASES:
        pool = [c for c in stores[platform]
                if not order_date or not c["effective_date"] or str(c["effective_date"])[:10] <= order_date]
        target = next((c for c in pool if c["chunk_id"] == target_id), None)
        if target is None:
            raise SystemExit(f"{case_id}: gold chunk {target_id} missing after platform/date filter")
        ranked = sorted(pool,
                        key=lambda c: (len(tokens(query) & tokens(c["text"] + " " + c["metadata"])), c["chunk_id"]),
                        reverse=True)
        rank = next(i for i, c in enumerate(ranked, 1) if c["chunk_id"] == target_id)
        ok = rank <= 5
        by_platform[platform][1] += 1
        by_platform[platform][0] += int(ok)
        passed += int(ok)
        date_note = "date_filter=applied" if order_date and target["effective_date"] else "date_filter=metadata-missing" if order_date else "date_filter=not-requested"
        print(f"{case_id} {'PASS' if ok else 'FAIL'} platform={platform} target={target_id} rank={rank} {date_note}")

    print(f"Top-5 lexical recall: {passed}/{len(CASES)} = {passed / len(CASES):.0%}")
    for platform, (ok, total) in by_platform.items():
        print(f"{platform}: {ok}/{total} top-5; chunks={len(stores[platform])}; missing effective_date={missing_date[platform]}")
    print("Not production retrieval: token-overlap only; production hybrid/vector test requires indexed, date-tagged corpora and embedding credentials.")


if __name__ == "__main__":
    main()
