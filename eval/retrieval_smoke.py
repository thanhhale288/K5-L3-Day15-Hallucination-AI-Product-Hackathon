"""Smoke-test retrieval on all policy chunks currently present in data/.

Uses a deterministic token-overlap baseline, not codebase.tools.search_policy.
Gold targets are pinned to chunk IDs so expected results do not shift with
ranking changes. Run: python eval/retrieval_smoke.py
"""
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHUNK_FILES = [
    ROOT / "data" / "lazada" / "policies" / "chunk_lazada.json",
    ROOT / "data" / "policies" / "chunks.jsonl",
]

# These queries cover the actual policy data currently present. Add Shopee and
# TikTok query/target pairs when their chunk files arrive; never infer targets.
CASES = [
    ("LZ01", "lazada", "phí cố định nhóm loa thanh LazMall", "lazada-phi-co-dinh-lazmall#001", "2026-06-04"),
    ("LZ02", "lazada", "phí cố định phụ kiện micro quay phim", "lazada-phi-co-dinh-lazmall#002", "2026-06-04"),
    ("LZ03", "lazada", "phí cố định dock sạc và giá đỡ", "lazada-phi-co-dinh-lazmall#003", "2026-06-04"),
    ("LZ04", "lazada", "phí cố định máy in di động", "lazada-phi-co-dinh-lazmall#008", "2026-06-04"),
    ("LZ05", "lazada", "phí cố định máy xông mặt", "lazada-phi-co-dinh-lazmall#009", "2026-06-04"),
    ("LZ06", "lazada", "phí cố định máy ép và máy xay sinh tố", "lazada-phi-co-dinh-lazmall#010", "2026-06-04"),
    ("LZ07", "lazada", "thiết bị gia dụng thiết bị làm lạnh máy làm đá", "lazada-phi-co-dinh-lazmall#011", "2026-06-04"),
    ("LZ08", "lazada", "phí cố định máy làm bánh mì và nhào bột", "lazada-phi-co-dinh-lazmall#012", "2026-06-04"),
    ("LZ09", "lazada", "quy trình trả hàng nhà bán hàng Lazada chỉ hoàn tiền", "lazada-hoan-tra-chi-hoan-tien#001", None),
    ("LZ10", "lazada", "Lazada lý do nhà bán hàng chưa nhận thanh toán", "lazada-ly-do-chua-nhan-thanh-toan#001", None),
]


def tokens(value):
    normalized = unicodedata.normalize("NFD", value.lower())
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return set(re.findall(r"[a-z0-9]+", normalized))


def main():
    chunks = []
    present_files = []
    for path in CHUNK_FILES:
        if not path.exists() or not path.stat().st_size:
            continue
        present_files.append(str(path.relative_to(ROOT)))
        if path.suffix == ".json":
            chunks.extend(json.loads(path.read_text(encoding="utf-8")))
        else:
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.strip():
                    try:
                        chunks.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise SystemExit(f"{path}:{line_no}: JSONL lỗi: {exc}")
    if not chunks:
        raise SystemExit("Không tìm thấy policy chunks không rỗng.")

    seen = set()
    unique = []
    for chunk in chunks:
        key = chunk.get("chunk_id")
        if not key:
            raise SystemExit("Chunk thiếu chunk_id.")
        if key not in seen:
            seen.add(key)
            unique.append(chunk)
    chunks = unique
    passed = 0
    available_platforms = {c.get("platform") for c in chunks}
    scoped_count = 0
    for case_id, platform, query, target_id, order_date in CASES:
        if platform not in available_platforms:
            print(f"{case_id} SKIP platform={platform}: không có data")
            continue
        scoped = [c for c in chunks if c.get("platform") == platform
                  and (not order_date or not c.get("effective_date")
                       or c.get("effective_date") <= order_date)]
        scoped_count += 1
        target = next((c for c in scoped if c["chunk_id"] == target_id), None)
        if target is None:
            raise SystemExit(f"{case_id}: chunk đích {target_id!r} không có trong scope {platform}/{order_date}")
        ranked = sorted(
            scoped,
            key=lambda c: (len(tokens(query) & tokens(c.get("text", "") + " "
                                                       + " ".join(c.get("section_path", []))
                                                       + " " + c.get("context_header", ""))),
                           c["chunk_id"]),
            reverse=True,
        )
        top5 = [c["chunk_id"] for c in ranked[:5]]
        ok = target["chunk_id"] in top5
        passed += ok
        rank = next((i for i, c in enumerate(ranked, 1) if c["chunk_id"] == target["chunk_id"]), "-")
        print(f"{case_id} {'PASS' if ok else 'FAIL'} platform={platform} target={target['chunk_id']} rank={rank}")
    if scoped_count:
        print(f"Top-5 recall: {passed}/{scoped_count} = {passed / scoped_count:.0%}")
    print(f"Loaded {len(chunks)} unique chunks from: {', '.join(present_files)}")
    print(f"Platforms in loaded data: {', '.join(sorted(str(p) for p in available_platforms))}")
    print("Scope: token-overlap baseline with platform/date filter; does not test production search_policy.")


if __name__ == "__main__":
    main()
