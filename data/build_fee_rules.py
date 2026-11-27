#!/usr/bin/env python3
"""TH-4: dựng data/fee_rules.csv (hợp đồng H2) cho cả 3 sàn từ bảng tạm v0 + đối chiếu kho chính sách đã crawl.

    python data/build_fee_rules.py          # ghi data/fee_rules.csv, in bảng đối chiếu
    python data/fee_engine.py --check       # đơn mẫu H4 vẫn phải ra 123.520 / 28.520

Nguyên tắc:
  1. GIỮ NGUYÊN tỉ lệ, trần, ngày và rule_id của v0 (data/fee_engine.build_v0_rules). Đáp án bộ câu thử
     (eval/benchmark.csv) và data/synthetic/line_answers.csv được sinh từ các số này; đổi số ở đây mà
     không sinh lại data thì tool và đáp án lệch nhau. Chỗ chính sách chính thức KHÁC v0 → ghi ở
     data/fee_rules_review.md cho Hà soát (HA-7), không tự sửa.
  2. Gắn chunk_id (kho gộp data/policies/chunks.jsonl, đúng sàn) cho luật có đoạn chính sách giải thích được.
     Chỉ gắn khi đoạn đó KHÔNG mâu thuẫn với số của luật (tránh agent trích đoạn ghi số khác số code tính).
  3. da_doi_chieu: chinh_thuc = tỉ lệ / mức phí VÀ ngày hiệu lực khớp trang chính sách đã crawl ·
     bao_chi = theo báo chí, chưa khớp trang chính sách · gia_dinh = nhóm tự đặt *(tự ước tính)*.
  4. ten_cu: nhiều tên cách nhau bằng " | " (lookup_fee_rule so khớp mọi tên).
  5. Thêm luật chính thức v0 còn thiếu (không nằm trong LINE_ORDER nên không đổi đơn giả đã sinh).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA))
import fee_engine as fe  # noqa: E402

CHUNKS = DATA / "policies" / "chunks.jsonl"
OUT = fe.FEE_RULES_OFFICIAL

# (platform, fee_key, điều kiện trên dòng v0) → cập nhật. Điều kiện: dict cột → giá trị phải bằng.
EVIDENCE = [
    # ── Shopee ──
    # Corpus 741c0ab (banhang.shopee.vn/edu + help.shopee.vn) thay kho cũ: bài 77243/77262/166085 không còn.
    ("shopee", "phi_co_dinh", {"ap_dung": "shop_thuong"},
     {"chunk_id": "shopee-10666#001"}),     # định nghĩa phí cố định, không ghi tỉ lệ. Biểu phí 27540 KHÁC v0 → review
    ("shopee", "phi_co_dinh", {"ap_dung": "mall"},
     {"chunk_id": "shopee-21087#001"}),     # định nghĩa phí cố định Mall, không ghi tỉ lệ. Biểu phí 27541 KHÁC v0 → review
    ("shopee", "phi_xu_ly_giao_dich", {"ap_dung": "shop_thuong", "rate": 6.0},
     {"chunk_id": "shopee-2150#002", "da_doi_chieu": "chinh_thuc"}),    # 6% từ 01/05/2026 (không thuộc Mall)
    ("shopee", "phi_xu_ly_giao_dich", {"ap_dung": "mall", "rate": 6.0, "hieu_luc_tu": "2026-05-08"},
     {"chunk_id": "shopee-2150#002", "da_doi_chieu": "chinh_thuc"}),    # 6% từ 08/05/2026 (Shopee Mall)
    ("shopee", "phi_xu_ly_giao_dich", {}, {"ten_cu": "Phí thanh toán"}),
    ("shopee", "tiep_thi_lien_ket", {},       # 4.2: Phí Hoa Hồng PPS = Tỷ Lệ Hoa Hồng × Giá Trị Mua Thuần
     {"chunk_id": "shopee-183831#006", "ten_cu": "Hoa hồng tiếp thị liên kết | Phí Affiliate | Hoa hồng Affiliate"}),
    # Đồng tài trợ: mọi đoạn của bài 26053 ghi người bán chịu 40% (trần 50.000đ/sp) từ 23/05/2026, v0 tính 50%
    # → KHÔNG gắn chunk_id cho tới khi sửa tỉ lệ + sinh lại data (xem data/fee_rules_review.md).
    ("shopee", "voucher_dong_tai_tro", {},
     {"ten_cu": "Voucher đồng tài trợ | Mã ưu đãi đồng tài trợ"}),
    ("shopee", "phi_ha_tang", {},             # "mức thu 3.000Đ ... cho mỗi đơn hàng ... tạo từ 01/07/2025"
     {"chunk_id": "shopee-25223#001", "da_doi_chieu": "chinh_thuc", "ten_cu": "Phí dịch vụ hạ tầng"}),
    ("shopee", "chi_phi_don_hoan", {},        # mục 7.1: người bán chịu phí vận chuyển hoàn trả
     {"chunk_id": "shopee-77251#009", "ten_cu": "Chi phí đơn hoàn | Phí trả hàng"}),
    ("shopee", "thue_khau_tru", {}, {"ten_cu": "Thuế | Thuế GTGT và TNCN"}),
    # ── TikTok Shop ──
    ("tiktok", "phi_giao_dich", {"rate": 6.0},
     {"chunk_id": "tiktok-753295858337537#002"}),             # 6% khớp; ngày lệch → xem review
    ("tiktok", "hoa_hong_nen_tang", {},
     {"chunk_id": "tiktok-3396736626312961#001", "ten_cu": "Phí hoa hồng | Phí hoa hồng cố định"}),
    ("tiktok", "hoa_hong_lien_ket", {},
     {"ten_cu": "Hoa hồng liên kết | Phí tiếp thị liên kết | Hoa hồng Affiliate"}),
    ("tiktok", "chi_phi_don_hoan", {},
     {"chunk_id": "tiktok-1398156382422785#005", "ten_cu": "Phí vận chuyển trả hàng thực tế | Chi phí đơn hoàn"}),
    ("tiktok", "thue_khau_tru", {}, {"ten_cu": "Thuế | Thuế GTGT và TNCN"}),
    # ── Lazada ──
    ("lazada", "tiep_thi_lien_ket", {}, {"ten_cu": "Phí tiếp thị liên kết | Hoa hồng Affiliate"}),
    ("lazada", "chi_phi_don_hoan", {}, {"ten_cu": "Chi phí đơn hoàn"}),
    ("lazada", "thue_khau_tru", {}, {"ten_cu": "Thuế | Thuế GTGT và TNCN"}),
]

# Luật chính thức v0 chưa có. Mỗi dòng dẫn chunk ghi rõ số và ngày.
EXTRA = [
    # "Phí Xử Lý Đơn Hàng ... thu từ ngày 27/10/2025 ... cố định là 3000 đồng (đã bao gồm thuế)"
    fe._r("tiktok", "phi_xu_ly_don_hang", "Phí xử lý đơn hàng", "bat_buoc", "don", per_order=3_000,
          tu="2025-10-27", url="", doi_chieu="chinh_thuc") | {"chunk_id": "tiktok-8858869405370113#004"},
]


def _load_chunks() -> dict:
    if not CHUNKS.exists():
        sys.exit("thiếu %s — chạy trước: python scripts/policies/merge.py" % CHUNKS)
    with CHUNKS.open(encoding="utf-8") as f:
        return {c["chunk_id"]: c for c in map(json.loads, f) if c}


def _match(row: dict, cond: dict) -> bool:
    for k, v in cond.items():
        x = row.get(k)
        if isinstance(v, float):
            if x in ("", None) or abs(float(x) - v) > 1e-9:
                return False
        elif x != v:
            return False
    return True


def build() -> list[dict]:
    chunks = _load_chunks()
    rows = fe.build_v0_rules() + [dict(r) for r in EXTRA]
    for r in rows:
        for plat, key, cond, upd in EVIDENCE:
            if r["platform"] == plat and r["fee_key"] == key and _match(r, cond):
                r.update(upd)
        cid = r.get("chunk_id")
        if cid:
            c = chunks.get(cid)
            assert c is not None, "chunk_id %s không có trong kho gộp" % cid
            assert c["platform"] == r["platform"], "luật %s trỏ chunk sàn khác" % r["rule_id"]
            r["nguon_url"] = c["url"] or r["nguon_url"]   # nguồn = trang chính sách đã crawl
    ids = [r["rule_id"] for r in rows]
    assert len(ids) == len(set(ids)), "rule_id trùng"
    return rows


def write(rows: list[dict], path: Path = OUT) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fe.COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fe.COLUMNS})
    return path


if __name__ == "__main__":
    rows = build()
    p = write(rows)
    print("Đã ghi %s · %d luật" % (p.relative_to(DATA.parent), len(rows)))
    for plat in fe.PLATFORMS:
        rs = [r for r in rows if r["platform"] == plat]
        by = {k: sum(r["da_doi_chieu"] == k for r in rs) for k in ("chinh_thuc", "bao_chi", "gia_dinh")}
        print("  %-7s %3d luật · có chunk_id %3d · %s" % (plat, len(rs), sum(bool(r.get("chunk_id")) for r in rs), by))
