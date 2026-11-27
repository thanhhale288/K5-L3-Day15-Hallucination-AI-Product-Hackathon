#!/usr/bin/env python3
"""Sinh bộ FILE XLSX MẪU "export từ sàn" của một shop demo trong 1 tháng — để demo luồng import.

DỮ LIỆU GIẢ LẬP. Cột và tên sheet MÔ PHỎNG file export của Shopee / TikTok Shop / Lazada theo hiểu biết
của nhóm, KHÔNG phải định dạng chính thức — trước demo nên đối chiếu với file export thật (tài khoản của
thành viên, đã che thông tin) và sửa EXPORT_FORMATS bên dưới cho khớp.

Đầu ra data/demo_import/:
  shopee_don_hang_2026-11.xlsx   sheet "Đơn hàng" (1 dòng / đơn, có cột từng khoản phí) + "Quảng cáo" + "Đọc tôi"
  tiktok_don_hang_2026-11.xlsx   như trên, tên cột kiểu TikTok Shop
  lazada_don_hang_2026-11.xlsx   như trên, tên cột kiểu Lazada (không có sheet quảng cáo)
  gia_von_mau.xlsx               file shop tự điền: giá vốn, ngành theo SKU; loại shop theo sàn
  _dap_an_2026-11.json           ĐÁP ÁN (agent không đọc): các "câu chuyện" cài sẵn trong tháng

Cần openpyxl:  python -m pip install openpyxl
  python data/make_demo_import.py [--seed 42] [--month 2026-11]
Đọc lại + phân tích:  python data/import_export.py data/demo_import/*.xlsx --cogs data/demo_import/gia_von_mau.xlsx
"""
from __future__ import annotations

import argparse
import calendar
import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
except ImportError:
    raise SystemExit("Thiếu openpyxl: python -m pip install openpyxl")

import fee_engine as fe

OUT = fe.DATA / "demo_import"

# (tiêu đề cột, trường chuẩn). Trường "fee:<fee_key>" là khoản phí (số DƯƠNG trong file export).
EXPORT_FORMATS = {
    "shopee": [
        ("Mã đơn hàng", "order_id"), ("Ngày đặt hàng", "order_date"), ("Trạng thái đơn hàng", "status"),
        ("SKU phân loại hàng", "sku"), ("Tên sản phẩm", "ten_sp"), ("Số lượng", "qty"),
        ("Giá gốc", "gia_goc"), ("Giá ưu đãi", "gia_ban"), ("Mã giảm giá của Shop", "voucher_shop"),
        ("Voucher đồng tài trợ (người bán chịu)", "fee:voucher_dong_tai_tro"),
        ("Phí cố định", "fee:phi_co_dinh"), ("Phí xử lý giao dịch", "fee:phi_xu_ly_giao_dich"),
        ("Phí dịch vụ Voucher Xtra", "fee:voucher_xtra"), ("Phí hoa hồng Tiếp thị liên kết", "fee:tiep_thi_lien_ket"),
        ("Phí hạ tầng", "fee:phi_ha_tang"), ("Thuế khấu trừ", "fee:thue_khau_tru"), ("Phí khác", "phi_khac"),
        ("Phí vận chuyển trả hàng", "fee:chi_phi_don_hoan"), ("Tổng tiền người bán nhận được", "payout"),
        ("Ngày thanh toán", "ngay_thanh_toan"),
    ],
    "tiktok": [
        ("ID đơn hàng", "order_id"), ("Thời gian tạo đơn", "order_date"), ("Trạng thái", "status"),
        ("SKU người bán", "sku"), ("Tên sản phẩm", "ten_sp"), ("Số lượng", "qty"), ("Giá gốc", "gia_goc"),
        ("Giá bán", "gia_ban"), ("Giảm giá của người bán", "voucher_shop"),
        ("Phí hoa hồng nền tảng", "fee:hoa_hong_nen_tang"), ("Phí giao dịch", "fee:phi_giao_dich"),
        ("Phí Voucher Extra", "fee:phi_voucher_extra"), ("Hoa hồng nhà sáng tạo (liên kết)", "fee:hoa_hong_lien_ket"),
        ("Thuế khấu trừ", "fee:thue_khau_tru"), ("Phí khác", "phi_khac"),
        ("Phí vận chuyển trả hàng", "fee:chi_phi_don_hoan"), ("Số tiền quyết toán", "payout"),
        ("Ngày quyết toán", "ngay_thanh_toan"),
    ],
    "lazada": [
        ("Mã đơn hàng", "order_id"), ("Ngày tạo đơn", "order_date"), ("Trạng thái", "status"),
        ("SKU người bán", "sku"), ("Tên sản phẩm", "ten_sp"), ("Số lượng", "qty"), ("Giá gốc", "gia_goc"),
        ("Giá bán", "gia_ban"), ("Giảm giá từ người bán", "voucher_shop"),
        ("Phí cố định", "fee:phi_co_dinh"), ("Phí thanh toán", "fee:phi_thanh_toan"),
        ("Phí dịch vụ Freeship Max", "fee:phi_freeship_max"), ("Hoa hồng Lazada Affiliate", "fee:tiep_thi_lien_ket"),
        ("Thuế khấu trừ", "fee:thue_khau_tru"), ("Phí khác", "phi_khac"),
        ("Phí vận chuyển trả hàng", "fee:chi_phi_don_hoan"), ("Số tiền thanh toán", "payout"),
        ("Ngày thanh toán", "ngay_thanh_toan"),
    ],
}
STATUS_LABEL = {
    "shopee": {"hoan_tat": "Hoàn thành", "huy": "Đã hủy", "hoan_hang": "Trả hàng/Hoàn tiền"},
    "tiktok": {"hoan_tat": "Đã hoàn thành", "huy": "Đã hủy", "hoan_hang": "Đã hoàn tiền"},
    "lazada": {"hoan_tat": "Đã giao", "huy": "Đã hủy", "hoan_hang": "Trả hàng"},
}
ADS_COLUMNS = ["Ngày", "Tên chiến dịch", "SKU", "Chi phí (đ)", "Lượt click", "Số đơn", "Doanh thu GMV (đ)", "ROAS"]
FILE_NAME = {"shopee": "shopee_don_hang_{m}.xlsx", "tiktok": "tiktok_don_hang_{m}.xlsx",
             "lazada": "lazada_don_hang_{m}.xlsx"}
