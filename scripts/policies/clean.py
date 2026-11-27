"""B2 · HTML đã crawl → Markdown sạch (<kho sàn>/clean/<doc_id>.md) + <kho sàn>/manifest.csv.
Kho sàn = data/<thư mục sàn>/policies (codebase/policy_paths.py).

Giữ heading H1–H4, list, bảng (mỗi hàng bảng → 1 dòng "Cột: giá trị | …"); bỏ menu, footer, script.
Chuẩn hoá Unicode NFC, không sửa số / % / đ / ngày.

    python -m pip install beautifulsoup4 markdownify
    python scripts/policies/clean.py [--platform tiktok]
"""
import argparse
import csv
import datetime
import hashlib
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import paths, read_urls  # noqa: E402

DROP_TAGS = ["script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form", "iframe", "button"]
DROP_CLASS = re.compile(r"(nav|menu|footer|header|breadcrumb|sidebar|recommend|related|feedback|cookie|banner|share)", re.I)
CONTENT_HINT = re.compile(r"(essay|article|content|rich|detail|knowledge)", re.I)
_DATE = r"(?:(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})|ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4}))"
DATE_RE = re.compile(r"(?:áp dụng từ|có hiệu lực từ|hiệu lực từ|kể từ)[^0-9]{0,40}?" + _DATE, re.I)
UPDATED_RE = re.compile(r"^Updated at:\s*\n?:?\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$", re.M)
TITLE_SUFFIX = re.compile(r"\s*\|\s*Học viện TikTok Shop.*$")
MANIFEST_COLS = ["doc_id", "platform", "title", "url", "policy_type", "effective_date", "updated_at", "fetched_at",
                 "content_hash"]


DATA_CELL = re.compile(r"\d[\d .,]*\s*(%|đ|₫|vnđ|vnd)|^[\s(\-+)]*\d[\d .,]*$", re.I)


def _grid(table):
    """Dàn rowspan/colspan ra lưới đầy đủ: ô gộp được lặp lại ở mọi vị trí nó phủ."""
    grid, pending = [], {}  # pending[(r, c)] = text còn kéo xuống từ rowspan
    for r, tr in enumerate(table.find_all("tr")):
        row, c = [], 0
        cells = tr.find_all(["th", "td"])
        k = 0
        while k < len(cells) or (r, c) in pending:
            if (r, c) in pending:
                row.append(pending.pop((r, c)))
                c += 1
                continue
            cell = cells[k]
            k += 1
            text = cell.get_text(" ", strip=True)
            rs, cs = int(cell.get("rowspan") or 1), int(cell.get("colspan") or 1)
            for dc in range(cs):
                row.append(text)
                for dr in range(1, rs):
                    pending[(r + dr, c + dc)] = text
            c += cs
        grid.append(row)
    width = max((len(r) for r in grid), default=0)
    return [r + [""] * (width - len(r)) for r in grid if any(r)]


def table_to_lines(table):
    """Bảng HTML → các dòng '- Cột: giá trị | …' để mỗi hàng tự đứng được khi bị cắt.
    Hàng đầu chỉ có 1 giá trị trải ngang → dòng chú thích. Tối đa 2 hàng đầu không có số liệu → header."""
    grid = _grid(table)
    if not grid:
        return ""
    lines = []
    if len(grid[0]) > 1 and len({v for v in grid[0] if v}) == 1 and all(grid[0]):
        lines.append("**%s**" % grid[0][0])
        grid = grid[1:]
    header_rows = []
    while grid and len(header_rows) < 2 and len(grid) > 1 and not any(DATA_CELL.search(v) for v in grid[0] if v):
        header_rows.append(grid.pop(0))
    head = []
    for i in range(len(grid[0]) if grid else 0):
        parts = []
        for hr in header_rows:
            if hr[i] and hr[i] not in parts:
                parts.append(hr[i])
        head.append(" · ".join(reversed(parts)))
    for r in grid:
        cells, last = [], None
        for i, v in enumerate(r):
            if not v:
                continue
            cell = "%s: %s" % (head[i], v) if head and head[i] else v
            if cell != last:
                cells.append(cell)
            last = cell
        if cells:
            lines.append("- " + " | ".join(cells))
    return "\n".join(lines)


def pick_content(soup):
    for t in soup(DROP_TAGS):
        t.decompose()
    for t in soup.find_all(class_=DROP_CLASS):
        if t.name not in ("html", "body"):
            t.decompose()
    candidates = soup.find_all(["article", "main"]) + soup.find_all(class_=CONTENT_HINT)
    candidates = [c for c in candidates if len(c.get_text(strip=True)) > 200] or [soup.body or soup]
    return max(candidates, key=lambda c: len(c.get_text(strip=True)))


