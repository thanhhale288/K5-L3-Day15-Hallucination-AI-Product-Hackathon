#!/usr/bin/env python3
"""Sinh data GIẢ LẬP (synthetic) cho Track D — "shop bán nhiều mà lãi ít".

Vì sao không dùng thẳng 07_Ecommerce_Seller_Store.xlsx:
  - 498 shop / 500 dòng → không có chuỗi tháng cho từng shop.
  - Không có giá vốn, phí ship shop chịu, chi phí hàng hoàn; Net_Margin_% trống.
  - Phí sàn chỉ 1–6% doanh thu, thấp xa so với mức báo chí đưa tin năm 2025.
  - Các cột gần như không liên quan đến nhau (không có "nguyên nhân" nào để chẩn đoán).

Script này sinh data có:
  - N shop × M tháng (mặc định 150 × 12, từ 2025-01), có mùa vụ (Tết, 9.9–12.12).
  - Phễu đơn: đặt → huỷ → giao thất bại (bom COD) → hoàn/trả → hoàn tất.
  - P&L đầy đủ: phí sàn theo sàn × ngành × thời điểm, voucher shop chịu, quảng cáo
    (ROAS giảm dần khi đốt nhiều), affiliate (TikTok), giá vốn, ship, đóng gói,
    hàng hoàn, thuế khấu trừ, chi phí cố định → lãi ròng.
  - Mỗi shop có một "kiểu rò" ẩn (archetype) → biết trước nguyên nhân đúng để chấm.
    Nhãn nằm RIÊNG ở labels.csv; công cụ của agent KHÔNG được đọc file này.

DATA NÀY LÀ GIẢ LẬP. Không phải bằng chứng pain (rubric R1). Mọi tỉ lệ ở khối
GIẢ ĐỊNH bên dưới là ước lượng của nhóm từ tin báo chí 2025, cần đối chiếu trang
chính sách chính thức của từng sàn trước khi trích lên slide.

Chỉ dùng thư viện chuẩn Python 3.10+.

Cách chạy (từ gốc repo):
  python data/generate_synthetic.py                       # → data/synthetic/*.csv
  python data/generate_synthetic.py --stores 200 --seed 7
  python data/generate_synthetic.py --dirty               # thêm store_months_dirty.csv (lỗi cài sẵn cho câu khó)
  python data/generate_synthetic.py --paste D017 2025-11  # in đoạn chủ shop sẽ dán vào bản chạy thử
  python data/generate_synthetic.py --paste D017 2025-11 --no-cogs
"""
from __future__ import annotations

import argparse
import csv
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

# ════════════════════════════════════════════════════════════════════════
# GIẢ ĐỊNH — sửa ở đây. "(tự ước tính)" = nhóm tự đặt, chưa có nguồn chính thức.
# ════════════════════════════════════════════════════════════════════════

# Tỉ lệ shop theo sàn (tự ước tính, gần thị phần GMV báo cáo Metric 2025 — cần kiểm).
PLATFORM_SHARE = {"Shopee": 0.55, "TikTok Shop": 0.38, "Lazada": 0.05, "Tiki": 0.02}

# Ngành: giá trị đơn trung bình (VND), giá vốn % giá bán, tỉ lệ hoàn sau giao,
# tỉ trọng shop. Tất cả (tự ước tính).
CATEGORIES = {
    #              aov      cogs  return  share
    "Fashion":     (185_000, 0.42, 0.075, 0.24),
    "Beauty":      (240_000, 0.40, 0.030, 0.16),
    "Electronics": (340_000, 0.68, 0.050, 0.12),
    "Home":        (210_000, 0.52, 0.045, 0.14),
    "Mom_Baby":    (290_000, 0.58, 0.030, 0.10),
    "Food":        (150_000, 0.62, 0.020, 0.10),
    "Health":      (270_000, 0.45, 0.030, 0.08),
    "Books":       (120_000, 0.66, 0.020, 0.06),
}

