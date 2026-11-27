"""Bước FILTER: từ chunks.jsonl (policy) tạo dataset Seller-only. Không crawl lại, không chunk lại, không sửa nội dung.

  python rag/pipeline.py filter   → data/shopee_policy/seller/{documents.jsonl, chunks.jsonl, filter_report.md, filter_decisions.jsonl}

Cách lọc (dựa trên NỘI DUNG từng chunk, không chỉ tiêu đề):
  0. Bỏ trùng: một số ID cũ trong sitemap chuyển hướng về cùng một bài → cùng article_id, cùng chunk_id. Giữ bản đầu.
  1. Bỏ bản cũ: bài có tiêu đề "(phiên bản trước)", "(bản trước đây)", "(phiên bản ngày …)" là bản lưu trữ của một
     chính sách còn bản hiện hành trong dataset; giữ lại sẽ làm RAG trả lời theo quy định đã hết hiệu lực.
  2. Chấm từng chunk: s = số tín hiệu Người bán, b = số tín hiệu Người mua (SELLER_RE / BUYER_RE, trên section + content).
  3. Phân loại bài theo tổng tín hiệu nội dung của cả bài:
       seller  — bài viết cho Người bán (tỉ lệ s/(s+b) ≥ 0,7 và s ≥ 10, hoặc tên/danh mục nói rõ "Người bán" và tỉ lệ ≥ 0,5)
                 → giữ mọi chunk, trừ chunk chỉ nói về Người mua (s = 0, b ≥ 2).
       mixed   — bài chung có phần cho Người bán (s ≥ 4, tỉ lệ ≥ 0,25)
                 → chỉ giữ chunk thuộc mục nói về Người bán, hoặc chunk có s ≥ 2 và s ≥ b.
       out     — còn lại: bài cho Người mua, bài chung, bài không xác định rõ liên quan Người bán (quy tắc 3).
     Bài hỏi đáp viết theo góc Người mua ("Tôi …", danh mục "Mua Sắm Cùng Shopee") không được xếp mixed dù có nhắc
     "Người bán": câu trả lời hướng dẫn người mua, không phải nghĩa vụ của người bán.
  4. OVERRIDES: quyết định tay cho các bài mà luật trên xếp sai, mỗi dòng có lý do; xem filter_report.md.
  5. Bỏ chunk trùng nội dung: hai chunk có `content` giống hệt nhau (so khớp nguyên văn, không dựa vào chunk_id) thì giữ
     chunk xuất hiện đầu tiên, loại chunk sau. Ví dụ: trang 124168 "GÓI DỊCH VỤ THƯƠNG MẠI ĐIỆN TỬ" trên Shopee lặp lại
     toàn bộ thân bài hai lần → chunk c034–c065 trùng c001–c033.
"""
import collections
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "shopee_policy")
OUT = os.path.join(SRC, "seller")

SELLER_RE = re.compile(
    r"người bán|nhà bán hàng|kênh người bán|seller|gian hàng|đăng bán|\bshop\b(?! ?ee)|shop mall|"
    r"sao quả tạ|điểm phạt|phí cố định|phí thanh toán|phí dịch vụ|phí hoa hồng|doanh thu|đối soát|"
    r"chuẩn bị hàng|thời gian chuẩn bị|bàn giao (?:hàng|đơn)|tỷ lệ (?:đơn hàng )?không thành công|"
    r"tỉ lệ (?:đơn hàng )?không thành công|đăng tải sản phẩm|niêm yết", re.I)
BUYER_RE = re.compile(
    r"người mua|người nhận hàng|đơn mua|giỏ hàng|bạn đã mua|khi mua hàng|đặt hàng|shopee xu|"
    r"mã miễn phí vận chuyển|nhận hàng", re.I)
SUPERSEDED_RE = re.compile(r"\((?:phiên bản|bản)\s+(?:trước|ngày)[^)]*\)?|bản trước đây", re.I)
SELLER_SECTION_RE = re.compile(r"người bán|nhà bán hàng|bán hàng|gian hàng|đăng bán|seller|\bshop\b(?! ?ee)|"
                               r"\bphí\b|vi phạm|thành viên", re.I)