ID_PREFIX = {"shopee": "SHP", "tiktok": "TTS", "lazada": "LZD"}
FIXED_TIME = datetime(2026, 12, 1, 9, 0, 0)

# Shop demo: 10 SKU. Mỗi SKU một "câu chuyện" để agent / phân tích phải tìm ra.
#   sku, tên, ngành, giá vốn, {sàn: (giá bán, voucher shop, chương trình bật?, % affiliate, tỉ lệ đơn qua affiliate,
#                                   tỉ lệ hoàn, số đơn/tháng)}
SKUS = [
    ("DM-AO01", "Áo thun cotton basic", "thoi_trang", 85_000,
     {"shopee": (189_000, 10_000, True, 15, 0.65, 0.04, 70), "tiktok": (185_000, 0, True, 20, 0.80, 0.05, 60),
      "lazada": (195_000, 0, False, 0, 0, 0.03, 15)}),
    ("DM-VA01", "Váy hoa nhí", "thoi_trang", 120_000,
     {"shopee": (299_000, 15_000, True, 8, 0.3, 0.05, 30), "tiktok": (289_000, 0, True, 10, 0.5, 0.18, 45),
      "lazada": (305_000, 0, True, 0, 0, 0.04, 10)}),
    ("DM-QJ01", "Quần jean ống suông", "thoi_trang", 160_000,
     {"shopee": (359_000, 20_000, True, 5, 0.2, 0.06, 25), "tiktok": (349_000, 10_000, False, 8, 0.3, 0.08, 15),
      "lazada": (365_000, 0, True, 0, 0, 0.05, 10)}),
    ("DM-TN01", "Tai nghe chống ồn", "dien_tu", 820_000,
     {"shopee": (1_390_000, 20_000, True, 0, 0, 0.03, 22), "tiktok": (1_350_000, 0, True, 5, 0.3, 0.03, 10),
      "lazada": (1_420_000, 0, True, 0, 0, 0.02, 12)}),
    ("DM-SC01", "Sạc nhanh 65W", "dien_tu", 230_000,
     {"shopee": (399_000, 10_000, True, 5, 0.2, 0.02, 30), "tiktok": (389_000, 0, True, 8, 0.4, 0.03, 20),
      "lazada": (409_000, 0, True, 0, 0, 0.02, 15)}),
    ("DM-SR01", "Serum vitamin C 30ml", "my_pham", 95_000,
     {"shopee": (259_000, 10_000, True, 10, 0.3, 0.02, 35), "tiktok": (249_000, 0, True, 15, 0.6, 0.03, 20),
      "lazada": (265_000, 0, False, 0, 0, 0.02, 10)}),
    ("DM-KC01", "Kem chống nắng 50ml", "my_pham", 80_000,
     {"shopee": (199_000, 5_000, True, 8, 0.3, 0.02, 25), "tiktok": (195_000, 0, True, 12, 0.5, 0.02, 15),
      "lazada": (205_000, 0, True, 0, 0, 0.02, 10)}),
    ("DM-HD01", "Bộ hộp đựng thực phẩm", "nha_cua", 110_000,
     {"shopee": (229_000, 10_000, False, 0, 0, 0.03, 15), "tiktok": (225_000, 0, False, 5, 0.2, 0.03, 0),
      "lazada": (235_000, 0, True, 0, 0, 0.02, 8)}),
    ("DM-HC01", "Hạt điều rang muối 500g", "thuc_pham", 150_000,
     {"shopee": (239_000, 0, True, 5, 0.2, 0.01, 8), "tiktok": (235_000, 0, False, 5, 0.2, 0.01, 0),
      "lazada": (0, 0, False, 0, 0, 0, 0)}),
    ("DM-BS01", "Bình sữa chống sặc", "me_be", None,          # giá vốn TRỐNG → agent phải hỏi
     {"shopee": (249_000, 10_000, True, 5, 0.2, 0.02, 0), "tiktok": (245_000, 0, True, 8, 0.3, 0.02, 0),
      "lazada": (255_000, 0, False, 0, 0, 0.02, 0)}),
]
SHOP_TYPE = {"shopee": "shop_thuong", "tiktok": "shop_thuong", "lazada": "shop_thuong"}
SELLER_TYPE = "ho_kinh_doanh"
CANCEL_RATE = 0.04
OVERCHARGE_SKU = ("shopee", "DM-TN01", 4)          # 4 đơn Voucher Xtra bị tính vượt trần 50.000đ
STRANGE = ("lazada", 3, ["Phí điều chỉnh", "Phí dịch vụ khác"])   # 3 đơn có "Phí khác" không khớp luật
ADS = [  # (sàn, sku, tên chiến dịch, phần doanh số quy cho QC, ROAS trên GMV mong muốn)
    ("shopee", "DM-SR01", "Serum - Tìm kiếm", 0.6, 2.2),       # dưới hoà vốn → lỗ
    ("shopee", "DM-AO01", "Áo thun - Khám phá", 0.4, 9.5),
    ("tiktok", "DM-VA01", "Váy hoa - Live", 0.5, 6.0),
]