# Phí cố định (hoa hồng) % theo sàn × ngành, mức áp dụng SAU thay đổi.
# Shopee: báo đưa tin tổng phí ~9% → ~14,5% từ 2025-04 → trước 04/2025 trừ SHOPEE_PRE_APR_CUT.
COMMISSION_PCT = {
    "Shopee":      {"Fashion": 10.0, "Beauty": 10.0, "Electronics": 8.0, "Home": 9.5,
                    "Mom_Baby": 9.0, "Food": 9.0, "Health": 10.0, "Books": 8.0},
    "TikTok Shop": {"Fashion": 9.0, "Beauty": 9.0, "Electronics": 7.0, "Home": 8.5,
                    "Mom_Baby": 8.0, "Food": 8.0, "Health": 9.0, "Books": 7.0},
    "Lazada":      {"Fashion": 9.0, "Beauty": 9.0, "Electronics": 6.5, "Home": 8.0,
                    "Mom_Baby": 8.0, "Food": 7.5, "Health": 9.0, "Books": 7.0},
    "Tiki":        {"Fashion": 13.0, "Beauty": 12.0, "Electronics": 9.0, "Home": 11.0,
                    "Mom_Baby": 10.0, "Food": 10.0, "Health": 12.0, "Books": 14.0},
}
SHOPEE_PRE_APR_CUT = 4.5          # điểm % (tự ước tính từ "~9% → ~14,5%")
SHOPEE_FEE_CHANGE = "2025-04"
PAYMENT_PCT = {"Shopee": 5.0, "TikTok Shop": 5.0, "Lazada": 5.0, "Tiki": 5.0}  # (tự ước tính ~5%)

# Gói dịch vụ tự chọn (% doanh thu) — (tự ước tính).
SERVICE_PROGRAMS = {
    "Shopee":      {"freeship_xtra": 6.0, "voucher_xtra": 3.0},
    "TikTok Shop": {"freeship_program": 4.0},
    "Lazada":      {"freeship_max": 5.0},
    "Tiki":        {},
}
# Phí hạ tầng / đơn (báo đưa tin Shopee 3.000đ/đơn từ 2025-07).
PER_ORDER_FEE = {"Shopee": (3_000, "2025-07")}

# Thuế hộ kinh doanh sàn khấu trừ thay (NĐ 117/2025, từ 2025-07): 1% GTGT + 0,5% TNCN.
HOUSEHOLD_TAX_PCT = 1.5
TAX_WITHHOLD_FROM = "2025-07"
HOUSEHOLD_SHARE = 0.85            # (tự ước tính) phần còn lại là công ty, không mô hình hoá thuế

# Hệ số mùa vụ số đơn theo tháng (tự ước tính: trước Tết cao, tháng Tết thấp, 9.9–12.12 cao).
SEASONALITY = {1: 1.25, 2: 0.70, 3: 0.95, 4: 0.95, 5: 0.95, 6: 1.00,
               7: 1.00, 8: 1.00, 9: 1.10, 10: 1.15, 11: 1.45, 12: 1.30}

# Quy mô shop: (tỉ trọng, số đơn/tháng min, max, chi phí cố định/tháng min, max) — (tự ước tính).
SIZE_TIERS = {
    "micro":  (0.45,   80,   400,          0,  4_000_000),
    "small":  (0.40,  400, 2_000,  8_000_000, 25_000_000),
    "medium": (0.15, 2_000, 8_000, 30_000_000, 90_000_000),
}

CANCEL_RATE = 0.04                # huỷ trước giao (tự ước tính)
FAILED_DELIVERY = {"Shopee": 0.03, "TikTok Shop": 0.05, "Lazada": 0.03, "Tiki": 0.02}  # bom COD
FAILED_DELIVERY_FEE = 20_000      # shop chịu ship chiều về / đơn giao thất bại (tự ước tính)
RETURN_SHIP_FEE = 25_000          # phí ship hoàn / đơn trả hàng (tự ước tính)
RETURN_SHIP_SHOP_PAYS = 0.5       # tỉ lệ đơn trả mà shop chịu phí ship (tự ước tính)
RETURN_GOODS_LOSS = 0.30          # phần hàng trả về không bán lại được (tự ước tính)
AFFILIATE_RATE = 0.12             # hoa hồng KOC trên doanh thu qua affiliate, TikTok (tự ước tính)