BUYER_SECTION_RE = re.compile(r"(?:của|dành cho) người mua|người tiêu dùng", re.I)
BUYER_FAQ_RE = re.compile(r"\btôi\b", re.I)

# Quyết định tay sau khi đọc nội dung (article_id → (class, lý do)). Ưu tiên hơn luật tự động.
OVERRIDES = {
    77247: ("seller", "danh sách sản phẩm cấm/hạn chế là quy định đăng bán; ít chữ 'Người bán' nhưng áp dụng trực tiếp cho Seller"),
    77265: ("seller", "quy trình tranh chấp/khiếu nại mà Người bán là một bên; các bước của hai bên đan xen, không tách được"),
    166085: ("mixed", "chính sách mã ưu đãi cho người dùng; chỉ Mục 10–12 và các câu làm rõ áp dụng cho Người bán"),
    197649: ("seller", "livestream bán sản phẩm của Người bán; quy định quyền/nghĩa vụ Người bán với Người Sáng Tạo"),
    77244: ("out", "chính sách bảo mật áp dụng cho mọi người dùng"),
    185399: ("out", "điều khoản Shopee AI cho người dùng chung"),
    159769: ("out", "điều khoản chatbot cho người dùng chung"),
    171475: ("out", "dịch vụ lắp đặt giữa Người mua và Nhà cung cấp; phần nhắc Người bán không nêu nghĩa vụ cụ thể"),
    79085: ("out", "hỏi đáp hướng dẫn Người mua ('Bạn không cần ra bưu cục')"),
    188931: ("out", "hỏi đáp trả hàng viết cho Người mua ('bạn có thể gửi yêu cầu')"),
    189473: ("out", "hỏi đáp thời gian nhận tiền hoàn của Người mua"),
    79518: ("out", "hỏi đáp phương thức vận chuyển cho Người mua"),
    195831: ("out", "giới thiệu phương thức Hỏa Tốc - Ưu Tiên cho Người mua"),
    118122: ("seller", "khoản vay dành riêng cho Người bán: điều kiện, phí, nghĩa vụ trả nợ của Người bán"),
    79086: ("out", "hỏi đáp cho Người mua khi Shop chưa xác nhận đơn"),
    121722: ("out", "hướng dẫn Người mua tố cáo Shop gian lận"),
    # Chốt dataset cuối
    77501: ("out", "chương trình giảm chi phí vận chuyển từ tháng 8/2020, policy cũ"),
    183825: ("out", "bản trước của Tiếp thị liên kết – Người bán tham gia: bài 183831 ghi 'đăng tải ngày 30/06/2026 … "
                    "phiên bản trước đây xem TẠI ĐÂY' và trỏ về 183825"),
    125582: ("out", "Shopee Video: điều khoản cho người dùng/nhà sáng tạo, không nhắc Người bán"),
    124185: ("out", "Shopee Video: tiêu chuẩn cộng đồng chung, không nhắc Người bán"),
    185946: ("out", "Shopee Video: quy định đăng video cho người dùng, chỉ 1 lần nhắc Người bán (cấm chia sẻ liên hệ)"),
    138173: ("out", "Shopee Video: quy định nội dung video chung, không nhắc Người bán"),
}


def nfc(t):
    return unicodedata.normalize("NFC", t or "")


def load_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def classify_doc(doc, chunks):
    s = sum(c["_s"] for c in chunks)
    b = sum(c["_b"] for c in chunks)
    ratio = s / (s + b) if s + b else 0.0
    title, cat = nfc(doc["title"]), nfc(doc["category"])
    names = (title + " | " + cat).lower()
    buyer_faq = bool(BUYER_FAQ_RE.search(title)) or cat.startswith("Mua Sắm Cùng Shopee")
    if doc["article_id"] in OVERRIDES:
        cls, why = OVERRIDES[doc["article_id"]]
        return cls, "override: " + why, s, b, ratio
    if buyer_faq and s < 10:
        return "out", "hỏi đáp góc Người mua (s=%d, b=%d)" % (s, b), s, b, ratio
    if (ratio >= 0.7 and s >= 10) or ("người bán" in names and ratio >= 0.5 and s >= 10):
        return "seller", "nội dung chủ yếu nói về Người bán (s=%d, b=%d)" % (s, b), s, b, ratio
    if s >= 4 and ratio >= 0.25 and not buyer_faq:
        return "mixed", "có phần cho Người bán (s=%d, b=%d)" % (s, b), s, b, ratio
    if buyer_faq:
        return "out", "hỏi đáp góc Người mua (s=%d, b=%d)" % (s, b), s, b, ratio
    if s == 0:
        return "out", "không nhắc tới Người bán (b=%d)" % b, s, b, ratio
    return "out", "không xác định rõ liên quan Người bán (s=%d, b=%d)" % (s, b), s, b, ratio