def build_orders(rng, rules, month):
    y, m = map(int, month.split("-"))
    ndays = calendar.monthrange(y, m)[1]
    weights = [3.0 if d == 11 else (1.6 if d in (10, 12) else 1.0) for d in range(1, ndays + 1)]  # 11/11
    orders, seq = [], defaultdict(int)
    for sku, name, cat, cogs, plats in SKUS:
        for p, (price, vshop, prog_on, aff_rate, aff_share, ret_rate, n) in plats.items():
            for _ in range(n + (2 if sku == "DM-BS01" else 0) * (p == "shopee")):
                d = date(y, m, rng.choices(range(1, ndays + 1), weights)[0]).isoformat()
                u = rng.random()
                status = "huy" if u < CANCEL_RATE else ("hoan_hang" if u < CANCEL_RATE + ret_rate else "hoan_tat")
                qty = rng.choices([1, 2], [0.88, 0.12])[0]
                programs = set()
                prog_key = {"shopee": "voucher_xtra", "tiktok": "phi_voucher_extra", "lazada": "phi_freeship_max"}[p]
                if prog_on and rng.random() < 0.8:
                    programs.add(prog_key)
                if aff_rate and rng.random() < aff_share:
                    programs.add({"shopee": "tiep_thi_lien_ket", "tiktok": "hoa_hong_lien_ket",
                                  "lazada": "tiep_thi_lien_ket"}[p])
                seq[p] += 1
                o = {"order_id": f"{ID_PREFIX[p]}-DEMO-{d[5:7]}{d[8:10]}-{seq[p]:04d}", "platform": p, "sku": sku,
                     "ten_sp": name, "nganh": cat, "order_date": d, "status": status, "qty": qty,
                     "price": price, "gia_goc": round(price * 1.25, -3), "voucher_shop": vshop,
                     "shop_type": SHOP_TYPE[p], "seller_type": SELLER_TYPE, "programs": programs,
                     "affiliate_rate": float(aff_rate), "cofund_voucher": 0, "phi_khac": 0, "flags": []}
                if status == "huy":
                    o["lines"] = []
                else:
                    o["lines"] = fe.compute_lines(rules, o)
                orders.append(o)
    # câu chuyện: tính vượt trần Voucher Xtra
    p, sku, k = OVERCHARGE_SKU
    cands = [o for o in orders if o["platform"] == p and o["sku"] == sku and o["status"] == "hoan_tat"
             and "voucher_xtra" in o["programs"]]
    for o in rng.sample(cands, min(k, len(cands))):
        for x in o["lines"]:
            if x["fee_key"] == "voucher_xtra":
                rule = next(r for r in rules if r["rule_id"] == x["rule_id"])
                raw = round((o["price"] * o["qty"] - o["voucher_shop"]) * rule["rate"] / 100)
                o["flags"].append({"loai": "vuot_tran", "fee_key": "voucher_xtra", "dung": -x["amount_vnd"], "thuc": raw})
                x["amount_vnd"] = -raw
    # câu chuyện: phí khác không khớp luật
    p, k, names = STRANGE
    for o in rng.sample([o for o in orders if o["platform"] == p and o["status"] == "hoan_tat"], k):
        o["phi_khac"] = rng.choice([2_000, 3_000, 5_000])
        o["flags"].append({"loai": "dong_la", "ten": rng.choice(names), "thuc": o["phi_khac"]})
    for o in orders:
        base = o["price"] * o["qty"] - o["voucher_shop"]
        fees = -sum(x["amount_vnd"] for x in o["lines"]) + o["phi_khac"]
        o["payout"] = 0 if o["status"] == "huy" else ((base if o["status"] == "hoan_tat" else 0) - fees)
        o["ngay_thanh_toan"] = "" if o["status"] == "huy" else \
            (date.fromisoformat(o["order_date"]) + timedelta(days=rng.randint(7, 12))).isoformat()
    orders.sort(key=lambda o: (o["platform"], o["order_date"], o["order_id"]))
    return orders


