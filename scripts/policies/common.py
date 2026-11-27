"""Hàm dùng chung cho pipeline chính sách (crawl → clean → chunk → embed).
Đường dẫn theo sàn lấy từ codebase/policy_paths.py (vd tiktok → data/tiktok_shop/policies/)."""
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "codebase"))
from policy_paths import paths  # noqa: E402,F401  (các script dùng: paths(platform)["chunks"]…)

HERE = os.path.dirname(os.path.abspath(__file__))
POLICY_TYPES = {"fee", "voucher", "ads", "return_refund", "settlement"}


def read_urls(platform):
    """scripts/policies/urls_<platform>.txt → [(doc_id, policy_type, url)]."""
    rows = []
    with open(os.path.join(HERE, "urls_%s.txt" % platform), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ptype, url = line.split(None, 1)  # tab hoặc dấu cách đều được
            if ptype not in POLICY_TYPES:
                raise ValueError("policy_type lạ: %r (dòng %s)" % (ptype, line))
            rows.append((doc_id(platform, url), ptype, url.strip()))
    return rows


def doc_id(platform, url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if q.get("knowledge_id"):
        return "%s-%s" % (platform, q["knowledge_id"][0])
    slug = re.sub(r"[^a-z0-9]+", "-", urllib.parse.urlparse(url).path.lower()).strip("-")
    return "%s-%s" % (platform, slug[-60:])