def keep_chunk(cls, c):
    if cls == "seller":
        return not (c["_s"] == 0 and c["_b"] >= 2)
    if cls == "mixed":
        sec = nfc(c["section"])
        by_section = bool(SELLER_SECTION_RE.search(sec)) and not BUYER_SECTION_RE.search(sec)
        return by_section or (c["_s"] >= 2 and c["_s"] >= c["_b"])
    return False


def fill_sections(cs, keep):
    """Bài mixed: trong một mục cấp cao nhất, nếu đã giữ ≥ một nửa số chunk thì giữ cả mục, tránh 'lỗ' giữa điều khoản."""
    top = lambda c: nfc(c["section"]).split(" > ")[0]
    kept_ids = {c["chunk_id"] for c in keep}
    total, kept = collections.Counter(), collections.Counter()
    for c in cs:
        total[top(c)] += 1
        kept[top(c)] += c["chunk_id"] in kept_ids
    return [c for c in cs if c["chunk_id"] in kept_ids
            or (kept[top(c)] * 2 >= total[top(c)] and not BUYER_SECTION_RE.search(top(c)))]


def dedupe_content(chunks):
    """Giữ chunk đầu tiên của mỗi `content` (so khớp nguyên văn), loại các chunk sau. Không sửa chunk được giữ.
    Trả về (kept, removed) với removed = [(chunk_id bị loại, chunk_id được giữ có cùng content)]."""
    first, kept, removed = {}, [], []
    for c in chunks:
        if c["content"] in first:
            removed.append((c["chunk_id"], first[c["content"]]))
        else:
            first[c["content"]] = c["chunk_id"]
            kept.append(c)
    return kept, removed