def build_ads(rng, orders, month):
    rows = defaultdict(list)
    y, m = map(int, month.split("-"))
    ndays = calendar.monthrange(y, m)[1]
    for p, sku, camp, share, roas in ADS:
        gmv_sku = sum(o["price"] * o["qty"] for o in orders if o["platform"] == p and o["sku"] == sku
                      and o["status"] != "huy")
        spend = round(gmv_sku * share / roas, -3)          # doanh số quy cho QC không vượt doanh số thật
        daily = [spend / ndays * rng.uniform(0.7, 1.3) for _ in range(ndays)]
        scale = spend / sum(daily)
        for d in range(ndays):
            cost = round(daily[d] * scale, -3)
            gmv = round(cost * roas * rng.uniform(0.85, 1.15), -3)
            n = max(0, round(gmv / next(o["price"] for o in orders if o["sku"] == sku and o["platform"] == p)))
            rows[p].append([date(y, m, d + 1).isoformat(), camp, sku, cost, round(cost / 1500), n, gmv,
                            round(gmv / cost, 2) if cost else 0])
    return rows


def style_header(ws):
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="F2E6D9")
    ws.freeze_panes = "A2"
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = max(12, min(38, len(str(col[0].value)) + 4))


def readme_sheet(wb, platform, month):
    ws = wb.create_sheet("Đọc tôi")
    for line in [
        f"FILE MẪU GIẢ LẬP — {fe.PLATFORM_NAME[platform]} — tháng {month} — Shop Demo (không phải shop thật)",
        "Sinh bằng data/make_demo_import.py (có seed). Cột mô phỏng file export của sàn, KHÔNG phải định dạng chính thức.",
        "Phí ghi số dương (số sàn đã trừ). Phí tính theo bảng phí tạm data/synthetic/fee_rules_v0.csv (chưa đối chiếu).",
        "Dùng để demo: import vào hệ thống → soi từng đơn + phân tích tháng. Không phải bằng chứng pain.",
    ]:
        ws.append([line])
    ws.column_dimensions["A"].width = 120


