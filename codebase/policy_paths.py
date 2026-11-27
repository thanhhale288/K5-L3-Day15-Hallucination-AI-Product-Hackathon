"""Đường dẫn kho chính sách theo từng sàn — CHỖ DUY NHẤT khai báo sàn nào nằm ở thư mục nào.

Mỗi sàn một thư mục riêng (tránh đè file khi nhiều người cùng làm):
    data/<thư mục sàn>/policies/
        raw-<platform>/   HTML gốc (không commit)
        clean/            Markdown đã làm sạch
        manifest.csv · chunks.jsonl · index.jsonl
Thêm sàn: thêm 1 dòng vào PLATFORM_DIRS (không có thì mặc định data/<platform>/policies).
Kho GỘP 3 sàn (hợp đồng H1, scripts/policies/merge.py): data/policies/ — gọi bằng platform "all".
Chỉ thư viện chuẩn.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PLATFORM_DIRS = {
    "tiktok": "tiktok_shop",
    "shopee": "shopee",
    "lazada": "lazada",
}


MERGED = "all"  # tên giả cho kho gộp data/policies/


def policy_dir(platform):
    if platform == MERGED:
        return os.path.join(ROOT, "data", "policies")
    return os.path.join(ROOT, "data", PLATFORM_DIRS.get(platform, platform), "policies")


def paths(platform):
    """→ dict đường dẫn của một sàn: dir, raw, clean, manifest, chunks, index."""
    d = policy_dir(platform)
    return {
        "dir": d,
        "raw": os.path.join(d, "raw-" + platform),
        "clean": os.path.join(d, "clean"),
        "manifest": os.path.join(d, "manifest.csv"),
        "chunks": os.path.join(d, "chunks.jsonl"),
        "index": os.path.join(d, "index.jsonl"),
    }


def available_platforms():
    """Các sàn tìm được: cả 3 khi đã có kho gộp; không thì các sàn có đủ chunks.jsonl + index.jsonl riêng."""
    if os.path.exists(paths(MERGED)["chunks"]):
        return list(PLATFORM_DIRS)
    return [p for p in PLATFORM_DIRS if os.path.exists(paths(p)["chunks"]) and os.path.exists(paths(p)["index"])]