def to_markdown(html):
    from bs4 import BeautifulSoup
    from markdownify import markdownify

    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else TITLE_SUFFIX.sub("", soup.title.get_text(strip=True) if soup.title else "")
    for card in soup.select(".file-container, .file-upload-card"):  # PDF đính kèm: giữ tên tệp làm dấu vết
        name = card.select_one(".file-upload-card-name")
        p = soup.new_tag("p")
        p.string = "[Tệp đính kèm, chưa trích nội dung: %s]" % (name.get_text(strip=True) if name else "không rõ tên")
        card.replace_with(p)
    node = pick_content(soup)
    tables = {}
    for n, table in enumerate(node.find_all("table")):
        key = "TABLEPLACEHOLDER%d" % n  # chèn sau markdownify để nó không xuống dòng / escape giữa bảng
        tables[key] = table_to_lines(table)
        p = soup.new_tag("p")
        p.string = key
        table.replace_with(p)
    md = markdownify(str(node), heading_style="ATX", bullets="-", strip=["a", "img"])
    for key, lines in tables.items():
        md = md.replace(key, "\n" + lines + "\n")
    md = unicodedata.normalize("NFC", md)
    md = re.sub(r"[ \t ]+", " ", md)
    md = re.sub(r"\n\s*\n\s*\n+", "\n\n", md).strip()
    md = re.sub(r"^(#{5,6}) ", "#### ", md, flags=re.M)  # giữ tối đa H4
    md = re.sub(r"^(#{1,4}) \*\*(.+?)\*\*\s*$", r"\1 \2", md, flags=re.M)  # heading không cần in đậm
    return unicodedata.normalize("NFC", title.strip()), md


def _iso(d, m, y):
    try:
        return datetime.date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def effective_date(text):
    """Ngày hiệu lực ĐẦU TIÊN nêu trong bài (một bài có thể nêu nhiều mốc → chỉ là gợi ý, không đoán thêm)."""
    m = DATE_RE.search(text)
    if not m:
        return None
    g = m.groups()
    return _iso(*g[0:3]) if g[0] else _iso(*g[3:6])


def split_updated(md):
    """Tách dòng 'Updated at: dd/mm/yyyy' khỏi thân bài → (updated_at ISO | None, md còn lại)."""
    m = UPDATED_RE.search(md)
    if not m:
        return None, md
    return _iso(*m.groups()), (md[:m.start()] + md[m.end():]).strip()


def fetched_dates(platform):
    path = os.path.join(paths(platform)["raw"], "_log.csv")
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["status"].isdigit():
                    out[r["doc_id"]] = r["fetched_at"][:10]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="tiktok")
    a = ap.parse_args()
    P = paths(a.platform)
    os.makedirs(P["clean"], exist_ok=True)
    fetched = fetched_dates(a.platform)

    old = {}
    if os.path.exists(P["manifest"]):
        with open(P["manifest"], encoding="utf-8") as f:
            old = {r["doc_id"]: r for r in csv.DictReader(f)}

    for doc_id, ptype, url in read_urls(a.platform):
        path = os.path.join(P["raw"], doc_id + ".html")
        if not os.path.exists(path):
            print("chưa crawl:", doc_id)
            continue
        with open(path, encoding="utf-8") as f:
            title, md = to_markdown(f.read())
        updated, md = split_updated(md)
        if len(md) < 200:
            print("CẢNH BÁO nội dung quá ngắn (%d ký tự), kiểm selector:" % len(md), doc_id)
        with open(os.path.join(P["clean"], doc_id + ".md"), "w", encoding="utf-8") as f:
            f.write("# %s\n\n%s\n" % (title, md) if not md.startswith("# ") else md + "\n")
        old[doc_id] = {
            "doc_id": doc_id, "platform": a.platform, "title": title, "url": url, "policy_type": ptype,
            "effective_date": effective_date(md) or "", "updated_at": updated or "", "fetched_at": fetched.get(doc_id, ""),
            "content_hash": hashlib.sha256(md.encode("utf-8")).hexdigest(),
        }
        print("ok", doc_id, len(md), "ký tự ·", title[:60])

    with open(P["manifest"], "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        w.writeheader()
        for r in sorted(old.values(), key=lambda r: r["doc_id"]):
            w.writerow(r)
    print("manifest:", len(old), "tài liệu →", P["manifest"])


if __name__ == "__main__":
    main()
