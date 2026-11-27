"""B3–B4 · Markdown sạch → data/<thư mục sàn>/policies/chunks.jsonl (chuẩn ở crawl-spec.md §B3, §B4). Chỉ thư viện chuẩn.

Quy tắc: cắt theo heading trước · mục tiêu ~400 token, trần 800 · section < 100 token gộp với section anh em ·
đoạn "lưu ý / trừ / không áp dụng" dính vào đoạn quy tắc đứng trước · không cắt ngang câu / hàng bảng ·
chỉ chồng 1 câu khi buộc phải tách giữa một đoạn dài.

    python scripts/policies/chunk.py [--platform tiktok] [--stats]
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import chunk_effective_date  # noqa: E402
from common import paths  # noqa: E402

CHUNKER_VERSION = "v2-structure-400"  # v2: tách block theo dòng trước, hàng bảng không bị cắt theo câu
TARGET, MAX_TOK, MIN_TOK = 400, 800, 100
OVERLAP_SENTENCES = 1
PLATFORM_NAME = {"tiktok": "TikTok Shop", "shopee": "Shopee", "lazada": "Lazada"}

HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
EXCEPTION = re.compile(r"^\W*(lưu ý|chú ý|trừ|ngoại trừ|không áp dụng|tuy nhiên|ngoại lệ|trường hợp ngoại lệ)", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?;:])\s+(?=[A-ZÀ-Ỹ0-9\"“(])")
NUMBER = re.compile(r"\d+([.,]\d+)?\s*(%|đ|₫|vnđ|vnd|ngày|giờ)", re.I)


def tokens(text):
    """Ước lượng token = số từ × 1.3 *(tự ước tính, chỉ để cắt — token tính tiền lấy từ usage API)*."""
    return int(len(text.split()) * 1.3) + 1


def sections(md):
    """Markdown → [(section_path, [block, …])]. Block = đoạn văn, hoặc cả cụm list / hàng bảng liền nhau."""
    out, stack, blocks, buf = [], [], [], []  # stack: [(cấp heading, tiêu đề)]

    def flush_buf():
        if buf:
            blocks.append("\n".join(buf).strip())
            buf.clear()

    def flush_section():
        flush_buf()
        if any(b for b in blocks):
            out.append(([t for _, t in stack], [b for b in blocks if b]))
        blocks.clear()

    prev_list = False
    for line in md.splitlines():
        m = HEADING.match(line)
        if m:
            flush_section()
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2).replace("**", "").strip()))
            prev_list = False
            continue
        if not line.strip():
            if not prev_list:
                flush_buf()
            continue
        is_list = bool(LIST_ITEM.match(line))
        if is_list != prev_list and buf and not (prev_list and line.startswith("  ")):
            flush_buf()
        buf.append(line.rstrip())
        prev_list = is_list or (prev_list and line.startswith("  "))
    flush_section()
    return out


def attach_exceptions(blocks):
    """Đoạn ngoại lệ không đứng một mình: dính vào đoạn quy tắc ngay trước nó."""
    out = []
    for b in blocks:
        if out and EXCEPTION.match(b):
            out[-1] = out[-1] + "\n" + b
        else:
            out.append(b)
    return out


def split_long_block(block):
    """Block > MAX_TOK → các mảnh ≤ MAX_TOK. List / bảng tách theo dòng, văn xuôi theo câu (chồng 1 câu)."""
    units = []  # (đoạn, là_văn_xuôi)
    for line in block.splitlines():
        if LIST_ITEM.match(line) or line.startswith("  "):
            units.append((line, False))  # hàng bảng / mục list giữ nguyên, đã tự mang tên cột
        else:
            units.extend((s, True) for s in SENT_SPLIT.split(line) if s.strip())
    pieces, cur = [], []
    for u, prose in units:
        if cur and tokens("\n".join(t for t, _ in cur) + "\n" + u) > TARGET:
            pieces.append("\n".join(t for t, _ in cur))
            # chỉ chồng câu văn xuôi; hàng bảng không cần chồng
            cur = cur[-OVERLAP_SENTENCES:] if cur[-1][1] and prose else []
        cur.append((u, prose))
    if cur:
        pieces.append("\n".join(t for t, _ in cur))
    return pieces


def pack(blocks):
    """Gộp block liền nhau tới ~TARGET token, không vượt MAX_TOK."""
    if tokens("\n\n".join(blocks)) <= MAX_TOK:
        return ["\n\n".join(blocks)]
    units = []
    for b in blocks:
        units.extend(split_long_block(b) if tokens(b) > MAX_TOK else [b])
    out, cur = [], []
    for u in units:
        if cur and tokens("\n\n".join(cur + [u])) > TARGET:
            out.append("\n\n".join(cur))
            cur = []
        cur.append(u)
    if cur:
        out.append("\n\n".join(cur))
    return out


def merge_small(units):
    """units: [(path, text)]. Mảnh < MIN_TOK gộp với mảnh kề cùng heading cha nếu tổng ≤ MAX_TOK."""
    def label(rest):
        return ("**%s**\n" % " > ".join(rest)) if rest else ""

    out = []  # [(path, text, đã gắn nhãn heading con chưa)]
    for path, text in units:
        if out:
            ppath, ptext, labeled = out[-1]
            same_parent = ppath[:-1] == path[:-1] or ppath == path[:-1] or path == ppath[:-1]
            small = tokens(text) < MIN_TOK or tokens(ptext) < MIN_TOK
            if same_parent and small and tokens(ptext + text) <= MAX_TOK:
                common = []
                for a, b in zip(ppath, path):
                    if a != b:
                        break
                    common.append(a)
                if not labeled:  # nhãn ghi đủ đường dẫn heading để không mất ngữ cảnh khi gộp tiếp
                    ptext = label(ppath) + ptext
                out[-1] = (common, ptext + "\n\n" + label(path) + text, True)
                continue
        out.append((path, text, False))
    return [(p, t) for p, t, _ in out]


def chunk_doc(doc, md):
    lines = md.splitlines()
    if lines and lines[0].startswith("# "):  # H1 = tiêu đề tài liệu, đã có trong context_header
        md = "\n".join(lines[1:])
    units = []
    for path, blocks in sections(md):
        for text in pack(attach_exceptions(blocks)):
            units.append((path, text))
    chunks = []
    for i, (path, text) in enumerate(merge_small(units), 1):
        full_path = [doc["title"]] + path
        # bài không có ngày hiệu lực chung → lấy ngày nêu trong chính chunk (luật chặt, xem clean.chunk_effective_date)
        eff = doc.get("effective_date") or chunk_effective_date(text)[0] or ""
        upd = doc.get("updated_at") or ""
        header = "[%s · %s%s]" % (PLATFORM_NAME.get(doc["platform"], doc["platform"]), " > ".join(full_path),
                                  " · cập nhật %s" % upd if upd else "")
        chunks.append({
            "chunk_id": "%s#%03d" % (doc["doc_id"], i), "doc_id": doc["doc_id"], "platform": doc["platform"],
            "policy_type": doc["policy_type"], "section_path": full_path, "text": text, "context_header": header,
            "token_count": tokens(header + "\n" + text), "has_table": "|" in text and ":" in text,
            "has_numbers": bool(NUMBER.search(text)), "effective_date": eff or None, "updated_at": upd or None,
            "url": doc["url"],
            "fetched_at": doc.get("fetched_at") or None, "content_hash": doc["content_hash"],
            "chunker_version": CHUNKER_VERSION,
        })
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="tiktok")
    ap.add_argument("--stats", action="store_true", help="in thống kê + 3 chunk mẫu")
    a = ap.parse_args()
    P = paths(a.platform)
    with open(P["manifest"], encoding="utf-8") as f:
        docs = list(csv.DictReader(f))
    all_chunks = []
    for d in docs:
        path = os.path.join(P["clean"], d["doc_id"] + ".md")
        if not os.path.exists(path):
            print("thiếu file sạch:", d["doc_id"])
            continue
        with open(path, encoding="utf-8") as f:
            all_chunks.extend(chunk_doc(d, f.read()))
    with open(P["chunks"], "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    toks = [c["token_count"] for c in all_chunks] or [0]
    print("%d tài liệu → %d chunk · token min/median/max = %d/%d/%d · có bảng %d · vượt trần %d → %s" % (
        len(docs), len(all_chunks), min(toks), statistics.median(toks), max(toks),
        sum(c["has_table"] for c in all_chunks), sum(t > MAX_TOK for t in toks), P["chunks"]))
    if a.stats:
        for c in all_chunks[:3]:
            print("\n---", c["chunk_id"], c["token_count"], "token\n" + c["context_header"] + "\n" + c["text"][:600])


if __name__ == "__main__":
    main()
