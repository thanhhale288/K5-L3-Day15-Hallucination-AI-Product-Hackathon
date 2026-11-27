"""Pipeline chuẩn bị dữ liệu chính sách Shopee Việt Nam cho RAG. Chỉ dùng thư viện chuẩn của Python.

  python rag/pipeline.py crawl [--limit N] [--refresh]   tải bài từ help.shopee.vn → data/shopee_policy/raw + clean
  python rag/pipeline.py chunk [--max 600 --overlap 80]  cắt theo heading/section → data/shopee_policy/chunks.jsonl
  python rag/pipeline.py filter                          lọc dataset Seller-only → data/shopee_policy/seller/
  python rag/pipeline.py embed [--dataset seller|all]    sinh embedding (mặc định Seller-only) → data/shopee_policy/seller/embeddings.jsonl

Nguồn: chỉ help.shopee.vn (Trung tâm hỗ trợ chính thức). Danh sách bài lấy từ sitemap.xml (robots.txt: Allow /),
nội dung lấy từ API công khai mà chính trang web gọi: /api/inhouse/hc/mobile/v1/article?id=<id>.
Nội dung giữ nguyên văn (heading, bullet, bảng), chỉ bỏ thẻ HTML / ảnh / style. Không tóm tắt, không viết lại.

Embedding: cấu hình qua .env (không hardcode key), xem rag/README.md.
"""
import argparse
import hashlib
import html
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "shopee_policy")
RAW = os.path.join(OUT, "raw")
CLEAN = os.path.join(OUT, "clean")
DOCS = os.path.join(OUT, "documents.jsonl")
CHUNKS = os.path.join(OUT, "chunks.jsonl")
EMB = os.path.join(OUT, "embeddings.jsonl")
EMB_META = os.path.join(OUT, "embeddings_meta.json")

BASE = "https://help.shopee.vn"
SITEMAP = BASE + "/sitemap.xml"
ARTICLE_API = BASE + "/api/inhouse/hc/mobile/v1/article?id={id}"
UA = "Mozilla/5.0 (compatible; policy-rag-research/0.1)"

# Chọn bài liên quan chính sách: theo tên danh mục hoặc tiêu đề (so khớp không dấu, chữ thường).
POLICY_PATTERNS = [
    r"chinh sach", r"dieu khoan", r"dieu kien", r"quy dinh", r"quy che", r"quy tac", r"tieu chuan",
    r"tra hang", r"hoan tien", r"van chuyen", r"giao hang", r"phi ", r"phi$", r"bieu phi",
    r"\bcam\b", r"han che", r"vi pham", r"xu phat", r"sao qua ta", r"khieu nai",
    r"bao mat", r"bao hanh", r"hang gia", r"so huu tri tue", r"nguoi ban",
    r"\bthue\b", r"doi soat", r"khoa tai khoan", r"tranh chap",
]
POLICY_RE = re.compile("|".join(POLICY_PATTERNS))