def write_platform_file(path, platform, orders, ads_rows, month):
    wb = Workbook()
    wb.properties.created = wb.properties.modified = FIXED_TIME
    ws = wb.active
    ws.title = "Đơn hàng"
    fmt = EXPORT_FORMATS[platform]
    ws.append([h for h, _ in fmt])
    for o in orders:
        fees = defaultdict(int)
        for x in o["lines"]:
            fees[x["fee_key"]] += -x["amount_vnd"]
        row = []
        for _, field in fmt:
            if field.startswith("fee:"):
                row.append(fees.get(field[4:], 0))
            elif field == "status":
                row.append(STATUS_LABEL[platform][o["status"]])
            elif field == "order_date":
                h = sum(map(ord, o["order_id"]))
                row.append(f"{o['order_date']} {8 + h % 14:02d}:{(h * 7) % 60:02d}")
            elif field == "gia_ban":
                row.append(o["price"])
            else:
                row.append(o.get(field, ""))
        ws.append(row)
    style_header(ws)
    if ads_rows:
        wa = wb.create_sheet("Quảng cáo")
        wa.append(ADS_COLUMNS)
        for r in ads_rows:
            wa.append(r)
        style_header(wa)
    readme_sheet(wb, platform, month)
    wb.save(path)


def write_cogs_file(path):
    wb = Workbook()
    wb.properties.created = wb.properties.modified = FIXED_TIME
    ws = wb.active
    ws.title = "Giá vốn"
    ws.append(["SKU", "Tên sản phẩm", "Ngành hàng", "Giá vốn / đơn vị (đ)", "Ghi chú"])
    for sku, name, cat, cogs, _ in SKUS:
        ws.append([sku, name, fe.CATEGORIES[cat], cogs if cogs else "", "" if cogs else "Chưa nhập giá vốn"])
    style_header(ws)
    wi = wb.create_sheet("Thông tin shop")
    wi.append(["Sàn", "Loại shop", "Loại người bán"])
    for p in fe.PLATFORMS:
        wi.append([fe.PLATFORM_NAME[p], {"shop_thuong": "Shop thường", "mall": "Mall"}[SHOP_TYPE[p]],
                   "Hộ kinh doanh" if SELLER_TYPE == "ho_kinh_doanh" else "Công ty"])
    style_header(wi)
    wb.save(path)