# Kiểu rò ẩn của shop → nguyên nhân đúng (nhãn chấm). Tỉ trọng (tự đặt).
ARCHETYPES = {
    "healthy":          (0.30, "khong_ro_ri"),
    "ads_burn":         (0.20, "quang_cao"),
    "voucher_heavy":    (0.12, "voucher"),
    "high_returns":     (0.12, "hoan_hang"),
    "thin_price":       (0.12, "gia_von"),
    "fee_stack":        (0.08, "phi_san"),
    "shipping_subsidy": (0.06, "phi_ship"),
}
COST_BUCKETS = ["quang_cao", "voucher", "phi_san", "hoan_hang", "phi_ship", "gia_von"]
MIN_EXCESS_PP = 3.0               # khoản lệch nhiều nhất < 3 điểm % so với nhóm → "khong_ro_ri"

# ════════════════════════════════════════════════════════════════════════


def weighted(rng: random.Random, table: dict) -> str:
    keys = list(table)
    w = [table[k] if isinstance(table[k], (int, float)) else table[k][0] for k in keys]
    return rng.choices(keys, weights=w, k=1)[0]


def month_list(start: str, n: int) -> list[str]:
    y, m = map(int, start.split("-"))
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def r1000(x: float) -> int:
    return int(round(x / 1000.0)) * 1000


def make_store(rng: random.Random, idx: int) -> dict:
    arch = weighted(rng, ARCHETYPES)
    platform = weighted(rng, PLATFORM_SHARE)
    category = weighted(rng, {k: v[3] for k, v in CATEGORIES.items()})
    if arch == "fee_stack" and rng.random() < 0.8:
        platform = "Shopee"                         # chồng gói dịch vụ chủ yếu ở Shopee
    if arch == "shipping_subsidy":
        category = rng.choice(["Food", "Books", "Fashion"])  # đơn giá thấp → ship ăn % lớn
    if arch == "high_returns" and rng.random() < 0.6:
        category = "Fashion"
    tier = weighted(rng, SIZE_TIERS)
    _, omin, omax, fmin, fmax = SIZE_TIERS[tier]
    aov0, cogs0, ret0, _ = CATEGORIES[category]

    progs_all = SERVICE_PROGRAMS[platform]
    if arch == "fee_stack":
        programs = list(progs_all)
    else:
        prob = 0.15 if arch == "healthy" else 0.35
        programs = [p for p in progs_all if rng.random() < prob]

    s = {
        "store_id": f"D{idx:03d}",
        "store_name": f"Shop D{idx:03d}",           # tên trung tính, không giống thương hiệu thật
        "platform": platform,
        "category": category,
        "size_tier": tier,
        "seller_type": "ho_kinh_doanh" if rng.random() < HOUSEHOLD_SHARE else "cong_ty",
        "service_programs": ";".join(programs),
        # tham số ẩn (không ghi ra stores.csv)
        "_arch": arch,
        "_orders0": rng.uniform(omin, omax),
        "_growth": rng.gauss(0.015, 0.025),
        "_aov": aov0 * rng.uniform(0.75, 1.30),
        "_cogs": min(0.92, max(0.20, cogs0 + rng.gauss(0, 0.04))),
        "_ret": ret0 * rng.uniform(0.8, 1.2),
        "_fail_mult": rng.uniform(0.8, 1.2),
        "_ad_pct": rng.uniform(4.0, 9.0),
        "_roas0": rng.uniform(8.0, 14.0),
        "_voucher_pct": rng.uniform(2.0, 5.0),
        "_ship_sub": rng.uniform(0, 6_000),
        "_pack": rng.uniform(3_000, 6_000),
        "_fixed": rng.uniform(fmin, fmax),
        "_aff_share": rng.uniform(0.10, 0.35) if platform == "TikTok Shop" else 0.0,
    }
    # Đẩy đúng một khoản lên cho shop có kiểu rò
    if arch == "healthy":
        s["_ad_pct"] = rng.uniform(3.0, 6.5)
        s["_voucher_pct"] = rng.uniform(1.5, 3.5)
        s["_cogs"] = max(0.20, s["_cogs"] - rng.uniform(0.02, 0.06))
    elif arch == "ads_burn":
        s["_ad_pct"] = rng.uniform(12.0, 20.0)
        s["_roas0"] = rng.uniform(5.0, 9.0)
    elif arch == "voucher_heavy":
        s["_voucher_pct"] = rng.uniform(8.0, 14.0)
    elif arch == "high_returns":
        s["_ret"] = ret0 * rng.uniform(3.5, 5.0)
        s["_fail_mult"] = rng.uniform(2.0, 3.0)
    elif arch == "thin_price":
        s["_cogs"] = min(0.92, s["_cogs"] + rng.uniform(0.08, 0.14))
    elif arch == "shipping_subsidy":
        s["_ship_sub"] = rng.uniform(9_000, 15_000)
    return s


