#!/usr/bin/env python3
"""Import file export đơn hàng của sàn (xlsx) → dữ liệu chuẩn + phân tích tháng.

Luồng demo: chủ shop tải file export tháng từ Shopee / TikTok Shop / Lazada (+ file giá vốn tự điền)
→ hệ thống chuẩn hoá về cùng schema với data/synthetic/orders.csv + order_lines.csv
→ phân tích bằng CODE (mọi con số), agent chỉ đọc kết quả để giải thích và chọn việc cần làm.

  python data/import_export.py data/demo_import/*_don_hang_*.xlsx --cogs data/demo_import/gia_von_mau.xlsx
  python data/import_export.py file.xlsx --platform shopee --out data/imported/thang-11

Tự nhận sàn theo tên cột (EXPORT_FORMATS trong make_demo_import.py). File export thật khác cột thì
thêm / sửa định dạng ở đó. Cần openpyxl.

Đầu ra <out>/: orders.csv · order_lines.csv · phan_tich.json (in tóm tắt ra màn hình).
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError:
    raise SystemExit("Thiếu openpyxl: python -m pip install openpyxl")

import fee_engine as fe
from make_demo_import import EXPORT_FORMATS

CAT_BY_NAME = {v.lower(): k for k, v in fe.CATEGORIES.items()}
SWITCH_KEYS = fe.SWITCH_PROGRAMS
AFFILIATE_KEYS = {"tiep_thi_lien_ket", "hoa_hong_lien_ket"}


class ImportFileError(ValueError):
    """File export / giá vốn không đọc được (sai định dạng, không nhận ra sàn). API trả 400, CLI in lỗi rồi thoát."""


def num(v) -> int:
    if v in (None, ""):
        return 0
    if isinstance(v, (int, float)):
        return int(round(v))
    s = str(v).replace("đ", "").replace("₫", "").replace(" ", "").replace(".", "").replace(",", "")
    return int(s) if s.lstrip("-").isdigit() else 0


def status_of(label: str) -> str:
    t = (label or "").lower()
    if "hủy" in t or "huỷ" in t:
        return "huy"
    if "trả" in t or "hoàn tiền" in t:
        return "hoan_hang"
    return "hoan_tat"


def detect_platform(headers: list[str]) -> str | None:
    hs = set(h for h in headers if h)
    score = {p: len(hs & {h for h, _ in fmt}) / len(fmt) for p, fmt in EXPORT_FORMATS.items()}
    p = max(score, key=score.get)
    return p if score[p] >= 0.6 else None


def read_cogs(path: Path | None):
    cogs, cat, shop = {}, {}, {}
    if not path:
        return cogs, cat, shop
    wb = load_workbook(path, read_only=True, data_only=True)
    if "Giá vốn" in wb.sheetnames:
        rows = list(wb["Giá vốn"].iter_rows(values_only=True))
        for r in rows[1:]:
            if not r or not r[0]:
                continue
            sku = str(r[0]).strip()
            if r[3] not in (None, ""):
                cogs[sku] = num(r[3])
            if r[2]:
                cat[sku] = CAT_BY_NAME.get(str(r[2]).strip().lower(), "")
    if "Thông tin shop" in wb.sheetnames:
        name2p = {v.lower(): k for k, v in fe.PLATFORM_NAME.items()}
        for r in list(wb["Thông tin shop"].iter_rows(values_only=True))[1:]:
            if r and r[0]:
                p = name2p.get(str(r[0]).strip().lower())
                if p:
                    shop[p] = {"shop_type": "mall" if "mall" in str(r[1]).lower() else "shop_thuong",
                               "seller_type": "cong_ty" if "công ty" in str(r[2]).lower() else "ho_kinh_doanh"}
    return cogs, cat, shop


def read_export(path: Path, platform: str | None):
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb["Đơn hàng"] if "Đơn hàng" in wb.sheetnames else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    platform = platform or detect_platform(headers)
    if not platform:
        raise ImportFileError(f"{path.name}: không nhận ra sàn từ tên cột — thêm --platform hoặc sửa EXPORT_FORMATS")
    field_of = {h: f for h, f in EXPORT_FORMATS[platform]}
    idx = {field_of[h]: i for i, h in enumerate(headers) if h in field_of}
    unknown = [h for h in headers if h and h not in field_of]
    orders = []
    for r in rows[1:]:
        if not r or r[idx["order_id"]] in (None, ""):
            continue
        g = lambda f: r[idx[f]] if f in idx else None
        fees = {f[4:]: num(g(f)) for f in idx if f.startswith("fee:") and num(g(f))}
        orders.append({"order_id": str(g("order_id")), "platform": platform, "sku": str(g("sku") or ""),
                       "ten_sp": g("ten_sp") or "", "order_date": str(g("order_date"))[:10],
                       "status": status_of(str(g("status"))), "qty": num(g("qty")) or 1,
                       "gia_ban": num(g("gia_ban")), "voucher_shop": num(g("voucher_shop")), "fees": fees,
                       "phi_khac": num(g("phi_khac")), "payout": num(g("payout"))})
    ads = []
    if "Quảng cáo" in wb.sheetnames:
        ar = list(wb["Quảng cáo"].iter_rows(values_only=True))
        h = [str(x) for x in ar[0]]
        for r in ar[1:]:
            if r and r[0]:
                d = dict(zip(h, r))
                ads.append({"platform": platform, "chien_dich": d.get("Tên chiến dịch"), "sku": d.get("SKU"),
                            "chi_phi": num(d.get("Chi phí (đ)")), "gmv": num(d.get("Doanh thu GMV (đ)"))})
    return platform, orders, ads, unknown


def analyse(orders, ads, rules, cogs, cat, shop):
    name_of = {(p, k): None for p in fe.PLATFORMS for k in []}
    rule_name = {(r["platform"], r["fee_key"]): r["ten_hien_thi"] for r in rules}
    plat = defaultdict(lambda: defaultdict(int))
    fee_tot = defaultdict(lambda: defaultdict(int))
    sku = defaultdict(lambda: {"don": 0, "hoan_tat": 0, "hoan_hang": 0, "huy": 0, "doanh_thu": 0, "tien_ve": 0,
                               "gia_von": 0, "thieu_gia_von": False, "cong_tac": defaultdict(int), "aff_rates": []})
    lech, la = [], []
    for o in orders:
        p, k = o["platform"], (o["platform"], o["sku"])
        P, S = plat[p], sku[k]
        P["don"] += 1; P[o["status"]] += 1; S["don"] += 1; S[o["status"]] += 1
        base = o["gia_ban"] * o["qty"] - o["voucher_shop"]
        if o["status"] == "hoan_tat":
            P["doanh_thu"] += base; S["doanh_thu"] += base
            if o["sku"] in cogs:
                c = cogs[o["sku"]] * o["qty"]; P["gia_von"] += c; S["gia_von"] += c
            else:
                S["thieu_gia_von"] = True; P["don_thieu_gia_von"] += 1
        P["tien_ve"] += o["payout"]; S["tien_ve"] += o["payout"]
        for fk, v in o["fees"].items():
            fee_tot[p][fk] += v
            if fk in SWITCH_KEYS:
                S["cong_tac"][rule_name.get((p, fk), fk)] += v
        if o["phi_khac"]:
            fee_tot[p]["phi_khac"] += o["phi_khac"]
            la.append({"order_id": o["order_id"], "platform": p, "sku": o["sku"], "so_tien": o["phi_khac"]})
        # kiểm từng khoản với bảng phí (trừ affiliate: tỉ lệ do shop đặt → chỉ suy ra tỉ lệ)
        if o["status"] == "huy":
            continue
        info = shop.get(p, {"shop_type": "shop_thuong", "seller_type": "ho_kinh_doanh"})
        q = {"platform": p, "order_date": o["order_date"], "shop_type": info["shop_type"],
             "seller_type": info["seller_type"], "nganh": cat.get(o["sku"], ""), "qty": o["qty"],
             "price": o["gia_ban"], "voucher_shop": o["voucher_shop"], "status": o["status"],
             "programs": {fk for fk in o["fees"] if fk in SWITCH_KEYS}, "affiliate_rate": None}
        expected = {x["fee_key"]: -x["amount_vnd"] for x in fe.compute_lines(rules, q)}
        for fk, v in o["fees"].items():
            if fk in AFFILIATE_KEYS:
                if base:
                    S["aff_rates"].append(round(v / base * 100, 1))
                continue
            e = expected.get(fk)
            if e is None:
                lech.append({"order_id": o["order_id"], "platform": p, "sku": o["sku"], "khoan": rule_name.get((p, fk), fk),
                             "thuc_tru": v, "dung_luat": None, "ly_do": "không tìm thấy luật (thiếu ngành / loại shop?)"})
            elif abs(v - e) > 1:
                lech.append({"order_id": o["order_id"], "platform": p, "sku": o["sku"], "khoan": rule_name.get((p, fk), fk),
                             "thuc_tru": v, "dung_luat": e, "chenh": v - e})
    platforms = {}
    for p, P in plat.items():
        lai = P["tien_ve"] - P["gia_von"]
        platforms[p] = {"don": P["don"], "hoan_tat": P["hoan_tat"], "huy": P["huy"], "hoan_hang": P["hoan_hang"],
                        "doanh_thu": P["doanh_thu"], "tong_phi": sum(fee_tot[p].values()),
                        "phi_tren_doanh_thu": round(sum(fee_tot[p].values()) / P["doanh_thu"], 3) if P["doanh_thu"] else None,
                        "tien_ve": P["tien_ve"], "gia_von": P["gia_von"], "lai_truoc_qc": lai,
                        "don_thieu_gia_von": P["don_thieu_gia_von"],
                        "phi_theo_khoan": {rule_name.get((p, k), k): v for k, v in
                                           sorted(fee_tot[p].items(), key=lambda kv: -kv[1])}}
    skus = []
    for (p, s), S in sorted(sku.items()):
        lai = None if S["thieu_gia_von"] else S["tien_ve"] - S["gia_von"]
        top = max(S["cong_tac"], key=S["cong_tac"].get) if S["cong_tac"] else None
        skus.append({"platform": p, "sku": s, "don": S["don"], "hoan_tat": S["hoan_tat"], "hoan_hang": S["hoan_hang"],
                     "ti_le_hoan": round(S["hoan_hang"] / S["don"], 3) if S["don"] else 0,
                     "doanh_thu": S["doanh_thu"], "tien_ve": S["tien_ve"], "lai_truoc_qc": lai,
                     "lai_moi_don": round(lai / S["hoan_tat"]) if lai is not None and S["hoan_tat"] else None,
                     "cong_tac_lon_nhat": top, "cong_tac_vnd": S["cong_tac"][top] if top else 0,
                     "ti_le_an_lai": round(S["cong_tac"][top] / lai, 3) if top and lai and lai > 0 else None,
                     "ti_le_affiliate_suy_ra": sorted(set(S["aff_rates"])) or None,
                     "thieu_gia_von": S["thieu_gia_von"]})
    camp = defaultdict(lambda: {"chi_phi": 0, "gmv": 0})
    for a in ads:
        c = camp[(a["platform"], a["chien_dich"], a["sku"])]
        c["chi_phi"] += a["chi_phi"]; c["gmv"] += a["gmv"]
    ad_rows = []
    for (p, name, s), c in camp.items():
        row = next((x for x in skus if x["platform"] == p and x["sku"] == s), None)
        m = row["lai_truoc_qc"] / row["doanh_thu"] if row and row["lai_truoc_qc"] is not None and row["doanh_thu"] else None
        roas = c["gmv"] / c["chi_phi"] if c["chi_phi"] else None
        be = 1 / m if m and m > 0 else None
        ad_rows.append({"platform": p, "chien_dich": name, "sku": s, "chi_phi": c["chi_phi"], "gmv": c["gmv"],
                        "roas": round(roas, 2) if roas else None, "roas_hoa_von": round(be, 2) if be else None,
                        "ket_luan": None if not be or not roas else ("lỗ" if roas < be else "lãi"),
                        "lai_sau_qc": (row["lai_truoc_qc"] - c["chi_phi"]) if row and row["lai_truoc_qc"] is not None else None})
    return {"theo_san": platforms, "theo_sku_san": skus, "dong_lech_luat": lech, "phi_khac_khong_khop": la,
            "quang_cao": ad_rows}


def run_import(files, cogs=None, platform=None, fee_rules=None, out=None) -> dict:
    """Đọc các file export (xlsx) + file giá vốn → ghi <out>/{orders.csv, order_lines.csv, phan_tich.json}.
    Dùng chung cho dòng lệnh (main) và API POST /import (codebase/app.py, TH-11).
    → {"phan_tich": dict như phan_tich.json, "files": [{"file", "platform", "orders", "unknown_columns"}],
       "out_dir": str, "bang_phi": tên file bảng phí}. Lỗi file → ImportFileError."""
    rules, rules_path = fe.load_rules(fee_rules)
    try:
        cogs_, cat, shop = read_cogs(Path(cogs) if cogs else None)
    except ImportFileError:
        raise
    except Exception as e:  # file giá vốn hỏng / không phải xlsx
        raise ImportFileError(f"file giá vốn không đọc được: {type(e).__name__}: {e}")
    orders, ads, info = [], [], []
    for f in files:
        try:
            p, os_, ad, unknown = read_export(Path(f), platform)
        except ImportFileError:
            raise
        except Exception as e:
            raise ImportFileError(f"{Path(f).name}: không đọc được file export ({type(e).__name__}: {e})")
        info.append({"file": Path(f).name, "platform": p, "orders": len(os_), "unknown_columns": unknown})
        orders += os_; ads += ad
    out = Path(out or fe.DATA / "imported" / "demo"); out.mkdir(parents=True, exist_ok=True)
    with (out / "orders.csv").open("w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo)
        w.writerow(["order_id", "platform", "sku", "ten_sp", "nganh", "order_date", "status", "qty", "gia_ban",
                    "voucher_shop", "payout", "gia_von"])
        for o in orders:
            w.writerow([o["order_id"], o["platform"], o["sku"], o["ten_sp"], cat.get(o["sku"], ""), o["order_date"],
                        o["status"], o["qty"], o["gia_ban"], o["voucher_shop"], o["payout"],
                        cogs_[o["sku"]] * o["qty"] if o["sku"] in cogs_ else ""])
    names = {(r["platform"], r["fee_key"]): r["ten_hien_thi"] for r in rules}
    with (out / "order_lines.csv").open("w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo)
        w.writerow(["order_id", "line_no", "ten_dong", "amount_vnd"])
        for o in orders:
            items = [(names.get((o["platform"], k), k), -v) for k, v in o["fees"].items()]
            if o["phi_khac"]:
                items.append(("Phí khác", -o["phi_khac"]))
            for i, (n, v) in enumerate(items, 1):
                w.writerow([o["order_id"], i, n, v])
    res = analyse(orders, ads, rules, cogs_, cat, shop)
    res["bang_phi"] = str(rules_path.name)
    (out / "phan_tich.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"phan_tich": res, "files": info, "out_dir": str(out), "bang_phi": rules_path.name}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--cogs", default=None, help="file giá vốn (xlsx, sheet 'Giá vốn' + 'Thông tin shop')")
    ap.add_argument("--platform", default=None, choices=fe.PLATFORMS)
    ap.add_argument("--fee-rules", default=None)
    ap.add_argument("--out", default=str(fe.DATA / "imported" / "demo"))
    a = ap.parse_args()
    try:
        r = run_import(a.files, a.cogs, a.platform, a.fee_rules, a.out)
    except ImportFileError as e:
        raise SystemExit(str(e))
    for x in r["files"]:
        print(f"Đọc {x['file']}: {fe.PLATFORM_NAME[x['platform']]}, {x['orders']} đơn"
              + (f" · cột lạ bỏ qua: {x['unknown_columns']}" if x["unknown_columns"] else ""))
    res, out, rules_path = r["phan_tich"], Path(r["out_dir"]), Path(r["bang_phi"])

    vn = lambda x: "—" if x is None else f"{x:,}".replace(",", ".")
    print(f"\nBảng phí: {rules_path.name} · ghi {out.relative_to(fe.DATA.parent)}/ (orders.csv, order_lines.csv, phan_tich.json)\n")
    print(f"{'Sàn':12s} {'Đơn':>5s} {'Doanh thu':>14s} {'Phí':>13s} {'%':>6s} {'Tiền về':>14s} {'Lãi trước QC':>14s}")
    for p, r in res["theo_san"].items():
        print(f"{fe.PLATFORM_NAME[p]:12s} {r['don']:5d} {vn(r['doanh_thu']):>14s} {vn(r['tong_phi']):>13s} "
              f"{(r['phi_tren_doanh_thu'] or 0) * 100:5.1f}% {vn(r['tien_ve']):>14s} {vn(r['lai_truoc_qc']):>14s}")
    print("\nCông tắc ăn lãi nhiều nhất (≥ 30% lãi):")
    for s in sorted([s for s in res["theo_sku_san"] if s["ti_le_an_lai"] and s["ti_le_an_lai"] >= 0.3],
                    key=lambda s: -s["ti_le_an_lai"]):
        print(f"  {fe.PLATFORM_NAME[s['platform']]:12s} {s['sku']:8s} {s['cong_tac_lon_nhat']:34s} "
              f"{s['ti_le_an_lai'] * 100:5.1f}% lãi · lãi/đơn {vn(s['lai_moi_don'])}")
    print(f"\nDòng lệch luật: {len(res['dong_lech_luat'])} · 'Phí khác' không khớp luật: {len(res['phi_khac_khong_khop'])}")
    for x in res["dong_lech_luat"][:8]:
        print(f"  {x['order_id']} {x['khoan']}: trừ {vn(x['thuc_tru'])}, đúng luật {vn(x['dung_luat'])}")
    hi = [s for s in res["theo_sku_san"] if s["ti_le_hoan"] >= 0.1]
    if hi:
        print("Tỉ lệ trả hàng ≥ 10%:", ", ".join(f"{fe.PLATFORM_NAME[s['platform']]} {s['sku']} {s['ti_le_hoan']:.0%}" for s in hi))
    for r in res["quang_cao"]:
        print(f"Quảng cáo {r['chien_dich']} ({fe.PLATFORM_NAME[r['platform']]}): ROAS {r['roas']} · hoà vốn "
              f"{r['roas_hoa_von']} → {r['ket_luan']} · lãi sau QC {vn(r['lai_sau_qc'])}")
    miss = [s["sku"] for s in res["theo_sku_san"] if s["thieu_gia_von"]]
    if miss:
        print("Thiếu giá vốn (cần hỏi chủ shop):", ", ".join(sorted(set(miss))))


if __name__ == "__main__":
    main()
