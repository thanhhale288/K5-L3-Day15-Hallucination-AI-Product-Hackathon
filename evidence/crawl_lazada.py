"""Lazada review + public seller policy crawl per crawl-spec.md (VN, 2026-11-27)."""
from __future__ import annotations

import base64
import argparse
import csv
import hashlib
import html
import json
import re
import unicodedata
import urllib.request
import zlib
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

from google_play_scraper import Sort, app, reviews

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "com.sc.lazada"
PLAY_URL = "https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN"
NOW = datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")
POLICIES = [
    ("lazada-phi-co-dinh-lazmall", "fee", "Tỷ lệ phần trăm phí cố định theo ngành hàng dành cho nhà bán hàng LazMall", "https://sellercenter.lazada.vn/helpcenter/s/faq/knowledge?categoryId=1000028699&m_station=faq&questionId=1000149707", "2026-06-04"),
    ("lazada-hoan-tra-chi-hoan-tien", "return_refund", "[Trả hàng cho Nhà bán hàng] Quy trình mới: Chỉ hoàn tiền", "https://sellercenter.lazada.vn/helpcenter/s/faq/knowledge?categoryId=1000028676&flag=tempWebview&hybrid=1&language=vi&m_station=BuyerHelp&questionId=1000149692", "null"),
    ("lazada-ly-do-chua-nhan-thanh-toan", "settlement", "Các lý do chưa nhận thanh toán", "https://sellercenter.lazada.vn/helpcenter/s/faq/knowledge?categoryId=1000028698&flag=tempWebview&hybrid=1&language=vi&m_station=BuyerHelp&questionId=1000149640", "null"),
    ("lazada-dieu-khoan-nha-ban-hang-2026-09", "fee", "Điều khoản dịch vụ Nhà Bán Hàng (Hiệu lực từ 29/09/2026)", "https://sellercenter.lazada.vn/helpcenter/s/faq/knowledge?categoryId=1000028750&m_station=faq&questionId=1000159631", "2026-09-29"),
]

def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", html.unescape(text))
    return re.sub(r"\s+", " ", text).strip()

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip: self.skip -= 1
        elif tag in ("p", "li", "h1", "h2", "h3", "h4", "tr", "br"): self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip and data.strip(): self.parts.append(data.strip())

def extract_page(url: str) -> tuple[str, str]:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; research crawl)"})
    raw=urllib.request.urlopen(req,timeout=30).read()
    source=raw.decode("utf-8","replace")
    title_match=re.search(r"<title[^>]*>(.*?)</title>",source,re.I|re.S)
    title=clean_text(title_match.group(1)) if title_match else ""
    # Seller Center stores its server state as a base64/zlib JSON schema.
    match=re.search(r"schema:\s*'([A-Za-z0-9+/=]+)'",source)
    if match:
        try:
            payload=zlib.decompress(base64.b64decode(match.group(1))).decode("utf-8","replace")
            obj=json.loads(payload)
            strings=[]
            def walk(v):
                if isinstance(v,dict):
                    for x in v.values(): walk(x)
                elif isinstance(v,list):
                    for x in v: walk(x)
                elif isinstance(v,str):
                    s=clean_text(v)
                    if len(s)>1 and not s.startswith(("http://","https://")): strings.append(s)
            walk(obj)
            # Keep rendered text-like values, remove script/style and repeated boilerplate.
            out=[]; seen=set()
            for s in strings:
                if s not in seen and not re.search(r"function\s*\(|^\{.*\}$",s): out.append(s); seen.add(s)
            text="\n".join(out)
            if len(text)>300: return title, text
        except Exception:
            pass
    parser=TextExtractor(); parser.feed(source)
    return title, clean_text("\n".join(parser.parts))