def fee_rates(store: dict, month: str) -> tuple[float, float, float, int]:
    p, c = store["platform"], store["category"]
    commission = COMMISSION_PCT[p][c]
    if p == "Shopee" and month < SHOPEE_FEE_CHANGE:
        commission -= SHOPEE_PRE_APR_CUT
    service = sum(SERVICE_PROGRAMS[p][x] for x in store["service_programs"].split(";") if x)
    per_order = 0
    if p in PER_ORDER_FEE and month >= PER_ORDER_FEE[p][1]:
        per_order = PER_ORDER_FEE[p][0]
    return commission, PAYMENT_PCT[p], service, per_order


def simulate_month(rng: random.Random, s: dict, month: str, t: int) -> dict:
    mnum = int(month[5:])
    season = SEASONALITY[mnum]
    campaign = max(0.0, season - 1.0)               # cường độ campaign tháng sale lớn

    orders = s["_orders0"] * season * (1 + s["_growth"]) ** t * rng.lognormvariate(0, 0.12)
    placed = max(10, int(round(orders)))
    aov = s["_aov"] * (1 - 0.25 * campaign) * rng.uniform(0.96, 1.04)

    cancelled = round(placed * CANCEL_RATE * rng.uniform(0.6, 1.4))
    shipped = placed - cancelled
    fail_rate = FAILED_DELIVERY[s["platform"]] * s["_fail_mult"] * rng.uniform(0.7, 1.3)
    failed = round(shipped * min(0.25, fail_rate))
    delivered = shipped - failed
    ret_rate = min(0.45, s["_ret"] * rng.uniform(0.75, 1.25))
    returned = round(delivered * ret_rate)
    completed = delivered - returned

    gmv = placed * aov
    revenue = completed * aov                       # doanh thu đơn hoàn tất (trước voucher)
    voucher = revenue * s["_voucher_pct"] / 100 * (1 + 1.5 * campaign) * rng.uniform(0.85, 1.15)
    net_sales = revenue - voucher

    commission_pct, payment_pct, service_pct, per_order = fee_rates(s, month)
    commission = net_sales * commission_pct / 100
    payment = net_sales * payment_pct / 100
    service = net_sales * service_pct / 100
    per_order_fee = completed * per_order
    platform_fee = commission + payment + service + per_order_fee

    tax = 0.0
    if s["seller_type"] == "ho_kinh_doanh":
        tax = net_sales * HOUSEHOLD_TAX_PCT / 100
    tax_withheld = s["seller_type"] == "ho_kinh_doanh" and month >= TAX_WITHHOLD_FROM
    payout = net_sales - platform_fee - (tax if tax_withheld else 0)

    cogs = revenue * s["_cogs"]
    return_loss = returned * aov * s["_cogs"] * RETURN_GOODS_LOSS
    shipping_subsidy = completed * s["_ship_sub"] * (1 + 0.3 * campaign)
    return_shipping = failed * FAILED_DELIVERY_FEE + returned * RETURN_SHIP_FEE * RETURN_SHIP_SHOP_PAYS
    packaging = shipped * s["_pack"]

    ad_pct = s["_ad_pct"] * (1 + 1.0 * campaign) * rng.uniform(0.85, 1.15)
    ad_spend = revenue * ad_pct / 100
    # ROAS giảm dần khi đốt nhiều; doanh số quy cho quảng cáo không vượt 85% GMV
    roas_raw = s["_roas0"] * (6.0 / ad_pct) ** 0.5 * rng.uniform(0.85, 1.15)
    ad_gmv = min(0.85 * gmv, ad_spend * roas_raw)
    roas = ad_gmv / ad_spend if ad_spend else 0.0
    affiliate = revenue * s["_aff_share"] * AFFILIATE_RATE

    fixed = s["_fixed"] * rng.uniform(0.95, 1.05)
    profit = (payout - (0 if tax_withheld else tax) - cogs - return_loss - shipping_subsidy
              - return_shipping - packaging - ad_spend - affiliate - fixed)

    row = {
        "store_id": s["store_id"], "month": month,
        "platform": s["platform"], "category": s["category"],
        "orders_placed": placed, "orders_cancelled": cancelled,
        "orders_failed_delivery": failed, "orders_returned": returned,
        "orders_completed": completed,
        "aov_vnd": r1000(aov), "gmv_vnd": r1000(gmv), "revenue_vnd": r1000(revenue),
        "shop_voucher_vnd": r1000(voucher), "net_sales_vnd": r1000(net_sales),
        "commission_fee_vnd": r1000(commission), "payment_fee_vnd": r1000(payment),
        "service_fee_vnd": r1000(service), "per_order_fee_vnd": r1000(per_order_fee),
        "platform_fee_vnd": r1000(platform_fee),
        "tax_vnd": r1000(tax), "tax_withheld_by_platform": int(tax_withheld),
        "payout_vnd": r1000(payout),
        "cogs_vnd": r1000(cogs), "return_goods_loss_vnd": r1000(return_loss),
        "shipping_subsidy_vnd": r1000(shipping_subsidy),
        "return_shipping_vnd": r1000(return_shipping),
        "packaging_vnd": r1000(packaging),
        "ad_spend_vnd": r1000(ad_spend), "ad_attributed_gmv_vnd": r1000(ad_gmv),
        "roas": round(roas, 2), "affiliate_commission_vnd": r1000(affiliate),
        "fixed_cost_vnd": r1000(fixed),
        "net_profit_vnd": r1000(profit),
        "net_margin_pct": round(profit / revenue * 100, 2) if revenue else 0.0,
    }
    return row