def answer_key(orders, ads, month):
    cogs = {s[0]: s[3] for s in SKUS}
    by = defaultdict(lambda: {"don": 0, "hoan_tat": 0, "huy": 0, "hoan_hang": 0, "doanh_thu": 0, "phi": 0,
                              "tien_ve": 0, "gia_von": 0, "cong_tac": defaultdict(int)})
    for o in orders:
        k = (o["platform"], o["sku"])
        b = by[k]
        b["don"] += 1
        b[o["status"]] += 1
        if o["status"] == "hoan_tat":
            b["doanh_thu"] += o["price"] * o["qty"] - o["voucher_shop"]
            b["gia_von"] += (cogs[o["sku"]] or 0) * o["qty"]
        b["phi"] += -sum(x["amount_vnd"] for x in o["lines"]) + o["phi_khac"]
        b["tien_ve"] += o["payout"]
        for x in o["lines"]:
            if x["loai"] == "cong_tac":
                b["cong_tac"][x["ten_dong"]] += -x["amount_vnd"]
    sku_rows = []
    for (p, sku), b in sorted(by.items()):
        lai = b["tien_ve"] - b["gia_von"] if cogs[sku] else None
        top = max(b["cong_tac"], key=b["cong_tac"].get) if b["cong_tac"] else None
        sku_rows.append({"platform": p, "sku": sku, "don": b["don"], "hoan_tat": b["hoan_tat"], "huy": b["huy"],
                         "hoan_hang": b["hoan_hang"], "doanh_thu": b["doanh_thu"], "tong_phi": b["phi"],
                         "tien_ve": b["tien_ve"], "gia_von": b["gia_von"] if cogs[sku] else None, "lai": lai,
                         "cong_tac_lon_nhat": top, "cong_tac_vnd": b["cong_tac"][top] if top else 0,
                         "ti_le_an_lai": round(b["cong_tac"][top] / lai, 3) if top and lai and lai > 0 else None})
    ads_rows = []
    for p, sku, camp, _, _ in ADS:
        rs = [r for r in ads[p] if r[1] == camp]
        spend, gmv = sum(r[3] for r in rs), sum(r[6] for r in rs)
        row = next(x for x in sku_rows if x["platform"] == p and x["sku"] == sku)
        margin = row["lai"] / row["doanh_thu"] if row["lai"] is not None and row["doanh_thu"] else None
        ads_rows.append({"platform": p, "sku": sku, "chien_dich": camp, "chi_phi": spend, "gmv": gmv,
                         "roas": round(gmv / spend, 2), "bien_lai_truoc_qc": round(margin, 3) if margin else None,
                         "roas_hoa_von": round(1 / margin, 2) if margin and margin > 0 else None,
                         "lo_hay_lai": None if not margin or margin <= 0 else
                         ("lỗ" if gmv / spend < 1 / margin else "lãi")})
    flags = [{"order_id": o["order_id"], "platform": o["platform"], **f} for o in orders for f in o["flags"]]
    return {
        "ghi_chu": "ĐÁP ÁN cho data/demo_import (giả lập). Agent / công cụ KHÔNG đọc file này.",
        "thang": month,
        "cau_chuyen": [
            "DM-AO01: hoa hồng tiếp thị liên kết (Shopee 15%, TikTok 20%) ăn phần lớn lãi",
            "DM-TN01 Shopee: 4 đơn Phí Voucher Xtra bị tính vượt trần 50.000đ/sản phẩm → Escalate",
            "DM-VA01 TikTok: tỉ lệ trả hàng ~18% → phí vận chuyển trả hàng",
            "Quảng cáo 'Serum - Tìm kiếm' (Shopee): ROAS trên GMV ~2,2, thấp hơn ROAS hoà vốn → đang lỗ",
            "Lazada: 3 đơn có 'Phí khác' không khớp luật nào → Escalate",
            "DM-BS01: chưa nhập giá vốn → Ask (không có đơn trong tháng trừ 2 đơn Shopee)",
        ],
        "dong_lech_luat": flags,
        "theo_sku_san": sku_rows,
        "quang_cao": ads_rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--month", default="2026-11")
    ap.add_argument("--fee-rules", default=None)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    rng = random.Random(a.seed)
    rules, rules_path = fe.load_rules(a.fee_rules)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    orders = build_orders(rng, rules, a.month)
    ads = build_ads(rng, orders, a.month)
    for p in fe.PLATFORMS:
        write_platform_file(out / FILE_NAME[p].format(m=a.month), p, [o for o in orders if o["platform"] == p],
                            ads.get(p), a.month)
    write_cogs_file(out / "gia_von_mau.xlsx")
    key = answer_key(orders, ads, a.month)
    (out / f"_dap_an_{a.month}.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Bảng phí: {rules_path.name} · seed {a.seed} · tháng {a.month} → {out.relative_to(fe.DATA.parent)}/")
    for p in fe.PLATFORMS:
        os_ = [o for o in orders if o["platform"] == p]
        print(f"  {fe.PLATFORM_NAME[p]:12s} {len(os_):4d} đơn · hoàn tất {sum(o['status'] == 'hoan_tat' for o in os_)}"
              f" · huỷ {sum(o['status'] == 'huy' for o in os_)} · trả hàng {sum(o['status'] == 'hoan_hang' for o in os_)}")
    print(f"  dòng lệch luật cài sẵn: {len(key['dong_lech_luat'])} · chiến dịch QC: {len(key['quang_cao'])}")
    for r in key["quang_cao"]:
        print(f"    {r['chien_dich']:22s} ROAS {r['roas']} · hoà vốn {r['roas_hoa_von']} → {r['lo_hay_lai']}")


if __name__ == "__main__":
    main()
