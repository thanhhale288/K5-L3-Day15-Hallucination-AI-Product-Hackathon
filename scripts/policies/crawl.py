"""B1 · Tải trang chính sách công khai → data/<thư mục sàn>/policies/raw-<platform>/<doc_id>.html (không commit).

Học viện TikTok Shop là trang render bằng JS → mở bằng trình duyệt headless (Playwright), như người xem
bình thường: không đăng nhập, không cookie tài khoản, 1 trang / ~3 giây.

    python -m pip install playwright && python -m playwright install chromium
    python scripts/policies/crawl.py [--platform tiktok] [--limit 2] [--force]
"""
import argparse
import csv
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import paths, read_urls  # noqa: E402

DELAY_S = 3
MIN_TEXT = 300  # trang render xong mà ít hơn số ký tự này → coi như chưa có nội dung bài


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="tiktok")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="tải lại cả trang đã có")
    a = ap.parse_args()

    from playwright.sync_api import sync_playwright

    out = paths(a.platform)["raw"]
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, "_log.csv")
    new_log = not os.path.exists(log_path)
    rows = read_urls(a.platform)[: a.limit or None]

    with sync_playwright() as p, open(log_path, "a", newline="", encoding="utf-8") as lf:
        log = csv.writer(lf)
        if new_log:
            log.writerow(["doc_id", "url", "status", "text_chars", "fetched_at"])
        browser = p.chromium.launch()
        page = browser.new_page(locale="vi-VN")
        for doc_id, _ptype, url in rows:
            path = os.path.join(out, doc_id + ".html")
            if os.path.exists(path) and not a.force:
                print("bỏ qua (đã có):", doc_id)
                continue
            status, chars = "error", 0
            for attempt in range(3):
                try:
                    resp = page.goto(url, wait_until="networkidle", timeout=45000)
                    page.wait_for_timeout(4000)
                    body = page.inner_text("body")
                    chars = len(body)
                    status = str(resp.status if resp else "noresp")
                    if "Internal Server Error" in body[:200]:  # server lỗi tạm thời → thử lại
                        status = "server_error"
                    elif chars >= MIN_TEXT:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write("<!-- source: %s -->\n" % url)
                            f.write(page.content())
                        break
                    status = "empty"
                except Exception as e:  # mạng chập chờn / timeout → thử lại
                    status = "error:%s" % type(e).__name__
                time.sleep(DELAY_S * (attempt + 1))
            log.writerow([doc_id, url, status, chars, datetime.datetime.now().astimezone().isoformat(timespec="seconds")])
            print(doc_id, status, chars)
            time.sleep(DELAY_S)
        browser.close()


if __name__ == "__main__":
    main()
