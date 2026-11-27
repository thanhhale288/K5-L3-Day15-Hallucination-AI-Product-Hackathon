"""B1' · Tải bài chính sách từ trung tâm người bán của Shopee và Lazada → raw-<platform>/<doc_id>.json (không commit).

Hai trang này (Shopee Seller Education Hub, Lazada Seller Center) là SPA: nội dung bài nằm trong phản hồi API
mà chính trang tự gọi. Script mở trình duyệt headless như người xem bình thường (không đăng nhập, không cookie
tài khoản, không tự dựng request), điều hướng, rồi đọc phản hồi mà trang đã tải. 1 trang / ~3 giây.

    python -m pip install playwright && python -m playwright install chromium
    python scripts/policies/crawl_hub.py --platform shopee --discover   # liệt kê bài theo chuyên mục → raw-shopee/_catalog.json
    python scripts/policies/crawl_hub.py --platform shopee              # tải các bài trong urls_shopee.txt
    python scripts/policies/crawl_hub.py --platform lazada --discover
    python scripts/policies/crawl_hub.py --platform lazada

File urls_<platform>.txt dùng chung định dạng với urls_tiktok.txt: "<policy_type> <url>".
Mỗi raw JSON: {doc_id, title, html, updated_at (YYYY-MM-DD hoặc null), url, category, fetched_at}.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import paths, read_urls  # noqa: E402

DELAY_S = 3

# Chuyên mục cần quét khi --discover. Chọn theo 5 policy_type; bổ sung khi cần.
SHOPEE_CATS = {  # l2_cat_id → tên (Shopee Seller Education Hub, banhang.shopee.vn/edu)
    2081: "Quản Lý Doanh Thu", 427: "Quy Trình Thanh Toán", 428: "Phân Loại Phí", 166: "Số dư TK Shopee",
    176: "Chương Trình Shopee", 2042: "Tiếp thị liên kết Người bán", 445: "Gói Dịch Vụ & Chương Trình",
    342: "Dịch Vụ Hiển Thị", 180: "Công Cụ Marketing Của Shop", 175: "Tổng Quan về Shopee MKT",
    585: "Mẹo Tăng Doanh Thu", 251: "Trả Hàng / Hoàn Tiền", 1764: "FAQ Thanh toán & Trả hàng",
    1763: "FAQ Chương trình & Công cụ", 1726: "Cập Nhật Mới Nhất", 1110: "Quy Định Shopee",
    1109: "Tính năng mới", 163: "Quy Định Vận Hành", 2148: "Phương Thức Vận Chuyển Shopee",
}
LAZADA_CATS = {  # categoryId → tên (sellercenter.lazada.vn/helpcenter)
    1000028699: "Các Loại Phí Khi Bán Hàng", 1000028698: "Các Vấn Đề Về Thanh Toán",
    1000028700: "Báo Cáo Tài Chính và Hoá Đơn", 1000028702: "Tài chính: Các Vấn Đề Khác",
    1000028685: "Mã giảm giá", 1000028680: "Freeship Max", 1000028686: "Miễn phí vận chuyển",
    1000028684: "Combo Linh hoạt", 1000028709: "Giải Pháp Tiếp Thị Liên Kết", 1000028708: "Tài Trợ Hiển Thị Sản Phẩm",
    1000028707: "Tài Trợ Sản Phẩm Mới", 1000028710: "Tổng Quan Các Dịch Vụ Tài Trợ", 1000028711: "Dịch vụ tài trợ: Cập nhật mới nhất",
    1000028714: "Dịch vụ tài trợ: Câu hỏi thường gặp", 1000028674: "Đơn hàng Giao hàng thất bại",
    1000028675: "Đơn hàng Hoàn trả về kho Lazada", 1000028676: "Đơn hàng Trả hàng trực tiếp cho Nhà bán hàng",
    1000028677: "Đơn trả hàng với lý do Thay đổi ý", 1000028750: "Tài khoản Nhà bán hàng",
    1000028756: "Chính sách: Quản lý đơn hàng", 1000028757: "Chính sách: Kinh doanh & Chương trình khuyến mãi",
    1000028759: "Chính sách: Dịch vụ Nhà bán hàng",
}

SHOPEE_ARTICLE = re.compile(r"banhang\.shopee\.vn/edu/article/(\d+)")
LAZADA_QUESTION = re.compile(r"questionId=(\d+)")


def today():
    return datetime.date.today().isoformat()


def epoch_date(v):
    try:
        return datetime.datetime.fromtimestamp(int(v), datetime.timezone(datetime.timedelta(hours=7))).date().isoformat()
    except (TypeError, ValueError):
        return None


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def collect(page, pattern, trigger):
    """Chạy trigger() (điều hướng), trả list (url, text) của các phản hồi khớp pattern mà trang đã tải."""
    got = []

    def on(resp):
        if re.search(pattern, resp.url):
            try:
                got.append((resp.url, resp.text()))
            except Exception:
                pass

    page.on("response", on)
    try:
        trigger()
    finally:
        page.remove_listener("response", on)
    return got


# ------------------------------ Shopee ------------------------------
def shopee_discover(page, out):
    catalog = {}

    def add(got, cid, name):
        total = 0
        for u, t in got:
            if "l2_cat_id=%d" % cid not in u:
                continue
            d = json.loads(t).get("data") or {}
            total = max(total, d.get("total", 0))
            for a in d.get("article_list", []):
                catalog[str(a["article_id"])] = {"id": a["article_id"], "title": a["title"], "cat_id": cid, "cat": name,
                                                  "updated_at": epoch_date(a.get("rtime")),
                                                  "url": "https://banhang.shopee.vn/edu/article/%d" % a["article_id"]}
        return total

    for cid, name in SHOPEE_CATS.items():
        url = "https://banhang.shopee.vn/edu/category?sub_cat_id=%d" % cid
        got = collect(page, r"/help/api/v3/article/list/",
                      lambda: (page.goto(url, wait_until="domcontentloaded", timeout=60000), page.wait_for_timeout(5000)))
        total = add(got, cid, name)
        for pn in range(2, -(-total // 15) + 1):  # trang 2.. bằng cách bấm số trang như người xem
            btn = page.locator(".shopee-pagination").get_by_text(str(pn), exact=True)
            if not btn.count():
                print("CẢNH BÁO %s: không thấy nút trang %d" % (name, pn))
                break
            got = collect(page, r"/help/api/v3/article/list/", lambda: (btn.first.click(), page.wait_for_timeout(3000)))
            add(got, cid, name)
        n = sum(1 for v in catalog.values() if v["cat_id"] == cid)
        print(cid, name, n, "/", total, "bài", flush=True)
        if n < total:
            print("CẢNH BÁO %s: mới lấy %d/%d bài" % (name, n, total))
        time.sleep(DELAY_S)
    write_json(os.path.join(out, "_catalog.json"), catalog)
    print("catalog:", len(catalog), "bài →", os.path.join(out, "_catalog.json"))


def shopee_help_fetch(page, url):
    """Văn bản gốc trên help.shopee.vn: trang tự gọi /api/inhouse/hc/mobile/v1/article?id=<id>."""
    aid = re.search(r"/article/(\d+)", url).group(1)
    got = collect(page, r"/api/inhouse/hc/mobile/v1/article\?[^ ]*\bid=%s\b" % aid,
                  lambda: (page.goto(url, wait_until="domcontentloaded", timeout=60000), page.wait_for_timeout(7000)))
    for _u, t in got:
        d = json.loads(t)
        if d.get("content"):
            return {"title": d.get("title", ""), "html": d["content"], "updated_at": None, "category": "help.shopee.vn"}
    return None


def shopee_fetch(page, doc_id, url, ptype):
    if "help.shopee.vn" in url:
        return shopee_help_fetch(page, url)
    aid = SHOPEE_ARTICLE.search(url).group(1)
    got = collect(page, r"/help/api/v3/article/detail/.*article_id=%s" % aid,
                  lambda: (page.goto(url, wait_until="domcontentloaded", timeout=60000), page.wait_for_timeout(7000)))
    for _u, t in got:
        d = json.loads(t).get("data") or {}
        if d.get("content"):
            return {"title": d.get("title", ""), "html": d["content"], "updated_at": epoch_date(d.get("rtime")),
                    "category": str(d.get("cat_id", ""))}
    return None


# ------------------------------ Lazada ------------------------------
def lazada_discover(page, out):
    catalog = {}

    def add(got, cid, name):
        pages = 1
        for _u, t in got:
            d = (json.loads(t).get("data") or {}).get("resultData") or {}
            pages = max(pages, int(d.get("pageCount") or 1))
            for a in d.get("data", []):
                qid = str(a.get("questionCode") or a.get("knowledgeId"))
                catalog[qid] = {"id": qid, "title": a.get("title", ""), "cat_id": cid, "cat": name,
                                "updated_at": (a.get("gmtModified") or "")[:10] or None,
                                "url": "https://sellercenter.lazada.vn/helpcenter/s/faq/knowledge?categoryId=%d&m_station=faq&questionId=%s" % (cid, qid)}
        return pages

    for cid, name in LAZADA_CATS.items():
        url = "https://sellercenter.lazada.vn/helpcenter/s/faq/category?categoryId=%d&m_station=faq" % cid
        got = collect(page, r"helpcenter\.knowledge\.list/1\.0",
                      lambda: (page.goto(url, wait_until="domcontentloaded", timeout=60000), page.wait_for_timeout(7000)))
        pages = add(got, cid, name)
        for pn in range(2, pages + 1):  # trang 2.. bằng cách bấm số trang như người xem
            btn = page.locator(".next-pagination-list").get_by_text(str(pn), exact=True)
            if not btn.count():
                print("CẢNH BÁO %s: không thấy nút trang %d" % (name, pn))
                break
            got = collect(page, r"helpcenter\.knowledge\.list/1\.0", lambda: (btn.first.click(), page.wait_for_timeout(4000)))
            add(got, cid, name)
        n = sum(1 for v in catalog.values() if v["cat_id"] == cid)
        print(cid, name, n, "bài / %d trang" % pages, flush=True)
        time.sleep(DELAY_S)
    write_json(os.path.join(out, "_catalog.json"), catalog)
    print("catalog:", len(catalog), "bài →", os.path.join(out, "_catalog.json"))


def lazada_fetch(page, doc_id, url, ptype):
    qid = LAZADA_QUESTION.search(url).group(1)
    got = collect(page, r"helpcenter\.knowledge\.detail/1\.0",
                  lambda: (page.goto(url, wait_until="domcontentloaded", timeout=60000), page.wait_for_timeout(7000)))
    for _u, t in got:
        d = (json.loads(t).get("data") or {}).get("resultData") or {}
        if d.get("content") and str(d.get("knowledgeId")) == qid:
            return {"title": d.get("title", ""), "html": d["content"], "updated_at": (d.get("gmtModified") or "")[:10] or None,
                    "category": d.get("categoryName", "")}
    return None


HANDLERS = {"shopee": (shopee_discover, shopee_fetch), "lazada": (lazada_discover, lazada_fetch)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True, choices=sorted(HANDLERS))
    ap.add_argument("--discover", action="store_true", help="chỉ liệt kê bài theo chuyên mục → _catalog.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="tải lại cả bài đã có")
    a = ap.parse_args()

    from playwright.sync_api import sync_playwright

    out = paths(a.platform)["raw"]
    os.makedirs(out, exist_ok=True)
    discover, fetch = HANDLERS[a.platform]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="vi-VN")
        if a.discover:
            discover(page, out)
            browser.close()
            return
        fails = []
        for doc_id, ptype, url in read_urls(a.platform)[: a.limit or None]:
            path = os.path.join(out, doc_id + ".json")
            if os.path.exists(path) and not a.force:
                print("bỏ qua (đã có):", doc_id)
                continue
            res = None
            for attempt in range(3):
                try:
                    res = fetch(page, doc_id, url, ptype)
                except Exception as e:  # mạng chập chờn / timeout → thử lại
                    print("  lỗi %s (lần %d)" % (type(e).__name__, attempt + 1))
                if res:
                    break
                time.sleep(DELAY_S * (attempt + 1))
            if not res:
                fails.append(doc_id)
                print("THẤT BẠI:", doc_id, url)
            else:
                res.update({"doc_id": doc_id, "url": url, "fetched_at": today(), "policy_type": ptype})
                write_json(path, res)
                print("ok", doc_id, len(res["html"]), "ký tự HTML ·", res["title"][:60])
            time.sleep(DELAY_S)
        browser.close()
        if fails:
            print("\n%d bài không tải được: %s" % (len(fails), ", ".join(fails)))
            sys.exit(1)


if __name__ == "__main__":
    main()