def bucket_shares(r: dict) -> dict:
    rev = r["revenue_vnd"] or 1
    return {
        "quang_cao": (r["ad_spend_vnd"] + r["affiliate_commission_vnd"]) / rev * 100,
        "voucher": r["shop_voucher_vnd"] / rev * 100,
        "phi_san": r["platform_fee_vnd"] / rev * 100,
        "hoan_hang": (r["return_goods_loss_vnd"] + r["return_shipping_vnd"]) / rev * 100,
        "phi_ship": r["shipping_subsidy_vnd"] / rev * 100,
        "gia_von": r["cogs_vnd"] / rev * 100,
    }


def label_rows(rows: list[dict]) -> list[str]:
    """Nguyên nhân chính theo QUY TẮC (không nhìn archetype):
    khoản chi (điểm % doanh thu) lệch lên nhiều nhất so với trung vị cùng ngành × sàn.
    Lệch lớn nhất < MIN_EXCESS_PP → 'khong_ro_ri' (không có khoản nào nổi bật)."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r["category"], r["platform"])].append(r)
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)

    def medians(rs):
        sh = [bucket_shares(x) for x in rs]
        med = {b: statistics.median(x[b] for x in sh) for b in COST_BUCKETS}
        med["margin"] = statistics.median(x["net_margin_pct"] for x in rs)
        return med

    cache: dict = {}
    out = []
    for r in rows:
        key = (r["category"], r["platform"])
        peers = groups[key] if len(groups[key]) >= 24 else by_cat[r["category"]]
        ck = key if len(groups[key]) >= 24 else r["category"]
        if ck not in cache:
            cache[ck] = medians(peers)
        med = cache[ck]
        sh = bucket_shares(r)
        top = max(COST_BUCKETS, key=lambda b: sh[b] - med[b])
        out.append(top if sh[top] - med[top] >= MIN_EXCESS_PP else "khong_ro_ri")
    return out


PLATFORM_TYPOS = {
    "Shopee": ["shopee", "Shopee.vn", "Shopee Vn", "SHOPEE"],
    "TikTok Shop": ["Tiktok shop", "TikTokShop", "tiktok", "TIKTOK SHOP"],
    "Lazada": ["lazada", "Lazada.vn", "Lazada Vn"],
    "Tiki": ["tiki", "Tiki.vn"],
}


def make_dirty(rng: random.Random, rows: list[dict]) -> tuple[list[dict], dict]:
    """Bản có lỗi cài sẵn (cho câu khó + luyện làm sạch). Trả về rows + cờ lỗi theo (store, month)."""
    out, flags = [], defaultdict(list)
    for r in rows:
        d = dict(r)
        k = (d["store_id"], d["month"])
        if rng.random() < 0.05:
            d["platform"] = rng.choice(PLATFORM_TYPOS[d["platform"]]); flags[k].append("platform_typo")
        if rng.random() < 0.08:
            d["cogs_vnd"] = ""; d["net_profit_vnd"] = ""; d["net_margin_pct"] = ""
            flags[k].append("missing_cogs")
        if rng.random() < 0.05:
            d["ad_spend_vnd"] = ""; flags[k].append("missing_ad_spend")
        if rng.random() < 0.01:
            d["shop_voucher_vnd"] = r1000(d["revenue_vnd"] * rng.uniform(1.0, 1.2))
            flags[k].append("voucher_over_revenue")
        if rng.random() < 0.02:
            d["revenue_vnd"] = f"{d['revenue_vnd']:,}".replace(",", ".")
            flags[k].append("number_as_text")
        out.append(d)
        if rng.random() < 0.01:
            out.append(dict(d)); flags[k].append("duplicate_row")
    return out, flags


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    fields = fields or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summarize(rows: list[dict], stores: list[dict], labels: list[str]) -> None:
    arch_of = {s["store_id"]: s["_arch"] for s in stores}
    margins = [r["net_margin_pct"] for r in rows]
    loss = sum(m < 0 for m in margins)
    print(f"\n{len(stores)} shop × {len(rows) // len(stores)} tháng = {len(rows)} dòng")
    print(f"Lãi ròng / doanh thu: trung vị {statistics.median(margins):.1f}% · "
          f"tháng lỗ {loss}/{len(rows)} ({loss / len(rows):.0%})")
    print("\nTrung vị phí sàn % doanh thu (theo sàn, trước → sau 2025-04 nếu là Shopee):")
    for p in PLATFORM_SHARE:
        pr = [bucket_shares(r)["phi_san"] for r in rows if r["platform"] == p]
        if not pr:
            continue
        line = f"  {p:12s} {statistics.median(pr):5.1f}%  (n={len(pr)})"
        if p == "Shopee":
            pre = [bucket_shares(r)["phi_san"] for r in rows if r["platform"] == p and r["month"] < SHOPEE_FEE_CHANGE]
            post = [bucket_shares(r)["phi_san"] for r in rows if r["platform"] == p and r["month"] >= SHOPEE_FEE_CHANGE]
            if pre and post:
                line += f"   trước {statistics.median(pre):.1f}% → sau {statistics.median(post):.1f}%"
        print(line)
    print("\nTheo kiểu rò ẩn: lãi ròng trung vị · quy tắc gắn đúng nguyên nhân")
    agree_total = 0
    for a, (_, expected) in ARCHETYPES.items():
        idx = [i for i, r in enumerate(rows) if arch_of[r["store_id"]] == a]
        if not idx:
            continue
        med = statistics.median(rows[i]["net_margin_pct"] for i in idx)
        hit = sum(labels[i] == expected for i in idx)
        agree_total += hit
        top = Counter(labels[i] for i in idx).most_common(2)
        print(f"  {a:17s} n={len(idx):4d}  lãi {med:6.1f}%  khớp {hit / len(idx):4.0%}  (hay ra: {top})")
    print(f"  → khớp chung {agree_total / len(rows):.0%}. Chỉ lấy dòng khớp làm câu thử có đáp án chắc;"
          f" dòng lệch dùng làm câu khó (hai khoản sát nhau).")


def paste_text(rows_path: Path, store_id: str, month: str | None, no_cogs: bool) -> str:
    with rows_path.open(encoding="utf-8") as f:
        rs = [r for r in csv.DictReader(f) if r["store_id"] == store_id]
    if not rs:
        raise SystemExit(f"Không thấy {store_id} trong {rows_path}")
    r = next((x for x in rs if x["month"] == month), rs[-1])
    v = lambda k: f"{int(float(r[k])):,}".replace(",", ".") + "đ"
    lines = [
        f"Shop mình bán {r['category']} trên {r['platform']}, số tháng {r['month']}:",
        f"- Đơn đặt {r['orders_placed']}, huỷ {r['orders_cancelled']}, giao thất bại "
        f"{r['orders_failed_delivery']}, hoàn {r['orders_returned']}, thành công {r['orders_completed']}",
        f"- Doanh thu đơn thành công: {v('revenue_vnd')}",
        f"- Voucher shop: {v('shop_voucher_vnd')}",
        f"- Phí sàn (cố định + thanh toán + dịch vụ + phí/đơn): {v('platform_fee_vnd')}",
        f"- Quảng cáo: {v('ad_spend_vnd')} (ROAS {r['roas']})",
    ]
    if float(r["affiliate_commission_vnd"]) > 0:
        lines.append(f"- Hoa hồng affiliate: {v('affiliate_commission_vnd')}")
    lines += [
        f"- Ship shop bù: {v('shipping_subsidy_vnd')}, ship hoàn: {v('return_shipping_vnd')}",
        f"- Đóng gói: {v('packaging_vnd')}, chi phí cố định: {v('fixed_cost_vnd')}",
        f"- Tiền sàn trả về: {v('payout_vnd')}",
    ]
    if not no_cogs:
        lines.insert(3, f"- Giá vốn hàng bán: {v('cogs_vnd')}")
    lines.append("Bán được mà sao lãi ít vậy, nên cắt khoản nào?")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Sinh data giả lập Track D (shop bán nhiều mà lãi ít).")
    ap.add_argument("--stores", type=int, default=150)
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--start", default="2025-01", help="tháng đầu, dạng YYYY-MM")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "synthetic"))
    ap.add_argument("--dirty", action="store_true", help="ghi thêm store_months_dirty.csv có lỗi cài sẵn")
    ap.add_argument("--paste", nargs="+", metavar=("STORE_ID", "MONTH"),
                    help="in đoạn văn chủ shop dán vào bản chạy thử (đọc từ store_months.csv đã sinh)")
    ap.add_argument("--no-cogs", action="store_true", help="dùng với --paste: bỏ giá vốn (câu khó)")
    a = ap.parse_args()
    out = Path(a.out)

    if a.paste:
        print(paste_text(out / "store_months.csv", a.paste[0], a.paste[1] if len(a.paste) > 1 else None, a.no_cogs))
        return

    rng = random.Random(a.seed)
    stores = [make_store(rng, i + 1) for i in range(a.stores)]
    months = month_list(a.start, a.months)
    rows = [simulate_month(rng, s, m, t) for s in stores for t, m in enumerate(months)]
    labels = label_rows(rows)

    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "stores.csv", stores,
              ["store_id", "store_name", "platform", "category", "size_tier", "seller_type", "service_programs"])
    write_csv(out / "store_months.csv", rows)
    arch_of = {s["store_id"]: s["_arch"] for s in stores}
    lab = [{"store_id": r["store_id"], "month": r["month"], "archetype": arch_of[r["store_id"]],
            "archetype_cause": ARCHETYPES[arch_of[r["store_id"]]][1], "main_cause_rule": l,
            "dirty_flags": ""} for r, l in zip(rows, labels)]

    if a.dirty:
        dirty, flags = make_dirty(random.Random(a.seed + 1), rows)
        write_csv(out / "store_months_dirty.csv", dirty)
        for x in lab:
            x["dirty_flags"] = ";".join(flags.get((x["store_id"], x["month"]), []))
    write_csv(out / "labels.csv", lab)

    print(f"Đã ghi vào {out}/: stores.csv, store_months.csv, labels.csv"
          + (", store_months_dirty.csv" if a.dirty else "") + f"  (seed={a.seed})")
    summarize(rows, stores, labels)


if __name__ == "__main__":
    main()