def reviews_crawl():
    summary_path=ROOT/"data/lazada/reviews/lazada_crawl_summary.json"
    if summary_path.exists():
        previous=json.loads(summary_path.read_text(encoding="utf-8"))
        if str(previous.get("crawled_at", "")).startswith(NOW[:10]):
            raise SystemExit("Đã có lượt crawl Lazada hôm nay; không crawl lại để tránh đổi mẫu. Dùng --policies nếu chỉ cập nhật manifest.")
    raw, _token = reviews(APP_ID,lang="vi",country="vn",sort=Sort.NEWEST,count=300,filter_score_with=None)
    # Never persist author name/image or the original review ID.
    raw_dir=ROOT/"data/lazada/reviews"; raw_dir.mkdir(parents=True,exist_ok=True)
    rows=[]; seen_ids=set(); seen_text=set(); excluded=0; dup=0
    for r in raw:
        key=hashlib.sha256(str(r["reviewId"]).encode()).hexdigest()[:12]
        content=clean_text(r.get("content") or "")
        duplicate_text=(APP_ID,content.casefold())
        if key in seen_ids or duplicate_text in seen_text: dup+=1; continue
        seen_ids.add(key); seen_text.add(duplicate_text)
        at=r.get("at")
        if at and at.tzinfo is None: at=at.replace(tzinfo=timezone.utc)
        review_at=at.astimezone(timezone(timedelta(hours=7))).isoformat(timespec="seconds") if at else ""
        reply=r.get("repliedAt")
        if reply and reply.tzinfo is None: reply=reply.replace(tzinfo=timezone.utc)
        lag=round((reply-at).total_seconds()/3600,2) if reply and at else ""
        content=re.sub(r"0\d{9,10}","[SĐT]",content)
        content=re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}","[EMAIL]",content,flags=re.I)
        content=re.sub(r"\b\d{10,}\b","[MÃ]",content)
        content=re.sub(r"https?://\S+","[LINK]",content)
        short=len(content)<10
        excluded += int(short)
        rows.append({"review_key":key,"platform":"lazada","app_id":APP_ID,"score":r.get("score"),"content":content,"content_len":len(content),"thumbs_up":r.get("thumbsUpCount",0),"app_version":r.get("appVersion") or r.get("reviewCreatedVersion") or "","review_at":review_at,"has_reply":bool(r.get("replyContent")),"reply_lag_h":lag,"lang":"vi","country":"vn","sort":"newest","crawled_at":NOW,"lib_version":"1.2.7","excluded_short":short})
    path=ROOT/"data/lazada/reviews/reviews_clean.csv"; path.parent.mkdir(parents=True,exist_ok=True)
    cols=list(rows[0]) if rows else []
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)
    meta=app(APP_ID,lang="vi",country="vn")
    (raw_dir/"raw-lazada-app.json").write_text(json.dumps({k:meta.get(k) for k in ("title","score","ratings","reviews","installs","version","updated")},ensure_ascii=False,default=str),encoding="utf-8")
    valid=[x for x in rows if not x["excluded_short"]]
    counts={"fetched":len(raw),"deduped_rows":len(rows),"duplicate_removed":dup,"excluded_short":excluded,"sample_n":len(valid),"score_1_2_n":sum(1 for x in valid if x["score"] in (1,2)),"min_review_at":min((x["review_at"] for x in valid if x["review_at"]),default=""),"max_review_at":max((x["review_at"] for x in valid if x["review_at"]),default=""),"app_title":meta.get("title"),"app_score":meta.get("score"),"app_ratings":meta.get("ratings"),"app_reviews":meta.get("reviews"),"app_version":meta.get("version"),"crawled_at":NOW,"app_url":PLAY_URL}
    summary_path.write_text(json.dumps(counts,ensure_ascii=False,indent=2),encoding="utf-8")
    return counts

def policy_crawl():
    data_dir=ROOT/"data/lazada/policies"; data_dir.mkdir(parents=True,exist_ok=True)
    manifest=[]; chunks=[]
    for doc_id,kind,expected_title,url,effective in POLICIES:
        title,text=extract_page(url)
        (data_dir/f"raw-{doc_id}.html").write_text(urllib.request.urlopen(url,timeout=30).read().decode("utf-8","replace"),encoding="utf-8")
        # The public SPA returns its application shell but no article body without its runtime API.
        # Do not hash or chunk the shell as if it were policy text.
        is_article=(expected_title.casefold() in text.casefold() and len(text)>600 and "queryKnowledgeDetail" not in text)
        digest=hashlib.sha256(unicodedata.normalize("NFC",text).encode("utf-8")).hexdigest() if is_article else ""
        manifest.append({"doc_id":doc_id,"platform":"lazada","title":expected_title,"url":url,"policy_type":kind,"effective_date":effective,"fetched_at":NOW[:10],"content_hash":digest})
        if is_article:
            paragraphs=[p.strip() for p in re.split(r"\n+",text) if p.strip()]
            body="\n".join(paragraphs)
            chunks.append({"chunk_id":f"{doc_id}#001","doc_id":doc_id,"platform":"lazada","policy_type":kind,"section_path":[expected_title],"text":body,"context_header":f"[Lazada · {expected_title} · hiệu lực {effective}]" if effective!="null" else f"[Lazada · {expected_title}]","token_count":len(body.split()),"has_table":"|" in body,"has_numbers":bool(re.search(r"\d",body)),"effective_date":effective,"url":url,"fetched_at":NOW[:10],"content_hash":digest,"chunker_version":"v1-structure-400"})
    with (data_dir/"manifest.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(manifest[0])); w.writeheader(); w.writerows(manifest)
    with (data_dir/"chunks.jsonl").open("w",encoding="utf-8") as f:
        for row in chunks: f.write(json.dumps(row,ensure_ascii=False)+"\n")
    return {"documents":len(manifest),"chunks":len(chunks),"body_chars":[len(c["text"]) for c in chunks]}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reviews",action="store_true",help="crawl một lượt 300 review mới nhất; chỉ chạy một lần/ngày")
    mode.add_argument("--policies",action="store_true",help="thử lấy các trang chính sách đã liệt kê trong manifest")
    args=parser.parse_args()
    result=reviews_crawl() if args.reviews else policy_crawl()
    print(json.dumps(result,ensure_ascii=True,indent=2))
