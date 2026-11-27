#!/usr/bin/env python3
"""Bộ tính phí dùng chung cho 3 sàn (Shopee, TikTok Shop, Lazada) — thư viện chuẩn Python.

Dùng bởi: data/make_orders.py, data/make_demo_import.py, data/import_export.py.
Thái có thể gọi lại trong codebase/tools.py (lookup_fee_rule, expected_amount) để agent và data
giả luôn tính phí theo CÙNG một bảng.

Bảng phí:
  - Ưu tiên data/fee_rules.csv (hợp đồng H2, Thái giữ) nếu đã có.
  - Chưa có thì dùng data/synthetic/fee_rules_v0.csv — BẢNG TẠM do nhóm tự dựng từ mốc phí 2026
    trong CONTEXT.md. Cột da_doi_chieu: `bao_chi` (báo chí / blog đưa tin, chưa khớp trang chính sách)
    hoặc `gia_dinh` (nhóm tự đặt). KHÔNG có dòng `chinh_thuc` nào: chưa được trích dẫn như sự thật.

  python data/fee_engine.py --write-v0     # ghi lại data/synthetic/fee_rules_v0.csv
  python data/fee_engine.py --check        # tính lại đơn mẫu H4 (phải ra 123.520 và 28.520)
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent
FEE_RULES_OFFICIAL = DATA / "fee_rules.csv"
FEE_RULES_V0 = DATA / "synthetic" / "fee_rules_v0.csv"

COLUMNS = ["rule_id", "platform", "fee_key", "ten_hien_thi", "ten_cu", "loai", "base", "rate",
           "cap_vnd", "per_order_vnd", "ap_dung", "hieu_luc_tu", "hieu_luc_den", "nganh",
           "chunk_id", "nguon_url", "da_doi_chieu"]

PLATFORMS = ["shopee", "tiktok", "lazada"]
PLATFORM_NAME = {"shopee": "Shopee", "tiktok": "TikTok Shop", "lazada": "Lazada"}
CATEGORIES = {
    "thoi_trang": "Thời trang", "my_pham": "Mỹ phẩm", "dien_tu": "Điện tử & phụ kiện",
    "nha_cua": "Nhà cửa & đời sống", "me_be": "Mẹ & bé", "thuc_pham": "Thực phẩm",
}

# base: gia_sau_voucher_shop = giá × SL − voucher shop · don = mỗi đơn · theo_shop = tỉ lệ shop tự đặt
#       (affiliate) tính trên gia_sau_voucher_shop · voucher_dong_tai_tro = giá trị voucher đồng tài trợ
# Thứ tự dòng khi in "chi tiết thanh toán" của từng sàn:
LINE_ORDER = {
    "shopee": ["voucher_dong_tai_tro", "phi_co_dinh", "phi_xu_ly_giao_dich", "phi_thanh_toan",
               "voucher_xtra", "tiep_thi_lien_ket", "phi_ha_tang", "thue_khau_tru", "chi_phi_don_hoan"],
    "tiktok": ["hoa_hong_nen_tang", "phi_giao_dich", "phi_voucher_extra", "hoa_hong_lien_ket",
               "thue_khau_tru", "chi_phi_don_hoan"],
    "lazada": ["phi_co_dinh", "phi_thanh_toan", "phi_freeship_max", "tiep_thi_lien_ket",
               "thue_khau_tru", "chi_phi_don_hoan"],
}
SWITCH_PROGRAMS = {  # công tắc cần shop bật / có trong đơn
    "voucher_xtra", "phi_voucher_extra", "phi_freeship_max", "tiep_thi_lien_ket", "hoa_hong_lien_ket",
    "voucher_dong_tai_tro",
}

URL = {  # nguồn để người soát mở kiểm; chưa phải trang chính sách đã khớp từng con số
    "shopee_bao": "https://vccinews.vn/news/shopee-tiktok-shop-tang-manh-phi-san",
    "tiktok_bao": "https://vccinews.vn/news/tu-9-5-tiktok-shop-tiep-tuc-tang-bieu-phi",
    "lazada_mall": "https://sellercenter.lazada.vn/helpcenter/s/faq/knowledge?categoryId=1000028699&m_station=faq&questionId=1000149707",
    "lazada_terms": "https://sellercenter.lazada.vn/helpcenter/s/faq/knowledge?categoryId=1000028750&m_station=faq&questionId=1000159631",
    "nd117": "https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Nghi-dinh-117-2025-ND-CP",
}


def _r(platform, fee_key, ten, loai, base, rate="", cap="", per_order="", ap_dung="tat_ca",
       tu="2026-01-01", den="", nganh="*", ten_cu="", url="", doi_chieu="gia_dinh"):
    rid = f"{platform}_{fee_key}" + (f"_{nganh}" if nganh != "*" else "") + \
          (f"_{ap_dung}" if ap_dung != "tat_ca" else "") + f"_{tu}"
    return {"rule_id": rid, "platform": platform, "fee_key": fee_key, "ten_hien_thi": ten,
            "ten_cu": ten_cu, "loai": loai, "base": base, "rate": rate, "cap_vnd": cap,
            "per_order_vnd": per_order, "ap_dung": ap_dung, "hieu_luc_tu": tu, "hieu_luc_den": den,
            "nganh": nganh, "chunk_id": "", "nguon_url": url, "da_doi_chieu": doi_chieu}


def build_v0_rules() -> list[dict]:
    """Bảng phí TẠM. Tỉ lệ theo ngành đều (tự ước tính); mốc ngày lấy từ CONTEXT.md (báo chí)."""
    R = []
    # ---------- Shopee ----------
    co_dinh_sau = {"thoi_trang": 9.0, "my_pham": 9.0, "dien_tu": 7.0, "nha_cua": 8.5, "me_be": 8.0, "thuc_pham": 7.5}
    for cat, after in co_dinh_sau.items():
        for ap, add in (("shop_thuong", 0.0), ("mall", 3.0)):
            # 08/05/2026: giảm 1% phí cố định ở nhiều ngành (báo chí) → trước đó +1
            R.append(_r("shopee", "phi_co_dinh", "Phí cố định", "bat_buoc", "gia_sau_voucher_shop",
                        rate=after + 1 + add, ap_dung=ap, tu="2026-01-01", den="2026-05-07", nganh=cat,
                        url=URL["shopee_bao"]))
            R.append(_r("shopee", "phi_co_dinh", "Phí cố định", "bat_buoc", "gia_sau_voucher_shop",
                        rate=after + add, ap_dung=ap, tu="2026-05-08", nganh=cat, url=URL["shopee_bao"]))
    R.append(_r("shopee", "phi_thanh_toan", "Phí thanh toán", "bat_buoc", "gia_sau_voucher_shop",
                rate=4.91, tu="2026-01-01", den="2026-04-23", url=URL["shopee_bao"], doi_chieu="bao_chi"))
    # 24/04/2026 đổi tên "phí thanh toán" → "phí xử lý giao dịch"; 01/05 lên 6% shop thường, Mall từ 08/05
    R.append(_r("shopee", "phi_xu_ly_giao_dich", "Phí xử lý giao dịch", "bat_buoc", "gia_sau_voucher_shop",
                rate=4.91, tu="2026-04-24", den="2026-04-30", ten_cu="Phí thanh toán", url=URL["shopee_bao"],
                doi_chieu="bao_chi"))
    R.append(_r("shopee", "phi_xu_ly_giao_dich", "Phí xử lý giao dịch", "bat_buoc", "gia_sau_voucher_shop",
                rate=6.0, ap_dung="shop_thuong", tu="2026-05-01", ten_cu="Phí thanh toán", url=URL["shopee_bao"],
                doi_chieu="bao_chi"))
    R.append(_r("shopee", "phi_xu_ly_giao_dich", "Phí xử lý giao dịch", "bat_buoc", "gia_sau_voucher_shop",
                rate=4.91, ap_dung="mall", tu="2026-05-01", den="2026-05-07", ten_cu="Phí thanh toán",
                url=URL["shopee_bao"], doi_chieu="bao_chi"))
    R.append(_r("shopee", "phi_xu_ly_giao_dich", "Phí xử lý giao dịch", "bat_buoc", "gia_sau_voucher_shop",
                rate=6.0, ap_dung="mall", tu="2026-05-08", ten_cu="Phí thanh toán", url=URL["shopee_bao"],
                doi_chieu="bao_chi"))
    R.append(_r("shopee", "voucher_xtra", "Phí Voucher Xtra", "cong_tac", "gia_sau_voucher_shop",
                rate=4.0, cap=50_000, tu="2026-01-01", den="2026-05-22", url=URL["shopee_bao"]))
    R.append(_r("shopee", "voucher_xtra", "Phí Voucher Xtra", "cong_tac", "gia_sau_voucher_shop",
                rate=5.5, cap=50_000, tu="2026-05-23", url=URL["shopee_bao"], doi_chieu="bao_chi"))
    R.append(_r("shopee", "tiep_thi_lien_ket", "Phí tiếp thị liên kết", "cong_tac", "theo_shop",
                url=URL["shopee_bao"], doi_chieu="bao_chi"))
    R.append(_r("shopee", "voucher_dong_tai_tro", "Voucher đồng tài trợ (người bán chịu)", "cong_tac",
                "voucher_dong_tai_tro", rate=50.0, url=URL["shopee_bao"]))
    R.append(_r("shopee", "phi_ha_tang", "Phí hạ tầng", "bat_buoc", "don", per_order=3_000,
                tu="2025-07-01", url=URL["shopee_bao"], doi_chieu="bao_chi"))
    # ---------- TikTok Shop ----------
    R.append(_r("tiktok", "phi_giao_dich", "Phí giao dịch", "bat_buoc", "gia_sau_voucher_shop",
                rate=5.0, tu="2026-01-01", den="2026-05-08", url=URL["tiktok_bao"]))
    R.append(_r("tiktok", "phi_giao_dich", "Phí giao dịch", "bat_buoc", "gia_sau_voucher_shop",
                rate=6.0, tu="2026-05-09", url=URL["tiktok_bao"], doi_chieu="bao_chi"))
    hh_truoc = {"thoi_trang": 7.0, "my_pham": 7.0, "dien_tu": 5.0, "nha_cua": 6.5, "me_be": 6.0, "thuc_pham": 5.5}
    hh_sau = {"thoi_trang": 10.0, "my_pham": 10.0, "dien_tu": 7.5, "nha_cua": 9.0, "me_be": 8.5, "thuc_pham": 8.0}
    for cat in CATEGORIES:
        # biểu hoa hồng mới 03/07 (shop thường), Mall 03/08 — mốc từ báo chí, tỉ lệ tự ước tính
        R.append(_r("tiktok", "hoa_hong_nen_tang", "Phí hoa hồng nền tảng", "bat_buoc", "gia_sau_voucher_shop",
                    rate=hh_truoc[cat], ap_dung="shop_thuong", tu="2026-01-01", den="2026-07-02", nganh=cat,
                    url=URL["tiktok_bao"]))
        R.append(_r("tiktok", "hoa_hong_nen_tang", "Phí hoa hồng nền tảng", "bat_buoc", "gia_sau_voucher_shop",
                    rate=hh_sau[cat], ap_dung="shop_thuong", tu="2026-07-03", nganh=cat, url=URL["tiktok_bao"]))
        R.append(_r("tiktok", "hoa_hong_nen_tang", "Phí hoa hồng nền tảng", "bat_buoc", "gia_sau_voucher_shop",
                    rate=hh_truoc[cat] + 2, ap_dung="mall", tu="2026-01-01", den="2026-08-02", nganh=cat,
                    url=URL["tiktok_bao"]))
        R.append(_r("tiktok", "hoa_hong_nen_tang", "Phí hoa hồng nền tảng", "bat_buoc", "gia_sau_voucher_shop",
                    rate=hh_sau[cat] + 2, ap_dung="mall", tu="2026-08-03", nganh=cat, url=URL["tiktok_bao"]))
    R.append(_r("tiktok", "phi_voucher_extra", "Phí Voucher Extra", "cong_tac", "gia_sau_voucher_shop",
                rate=4.0, cap=50_000, tu="2026-01-01", den="2026-05-08", url=URL["tiktok_bao"]))
    R.append(_r("tiktok", "phi_voucher_extra", "Phí Voucher Extra", "cong_tac", "gia_sau_voucher_shop",
                rate=5.0, cap=50_000, tu="2026-05-09", url=URL["tiktok_bao"]))
    R.append(_r("tiktok", "hoa_hong_lien_ket", "Hoa hồng nhà sáng tạo (liên kết)", "cong_tac", "theo_shop",
                url=URL["tiktok_bao"], doi_chieu="bao_chi"))
    # ---------- Lazada ----------
    lz = {"thoi_trang": 8.0, "my_pham": 8.0, "dien_tu": 6.0, "nha_cua": 7.5, "me_be": 7.0, "thuc_pham": 6.5}
    for cat, v in lz.items():
        R.append(_r("lazada", "phi_co_dinh", "Phí cố định", "bat_buoc", "gia_sau_voucher_shop", rate=v,
                    ap_dung="shop_thuong", nganh=cat, url=URL["lazada_terms"]))
        R.append(_r("lazada", "phi_co_dinh", "Phí cố định", "bat_buoc", "gia_sau_voucher_shop", rate=v + 2,
                    ap_dung="mall", den="2026-06-03", nganh=cat, url=URL["lazada_mall"]))
        # Trang "phí cố định theo ngành LazMall" ghi hiệu lực 04/06/2026 (manifest đã crawl); tỉ lệ tự ước tính
        R.append(_r("lazada", "phi_co_dinh", "Phí cố định", "bat_buoc", "gia_sau_voucher_shop", rate=v + 3,
                    ap_dung="mall", tu="2026-06-04", nganh=cat, url=URL["lazada_mall"]))
    R.append(_r("lazada", "phi_thanh_toan", "Phí thanh toán", "bat_buoc", "gia_sau_voucher_shop", rate=4.0,
                url=URL["lazada_terms"]))
    R.append(_r("lazada", "phi_freeship_max", "Phí dịch vụ Freeship Max", "cong_tac", "gia_sau_voucher_shop",
                rate=5.0, cap=40_000, url=URL["lazada_terms"]))
    R.append(_r("lazada", "tiep_thi_lien_ket", "Hoa hồng Lazada Affiliate", "cong_tac", "theo_shop",
                url=URL["lazada_terms"]))
    # ---------- chung 3 sàn ----------
    for p in PLATFORMS:
        # NĐ 117/2025 từ 01/07/2025: sàn khấu trừ thay hộ kinh doanh (1% GTGT + 0,5% TNCN — cần tra Điều 5)
        R.append(_r(p, "thue_khau_tru", "Thuế khấu trừ (GTGT + TNCN)", "bat_buoc", "gia_sau_voucher_shop",
                    rate=1.5, tu="2025-07-01", url=URL["nd117"]))
        R.append(_r(p, "chi_phi_don_hoan", "Phí vận chuyển trả hàng", "bat_buoc", "don", per_order=20_000))
    return R


def write_v0(path: Path = FEE_RULES_V0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(build_v0_rules())
    return path


def load_rules(path: str | Path | None = None) -> tuple[list[dict], Path]:
    if path is None:
        path = FEE_RULES_OFFICIAL if FEE_RULES_OFFICIAL.exists() else FEE_RULES_V0
    path = Path(path)
    if not path.exists():
        write_v0(path)
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["rate"] = float(r["rate"]) if r.get("rate") not in ("", None) else None
        r["cap_vnd"] = int(float(r["cap_vnd"])) if r.get("cap_vnd") not in ("", None) else None
        r["per_order_vnd"] = int(float(r["per_order_vnd"])) if r.get("per_order_vnd") not in ("", None) else None
        r["nganh"] = r.get("nganh") or "*"
    return rows, path


def find_rule(rules: list[dict], platform: str, fee_key: str, date: str, shop_type: str,
              nganh: str) -> dict | None:
    """Luật đang hiệu lực tại `date` (YYYY-MM-DD). Ưu tiên khớp ngành và loại shop cụ thể."""
    best, score = None, -1
    for r in rules:
        if r["platform"] != platform or r["fee_key"] != fee_key:
            continue
        if not (r["hieu_luc_tu"] <= date and (not r["hieu_luc_den"] or date <= r["hieu_luc_den"])):
            continue
        if r["ap_dung"] not in (shop_type, "tat_ca") or r["nganh"] not in (nganh, "*"):
            continue
        s = (r["ap_dung"] == shop_type) + (r["nganh"] == nganh)
        if s > score:
            best, score = r, s
    return best


def amount_for(rule: dict, base_amount: int, qty: int = 1, shop_rate: float | None = None) -> int:
    """Số tiền đúng luật (dương). base_amount đã là căn cứ phù hợp với rule['base']."""
    if rule["base"] == "don":
        return int(rule["per_order_vnd"] or 0)
    rate = shop_rate if rule["base"] == "theo_shop" else rule["rate"]
    if not rate:
        return 0
    amt = round(base_amount * rate / 100)
    if rule["cap_vnd"]:
        amt = min(amt, rule["cap_vnd"] * qty)
    return int(amt)


def compute_lines(rules: list[dict], o: dict) -> list[dict]:
    """Các dòng phí ĐÚNG LUẬT của một đơn.

    o cần: platform, order_date, shop_type, nganh, qty, price, voucher_shop, seller_type,
           status ('hoan_tat' | 'hoan_hang'), programs (set fee_key công tắc có trong đơn),
           affiliate_rate (%), cofund_voucher (VND).
    """
    p, d = o["platform"], o["order_date"]
    out = []
    if o.get("status") == "hoan_hang":
        r = find_rule(rules, p, "chi_phi_don_hoan", d, o["shop_type"], o["nganh"])
        if r:
            out.append(_line(r, -amount_for(r, 0)))
        return out
    base = o["price"] * o["qty"] - o.get("voucher_shop", 0)
    for key in LINE_ORDER[p]:
        if key == "chi_phi_don_hoan":
            continue
        if key in SWITCH_PROGRAMS and key not in o.get("programs", set()):
            continue
        if key == "thue_khau_tru" and o.get("seller_type", "ho_kinh_doanh") != "ho_kinh_doanh":
            continue
        r = find_rule(rules, p, key, d, o["shop_type"], o["nganh"])
        if r is None:
            continue
        if r["base"] == "voucher_dong_tai_tro":
            amt = round(o.get("cofund_voucher", 0) * (r["rate"] or 0) / 100)
        else:
            amt = amount_for(r, base, o["qty"], o.get("affiliate_rate"))
        if amt:
            out.append(_line(r, -amt))
    return out


def _line(r: dict, amount: int) -> dict:
    return {"fee_key": r["fee_key"], "ten_dong": r["ten_hien_thi"], "amount_vnd": amount,
            "rule_id": r["rule_id"], "loai": r["loai"]}


def _check() -> None:
    rules, path = load_rules()
    o = {"platform": "shopee", "order_date": "2026-11-12", "shop_type": "shop_thuong", "nganh": "thoi_trang",
         "qty": 1, "price": 199_000, "voucher_shop": 10_000, "seller_type": "ho_kinh_doanh", "status": "hoan_tat",
         "programs": {"voucher_xtra", "tiep_thi_lien_ket"}, "affiliate_rate": 10.0}
    lines = compute_lines(rules, o) + [{"ten_dong": "Phí dịch vụ khác", "amount_vnd": -2_000, "rule_id": ""}]
    payout = 199_000 - 10_000 + sum(x["amount_vnd"] for x in lines)
    for x in lines:
        print(f"  {x['ten_dong']:40s} {x['amount_vnd']:>10,}  {x['rule_id']}")
    print(f"Bảng phí: {path}\nTiền về {payout:,} (cần 123,520) · lãi {payout - 95_000:,} (cần 28,520)")
    assert payout == 123_520, "đơn mẫu H4 lệch"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-v0", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.write_v0:
        print("Đã ghi", write_v0())
    if a.check or not a.write_v0:
        _check()