def strip_accents(s):
    import unicodedata
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def http_get(url, retries=3, timeout=30):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/xml, */*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404, 410):
                raise
            last = e
            time.sleep(1.5 * (i + 1))
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


# ---------------------------------------------------------------- HTML → văn bản giữ cấu trúc
BLOCK = {"p", "div", "section", "article", "blockquote", "pre", "figure", "figcaption"}
HEAD = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
NUM_HEAD = re.compile(r"^((?:Điều|ĐIỀU|Mục|MỤC|Chương|CHƯƠNG|Phần|PHẦN)\s+\d+|[IVX]+\.|\d+(?:\.\d+)*)\.?\s+\S")
SKIP = {"script", "style", "noscript", "img", "svg", "iframe", "video", "button", "nav", "footer", "header"}


class HtmlToText(HTMLParser):
    """Đổi HTML bài viết thành Markdown đơn giản: heading → '#', li → '- ' / '1. ', bảng → '| a | b |'.
    Đoạn <p> chỉ gồm chữ in đậm (cách Shopee viết tiêu đề mục) được coi là heading cấp 3."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []          # danh sách (kind, text): kind ∈ {"h1".."h6", "p", "li", "row"}
        self.buf = []            # các mảnh (text, bold)
        self.bold = 0
        self.skip = 0
        self.lists = []          # stack: ["ul"| "ol", counter]
        self.head = None
        self.row = None
        self.cell = None
        self.in_li = False

    def _flush(self, kind=None):
        text = "".join(t for t, _ in self.buf)
        text = re.sub(r"[ \t ​]+", " ", text).strip()
        pieces = [(t, b) for t, b in self.buf if t.strip()]
        self.buf = []
        if not text:
            return
        if kind is None:
            if self.head:
                kind = "h%d" % self.head
            elif pieces and all(b for _, b in pieces) and len(text) <= 160 and not self.lists:
                m = NUM_HEAD.match(text)   # tiêu đề in đậm có đánh số: cấp theo số (4. → h3, 4.2 → h4)
                kind = "h%d" % min(2 + m.group(1).count(".") + 1, 5) if m and m.group(1)[0].isdigit() else "h3"
            elif NUM_HEAD.match(text) and len(text) <= 110 and not text.rstrip().endswith((".", ";", ",", ":")):
                depth = NUM_HEAD.match(text).group(1).count(".") + 1
                kind = "h%d" % min(2 + depth, 5)
            elif len(text) <= 110 and text.upper() == text and sum(ch.isalpha() for ch in text) >= 8:
                kind = "h2"
            else:
                kind = "p"
        self.lines.append((kind, text))

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ("strong", "b"):
            self.bold += 1
        elif tag == "br":
            if self.cell is not None:
                self.cell.append(" ")
            else:
                self._flush()
        elif tag in HEAD:
            self._flush()
            self.head = HEAD[tag]
        elif tag in ("ul", "ol"):
            self._flush_li()
            self._flush()
            start = dict(attrs).get("start")
            self.lists.append([tag, int(start) - 1 if start and start.isdigit() else 0])
            self.in_li = False
        elif tag == "li":
            self._flush_li()
            self._flush()
            if self.lists:
                self.lists[-1][1] += 1
            self.in_li = True
        elif tag == "tr":
            self._flush()
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag in BLOCK:
            if self.cell is None and not self.in_li:
                self._flush()
            elif self.in_li and self.buf:
                self.buf.append((" ", False))   # <p> trong <li>: cùng một mục, chỉ cách nhau dấu cách

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ("strong", "b"):
            self.bold = max(0, self.bold - 1)
        elif tag in HEAD:
            self._flush()
            self.head = None
        elif tag == "li":
            self._flush_li()
        elif tag in ("ul", "ol"):
            self._flush_li()
            if self.lists:
                self.lists.pop()
            self.in_li = False
        elif tag in ("td", "th"):
            if self.cell is not None and self.row is not None:
                self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr":
            if self.row and any(self.row):
                self.lines.append(("row", "| " + " | ".join(self.row) + " |"))
            self.row = None
        elif tag in BLOCK and self.cell is None and not self.in_li:
            self._flush()

    def _flush_li(self):
        if not self.buf:
            return
        depth = max(0, len(self.lists) - 1)
        kind, n = (self.lists[-1] if self.lists else ["ul", 0])
        text = re.sub(r"[ \t ​]+", " ", "".join(t for t, _ in self.buf)).strip()
        self.buf = []
        self.in_li = False
        if text:
            marker = ("%d." % n) if kind == "ol" else "-"
            self.lines.append(("li", "  " * depth + marker + " " + text))

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
        else:
            self.buf.append((data.replace("\n", " "), self.bold > 0 or self.head is not None))

    def close(self):
        super().close()
        self._flush_li()
        self._flush()


def html_to_markdown(content):
    p = HtmlToText()
    p.feed(content or "")
    p.close()
    out, prev = [], None
    for kind, text in p.lines:
        if kind.startswith("h"):
            text = "#" * int(kind[1]) + " " + text.strip("*: ").strip() if text.strip("*: ").strip() else ""
            if not text:
                continue
            out.append("")
            out.append(text)
            out.append("")
        elif kind in ("li", "row"):
            if prev not in ("li", "row"):
                out.append("")
            out.append(text)
        else:
            out.append("")
            out.append(text)
        prev = kind
    md = "\n".join(out)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md


# ---------------------------------------------------------------- 1. crawl
def sitemap_articles():
    xml = http_get(SITEMAP)
    out = []
    for loc in re.findall(r"<loc>([^<]+)</loc>", xml):
        m = re.search(r"/portal/(\d+)/article/(\d+)", loc)
        if m:
            out.append({"portal": int(m.group(1)), "id": int(m.group(2)), "url": html.unescape(loc)})
    seen, uniq = set(), []
    for a in out:
        if a["id"] not in seen:
            seen.add(a["id"])
            uniq.append(a)
    return uniq


def is_policy(title, category_path):
    hay = strip_accents(title + " | " + " / ".join(category_path))
    return bool(POLICY_RE.search(hay))


def category_path(d):
    path, node = [], d.get("full_category_info")
    while node:
        if node.get("name"):
            path.append(node["name"])
        node = node.get("sub_category")
    return path


def cmd_crawl(args):
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(CLEAN, exist_ok=True)
    arts = sitemap_articles()
    print("sitemap: %d bài (portal: %s)" % (len(arts), sorted({a["portal"] for a in arts})))
    if args.limit:
        arts = arts[: args.limit]
    nf_path = os.path.join(RAW, "_not_found.json")
    not_found = set(json.load(open(nf_path))) if os.path.exists(nf_path) and not args.refresh else set()
    queue = [a for a in arts if a["id"] not in not_found]
    known = {a["id"] for a in arts}
    if not_found:
        print("bỏ qua %d bài đã 404 ở lần trước (sitemap cũ còn liệt kê)" % len(not_found))
    fetched = cached = failed = linked = 0
    i = 0
    while i < len(queue):
        a = queue[i]
        i += 1
        path = os.path.join(RAW, "%d.json" % a["id"])
        d = None
        if os.path.exists(path) and not args.refresh:
            cached += 1
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        else:
            try:
                body = http_get(ARTICLE_API.format(id=a["id"]))
                d = json.loads(body)
                if "content" not in d:
                    raise ValueError("phản hồi không có content: " + body[:120])
                d["_source_url"] = a["url"]
                d["_portal"] = a["portal"]
                d["_via"] = a.get("via", "sitemap")
                d["_fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False)
                fetched += 1
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    not_found.add(a["id"])
                failed += 1
                print("  lỗi id=%d: %s" % (a["id"], e))
            except Exception as e:
                failed += 1
                print("  lỗi id=%d: %s" % (a["id"], e))
            time.sleep(args.delay)
        # Bài chính sách thường chỉ là trang mục lục trỏ sang bài khác không có trong sitemap: đi theo link
        # help.shopee.vn/.../article/<id> trong các bài chính sách (chỉ trong help.shopee.vn).
        if d and not args.limit and is_policy(d.get("title") or "", category_path(d)):
            for m in re.finditer(r'href="https?://help\.shopee\.vn/portal/(?:(\d+)/)?article/(\d+)[^"]*"', d.get("content", "")):
                aid = int(m.group(2))
                if aid not in known and aid not in not_found:
                    known.add(aid)
                    portal = int(m.group(1) or 4)
                    queue.append({"portal": portal, "id": aid, "via": "link:%d" % d["id"],
                                  "url": "%s/portal/%d/article/%d" % (BASE, portal, aid)})
                    linked += 1
        if i % 100 == 0:
            print("  %d/%d" % (i, len(queue)))
    with open(nf_path, "w") as f:
        json.dump(sorted(not_found), f)
    print("raw: tải mới %d, dùng lại %d, lỗi %d · thêm %d bài theo link ngoài sitemap" % (fetched, cached, failed, linked))

    # clean + chọn bài chính sách
    docs, skipped = [], 0
    for name in sorted((n for n in os.listdir(RAW) if n[0].isdigit()), key=lambda n: int(n.split(".")[0])):
        with open(os.path.join(RAW, name), encoding="utf-8") as f:
            d = json.load(f)
        cats = category_path(d)
        title = (d.get("title") or "").strip()
        if not is_policy(title, cats):
            skipped += 1
            continue
        md = html_to_markdown(d.get("content", ""))
        if len(md.strip()) < 40:
            skipped += 1
            continue
        doc = {
            "doc_id": "shopee-vn-%d" % d["id"],
            "article_id": d["id"],
            "title": title,
            "source_url": d.get("_source_url") or (BASE + "/portal/4/article/%d" % d["id"]),
            "portal": d.get("_portal"),
            "category": " / ".join(cats),
            "fetched_at": d.get("_fetched_at"),
            "content": md,
        }
        with open(os.path.join(CLEAN, "%d.md" % d["id"]), "w", encoding="utf-8") as f:
            f.write("# %s\n\n<!-- source: %s | category: %s -->\n\n%s" % (title, doc["source_url"], doc["category"], md))
        docs.append(doc)
    with open(DOCS, "w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("clean: giữ %d bài chính sách, bỏ %d bài không liên quan → %s" % (len(docs), skipped, rel(DOCS)))


# ---------------------------------------------------------------- 2. chunk
try:
    import tiktoken  # tuỳ chọn: đếm token chính xác hơn nếu đã cài
    _ENC = tiktoken.get_encoding("cl100k_base")

    def ntok(s):
        return len(_ENC.encode(s))
    TOKENIZER = "tiktoken cl100k_base"
except Exception:
    def ntok(s):
        # Ước lượng cho tiếng Việt có dấu với tokenizer kiểu BPE: ~1 token / 2,6 ký tự (tự ước tính).
        return int(math.ceil(len(s) / 2.6))
    TOKENIZER = "ước lượng len/2.6 (chưa cài tiktoken)"


def parse_blocks(md):
    """Tách Markdown thành block: heading (kèm cấp) hoặc khối nội dung (đoạn văn / cả một danh sách / cả một bảng)."""
    blocks = []
    for part in re.split(r"\n\s*\n", md):
        part = part.strip("\n")
        if not part.strip():
            continue
        m = re.match(r"^(#{1,6}) (.+)$", part.strip())
        if m and "\n" not in part.strip():
            blocks.append(("h", len(m.group(1)), m.group(2).strip()))
        elif re.match(r"^\s*(- |\d+\. |\| )", part):
            # danh sách / bảng: tách theo từng mục để có thể dừng giữa danh sách mà không cắt giữa một mục
            items, cur = [], []
            for line in part.split("\n"):
                if re.match(r"^(- |\d+\. |\| )", line) and cur:
                    items.append("\n".join(cur))
                    cur = []
                cur.append(line)
            if cur:
                items.append("\n".join(cur))
            for it in items:
                blocks.append(("t", 0, it))
        else:
            blocks.append(("t", 0, part))
    return blocks


def split_long(text, max_tok):
    """Block dài hơn max: cắt theo câu, không cắt giữa câu."""
    sents = re.split(r"(?<=[.!?;:])\s+", text)
    out, cur = [], ""
    for s in sents:
        if cur and ntok(cur + " " + s) > max_tok:
            out.append(cur)
            cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        out.append(cur)
    return out


def chunk_doc(doc, max_tok, overlap_tok, min_tok):
    path = []                 # heading path hiện tại: [(level, text)]
    units = []                # (section_path_str, text, is_list_item)
    for kind, level, text in parse_blocks(doc["content"]):
        if kind == "h":
            path = [p for p in path if p[0] < level] + [(level, text)]
            units.append((" > ".join(t for _, t in path), "#" * level + " " + text, "h"))
        else:
            sec = " > ".join(t for _, t in path)
            pieces = split_long(text, max_tok) if ntok(text) > max_tok else [text]
            for p in pieces:
                units.append((sec, p, "t"))

    chunks, cur, cur_tok = [], [], 0

    def emit():
        if not cur or all(u[2] == "h" for u in cur):
            return
        content = "\n\n".join(u[1] for u in cur)
        content = re.sub(r"\n\n(?=(- |\d+\. |\| ))", "\n", content)  # mục danh sách liền nhau
        first_sec = next((u[0] for u in cur if u[2] == "t"), cur[0][0])
        chunks.append({"content": content, "section": first_sec or doc["title"]})

    for u in units:
        t = ntok(u[1])
        new_section = u[2] == "h"
        if cur and (cur_tok + t > max_tok or (new_section and cur_tok >= min_tok)):
            emit()
            # overlap: mang các block cuối (không phải heading) sang chunk sau, chỉ khi chưa sang mục mới
            carry, ctok = [], 0
            if not new_section:
                for prev in reversed(cur):
                    if prev[2] == "h":
                        break
                    pt = ntok(prev[1])
                    if ctok + pt > overlap_tok:
                        break
                    carry.insert(0, prev)
                    ctok += pt
                # nhắc lại heading của mục để chunk sau tự hiểu ngữ cảnh
                heads = [p for p in cur if p[2] == "h"]
                if heads and (not carry or carry[0][2] != "h"):
                    carry.insert(0, heads[-1])
                    ctok += ntok(heads[-1][1])
            cur, cur_tok = carry, ctok
        cur.append(u)
        cur_tok += t
    emit()

    out = []
    for i, c in enumerate(chunks):
        out.append({
            "chunk_id": "%s-c%03d" % (doc["doc_id"], i),
            "content": c["content"],
            "title": doc["title"],
            "source_url": doc["source_url"],
            "section": c["section"],
            "category": doc["category"],
            "n_tokens": ntok(c["content"]),
        })
    return out


def cmd_chunk(args):
    if not os.path.exists(DOCS):
        sys.exit("Chưa có %s — chạy `python rag/pipeline.py crawl` trước." % rel(DOCS))
    docs = [json.loads(l) for l in open(DOCS, encoding="utf-8")]
    allc = []
    for d in docs:
        allc.extend(chunk_doc(d, args.max, args.overlap, args.min))
    with open(CHUNKS, "w", encoding="utf-8") as f:
        for c in allc:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    toks = sorted(c["n_tokens"] for c in allc) or [0]
    print("chunk: %d bài → %d chunk (max %d, overlap %d, min %d token; tokenizer: %s)"
          % (len(docs), len(allc), args.max, args.overlap, args.min, TOKENIZER))
    print("  token/chunk: min %d · trung vị %d · max %d → %s" % (toks[0], toks[len(toks) // 2], toks[-1], rel(CHUNKS)))


# ---------------------------------------------------------------- 3. embed
def load_env(path=os.path.join(ROOT, ".env")):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


EMBED_PROVIDERS = ("openrouter", "openai", "gemini")
OPENROUTER_EMBED_URL = "https://openrouter.ai/api/v1/embeddings"


def embed_config():
    """Đọc cấu hình embedding từ .env / biến môi trường. Bắt buộc đủ 4 biến, KHÔNG fallback
    (không mượn MODEL_PROVIDER / API_KEY, không có model hay số chiều mặc định)."""
    load_env()
    cfg = {k: (os.environ.get(k) or "").strip() for k in ("EMBED_PROVIDER", "EMBED_MODEL", "EMBED_DIM", "EMBED_API_KEY")}
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        sys.exit("Thiếu cấu hình embedding trong .env: %s\nCần đủ:\n  EMBED_PROVIDER=openrouter\n"
                 "  EMBED_MODEL=openai/text-embedding-3-small\n  EMBED_DIM=1536\n  EMBED_API_KEY=<OPENROUTER_API_KEY>"
                 % ", ".join(missing))
    provider = cfg["EMBED_PROVIDER"].lower()
    if provider not in EMBED_PROVIDERS:
        sys.exit("EMBED_PROVIDER=%s chưa hỗ trợ (hỗ trợ: %s)." % (provider, ", ".join(EMBED_PROVIDERS)))
    if not cfg["EMBED_DIM"].isdigit() or int(cfg["EMBED_DIM"]) <= 0:
        sys.exit("EMBED_DIM=%s không hợp lệ: cần số nguyên dương, vd 1536." % cfg["EMBED_DIM"])
    return provider, cfg["EMBED_MODEL"], cfg["EMBED_API_KEY"], int(cfg["EMBED_DIM"])


def check_vectors(vecs, n_expected, dim):
    """Dừng nếu API trả thiếu vector, sai số chiều, hoặc có giá trị null/NaN/vô cực."""
    if len(vecs) != n_expected:
        sys.exit("API trả %d vector cho %d input." % (len(vecs), n_expected))
    for i, v in enumerate(vecs):
        if not isinstance(v, list) or len(v) != dim:
            sys.exit("Vector #%d có %s chiều, cần đúng EMBED_DIM=%d." % (i, len(v) if isinstance(v, list) else "?", dim))
        if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in v):
            sys.exit("Vector #%d có giá trị null/NaN/vô cực." % i)


def post_json(url, payload, headers, retries=5):
    data = json.dumps(payload).encode("utf-8")
    for i in range(retries):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and i < retries - 1:
                wait = 2 ** i * 2
                print("  HTTP %d, thử lại sau %ds" % (e.code, wait))
                time.sleep(wait)
                continue
            raise SystemExit("Lỗi embedding API HTTP %d: %s" % (e.code, body))


def embed_batch(provider, model, key, dim, texts):
    if provider == "openrouter":
        # OpenRouter Embeddings API (định dạng giống OpenAI). Chỉ gọi OpenRouter, không gọi api.openai.com.
        r = post_json(OPENROUTER_EMBED_URL, {"model": model, "input": texts, "dimensions": dim},
                      {"Authorization": "Bearer " + key})
        if not isinstance(r, dict) or not isinstance(r.get("data"), list):
            sys.exit("OpenRouter không trả dữ liệu embedding: %s" % json.dumps(r, ensure_ascii=False)[:300])
        # OpenRouter trả tên model không kèm tiền tố nhà cung cấp (vd "text-embedding-3-small")
        if r.get("model") and r["model"] != model and model.split("/", 1)[-1] != r["model"]:
            sys.exit("OpenRouter trả model %s, khác EMBED_MODEL=%s." % (r["model"], model))
        vecs = [d.get("embedding") for d in sorted(r["data"], key=lambda d: d.get("index", 0))]
        return vecs, (r.get("usage") or {}).get("prompt_tokens", 0)
    if provider == "openai":
        payload = {"model": model, "input": texts}
        if dim:
            payload["dimensions"] = dim
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        r = post_json(base + "/embeddings", payload, {"Authorization": "Bearer " + key})
        vecs = [d["embedding"] for d in sorted(r["data"], key=lambda d: d["index"])]
        return vecs, (r.get("usage") or {}).get("prompt_tokens", 0)
    # gemini
    reqs = []
    for t in texts:
        q = {"model": "models/" + model, "content": {"parts": [{"text": t}]}, "taskType": "RETRIEVAL_DOCUMENT"}
        if dim:
            q["outputDimensionality"] = dim
        reqs.append(q)
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:batchEmbedContents" % model
    r = post_json(url, {"requests": reqs}, {"x-goog-api-key": key})
    return [e["values"] for e in r["embeddings"]], 0


def embed_text(c):
    # Đưa tiêu đề + mục vào văn bản embed để chunk ngắn vẫn mang ngữ cảnh; content lưu nguyên văn.
    return "%s\n%s\n\n%s" % (c["title"], c["section"], c["content"])


def cmd_filter(args):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import seller_filter
    seller_filter.run()


def cmd_embed(args):
    # Mặc định embed dataset Seller-only (data/shopee_policy/seller/); --dataset all = toàn bộ policy.
    base = OUT if args.dataset == "all" else os.path.join(OUT, "seller")
    CHUNKS = os.path.join(base, "chunks.jsonl")
    EMB = os.path.join(base, "embeddings.jsonl")
    EMB_META = os.path.join(base, "embeddings_meta.json")
    if not os.path.exists(CHUNKS):
        step = "chunk" if args.dataset == "all" else "filter"
        sys.exit("Chưa có %s — chạy `python rag/pipeline.py %s` trước." % (rel(CHUNKS), step))
    provider, model, key, dim = embed_config()
    chunks = [json.loads(l) for l in open(CHUNKS, encoding="utf-8")]

    # dùng lại vector đã có nếu cùng model và văn bản không đổi
    done = {}
    if os.path.exists(EMB) and os.path.exists(EMB_META):
        meta = json.load(open(EMB_META, encoding="utf-8"))
        if meta.get("model") == model and meta.get("provider") == provider and meta.get("requested_dim") == dim:
            for l in open(EMB, encoding="utf-8"):
                r = json.loads(l)
                if isinstance(r.get("embedding"), list) and len(r["embedding"]) == dim:
                    done[r["text_hash"]] = r["embedding"]

    todo = []
    for c in chunks:
        c["text_hash"] = hashlib.sha256(embed_text(c).encode("utf-8")).hexdigest()[:16]
        if c["text_hash"] not in done:
            todo.append(c)
    print("embed [%s]: %s / %s · %d chunk (%d đã có, %d cần gọi API)"
          % (args.dataset, provider, model, len(chunks), len(chunks) - len(todo), len(todo)))
    tokens = 0
    for i in range(0, len(todo), args.batch):
        part = todo[i:i + args.batch]
        vecs, t = embed_batch(provider, model, key, dim, [embed_text(c) for c in part])
        check_vectors(vecs, len(part), dim)
        tokens += t
        for c, v in zip(part, vecs):
            done[c["text_hash"]] = v
        print("  %d/%d" % (min(i + args.batch, len(todo)), len(todo)))
        time.sleep(args.wait)

    dims = set()
    with open(EMB, "w", encoding="utf-8") as f:
        for c in chunks:
            v = done[c["text_hash"]]
            dims.add(len(v))
            f.write(json.dumps({**c, "embedding": v}, ensure_ascii=False) + "\n")
    meta = {"provider": provider, "model": model, "requested_dim": dim, "dimension": sorted(dims)[0] if len(dims) == 1 else sorted(dims),
            "dataset": args.dataset, "n_chunks": len(chunks), "embedded_text": "title\\nsection\\n\\ncontent", "api_tokens_this_run": tokens,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    with open(EMB_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("  dimension %s → %s (+ %s)" % (meta["dimension"], rel(EMB), rel(EMB_META)))


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def main(argv):
    ap = argparse.ArgumentParser(description="Shopee VN policy → RAG: crawl, chunk, embed")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crawl")
    c.add_argument("--limit", type=int, default=0, help="chỉ tải N bài đầu trong sitemap (thử)")
    c.add_argument("--refresh", action="store_true", help="tải lại cả bài đã có trong raw/")
    c.add_argument("--delay", type=float, default=0.3, help="nghỉ giữa hai request (giây)")
    k = sub.add_parser("chunk")
    k.add_argument("--max", type=int, default=600)
    k.add_argument("--overlap", type=int, default=80)
    k.add_argument("--min", type=int, default=150, help="chunk đạt ngưỡng này thì sang mục mới sẽ cắt")
    e = sub.add_parser("embed")
    e.add_argument("--batch", type=int, default=64)
    e.add_argument("--wait", type=float, default=0.0)
    e.add_argument("--dataset", choices=["seller", "all"], default="seller", help="seller = sau bước filter (mặc định)")
    sub.add_parser("filter", help="lọc chunks.jsonl → dataset Seller-only (rag/seller_filter.py)")
    args = ap.parse_args(argv)
    {"crawl": cmd_crawl, "chunk": cmd_chunk, "filter": cmd_filter, "embed": cmd_embed}[args.cmd](args)


if __name__ == "__main__":
    main(sys.argv[1:])