def run():
    for name in ("documents.jsonl", "chunks.jsonl"):
        if not os.path.exists(os.path.join(SRC, name)):
            raise SystemExit("Không có data/shopee_policy/%s (dữ liệu trung gian đã được dọn sau khi chốt dataset). "
                             "Dataset Seller-only đã có ở data/shopee_policy/seller/. Muốn lọc lại từ đầu: chạy "
                             "`python rag/pipeline.py crawl` rồi `chunk` rồi `filter`." % name)
    docs_all = load_jsonl(os.path.join(SRC, "documents.jsonl"))
    chunks_all = load_jsonl(os.path.join(SRC, "chunks.jsonl"))
    n_docs_in, n_chunks_in = len(docs_all), len(chunks_all)

    docs, seen = [], set()
    for d in docs_all:
        if d["article_id"] not in seen:
            seen.add(d["article_id"])
            docs.append(d)
    chunks, seen = [], set()
    for c in chunks_all:
        if c["chunk_id"] not in seen:
            seen.add(c["chunk_id"])
            chunks.append(c)
    by_doc = collections.defaultdict(list)
    for c in chunks:
        hay = nfc(c["section"] + "\n" + c["content"])
        c["_s"] = len(SELLER_RE.findall(hay))
        c["_b"] = len(BUYER_RE.findall(hay))
        by_doc[c["chunk_id"].rsplit("-c", 1)[0]].append(c)

    decisions, kept_docs, kept_chunks = [], [], []
    for d in docs:
        cs = by_doc.get(d["doc_id"], [])
        if SUPERSEDED_RE.search(nfc(d["title"])) and d["article_id"] not in OVERRIDES:
            cls, why, s, b, ratio = "out", "bản cũ / bản lưu trữ của chính sách", 0, 0, 0.0
        else:
            cls, why, s, b, ratio = classify_doc(d, cs)
        keep = [c for c in cs if keep_chunk(cls, c)]
        if cls == "mixed":
            keep = fill_sections(cs, keep)
        if cls != "out" and not keep:
            why += "; không còn chunk nào sau lọc"
        decisions.append({"article_id": d["article_id"], "title": d["title"], "category": d["category"],
                          "class": cls, "reason": why, "seller_hits": s, "buyer_hits": b,
                          "chunks_before": len(cs), "chunks_after": len(keep), "source_url": d["source_url"]})
        if keep:
            kept_docs.append(d)
            for c in keep:
                kept_chunks.append({k: v for k, v in c.items() if not k.startswith("_")})

    # 5. bỏ chunk trùng nội dung trên toàn dataset, rồi cập nhật số chunk giữ của từng bài
    kept_chunks, removed = dedupe_content(kept_chunks)
    if removed:
        per_doc = collections.Counter(cid.rsplit("-c", 1)[0] for cid, _ in removed)
        left = collections.Counter(c["chunk_id"].rsplit("-c", 1)[0] for c in kept_chunks)
        for r in decisions:
            n = per_doc.get("shopee-vn-%d" % r["article_id"], 0)
            if n:
                r["chunks_after"] = left.get("shopee-vn-%d" % r["article_id"], 0)
                r["reason"] += "; bỏ %d chunk trùng nội dung với chunk trước đó" % n
        kept_ids = {c["chunk_id"].rsplit("-c", 1)[0] for c in kept_chunks}
        kept_docs = [d for d in kept_docs if d["doc_id"] in kept_ids]

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "documents.jsonl"), "w", encoding="utf-8") as f:
        for d in kept_docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(os.path.join(OUT, "chunks.jsonl"), "w", encoding="utf-8") as f:
        for c in kept_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(os.path.join(OUT, "filter_decisions.jsonl"), "w", encoding="utf-8") as f:
        for r in decisions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    write_report(decisions, n_docs_in, n_chunks_in, len(docs), len(chunks), kept_docs, kept_chunks, len(removed))

    cnt = collections.Counter(r["class"] for r in decisions)
    print("filter: tài liệu %d (%d sau bỏ trùng) → %d · chunk %d (%d sau bỏ trùng) → %d (đã bỏ %d chunk trùng nội dung)"
          % (n_docs_in, len(docs), len(kept_docs), n_chunks_in, len(chunks), len(kept_chunks), len(removed)))
    print("  seller %d · mixed %d · out %d → data/shopee_policy/seller/" % (cnt["seller"], cnt["mixed"], cnt["out"]))


def write_report(dec, nd_in, nc_in, nd_u, nc_u, kd, kc, n_dup_content=0):
    L = ["# Seller-only filter: báo cáo", "",
         "| | Tài liệu | Chunk |", "|---|---:|---:|",
         "| Policy dataset (documents.jsonl / chunks.jsonl) | %d | %d |" % (nd_in, nc_in),
         "| Sau bỏ trùng (ID cũ chuyển hướng về cùng bài) | %d | %d |" % (nd_u, nc_u),
         "| Chunk trùng nội dung đã bỏ (giữ bản đầu) | | %d |" % n_dup_content,
         "| **Seller-only** | **%d** | **%d** |" % (len(kd), len(kc)), ""]
    for cls, head in (("seller", "Giữ nguyên bài (viết cho Người bán)"), ("mixed", "Giữ một phần (bài chung, chỉ lấy mục cho Người bán)"),
                      ("out", "Loại")):
        rows = sorted((r for r in dec if r["class"] == cls), key=lambda r: -r["chunks_before"])
        L += ["## %s: %d bài" % (head, len(rows)), "", "| ID | Tiêu đề | Chunk giữ/tổng | Lý do |", "|---|---|---|---|"]
        for r in rows:
            L.append("| [%d](%s) | %s | %d/%d | %s |" % (r["article_id"], r["source_url"], r["title"].replace("|", "/"),
                                                     r["chunks_after"], r["chunks_before"], r["reason"]))
        L.append("")
    with open(os.path.join(OUT, "filter_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    run()
