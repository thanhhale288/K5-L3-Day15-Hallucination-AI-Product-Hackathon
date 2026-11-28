#!/usr/bin/env python3
"""Tính lại bảng chi phí khi chỉ đổi GIÁ, không gọi lại model (TH-9).

  python cost/reprice.py cost/simulate-1.csv --rate-from eval/run-2.csv
  → cost/simulate-1-gia-moi-summary.md

Token đã đo thật trong cost/simulate-N.csv (khung `simulate`). Script này đọc lại các dòng đó, lấy giá / số người
dùng / persona hiện tại trong cost/personas.yaml, rồi gọi đúng hàm `summarize` của khung cost/simulate.py
(không sửa khung, không tính tay). Dùng khi giá model đổi mà không cần chạy lại 50 phiên.
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cost"))
import simulate as sim  # noqa: E402


def load_rows(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r = dict(r)
            for k in ("turns", "model_calls", "tool_calls", "tokens_in", "tokens_out"):
                r[k] = int(float(r[k] or 0))
            r["latency_s"] = float(r["latency_s"] or 0)
            r["by_model"] = json.loads(r.get("tokens_by_model") or "{}")
            rows.append(r)
    return rows


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    src = argv[0]
    rate_from = argv[argv.index("--rate-from") + 1] if "--rate-from" in argv else None
    cfg, warn = sim.load_config()
    for w in warn:
        print("⚠️ " + w)
    rows = load_rows(src if os.path.isabs(src) else os.path.join(ROOT, src))
    graded, other = sim.pick_rate(sim.measured_models(rows), rate_from)
    base = os.path.splitext(os.path.basename(src))[0]
    run_id = rows[0]["run_id"] if rows else base
    out = os.path.join(ROOT, "cost", base + "-gia-moi-summary.md")
    lines = [
        "# Tính lại giá cho %s" % run_id,
        "",
        "Do `python cost/reprice.py %s%s` sinh ra — không sửa tay. Token lấy nguyên từ `%s` (đo thật); "
        "giá, số người dùng và persona lấy từ `cost/personas.yaml` hiện tại; bảng tính bằng hàm `summarize` của khung."
        % (os.path.relpath(src, ROOT) if os.path.isabs(src) else src, " --rate-from " + rate_from if rate_from else "",
           os.path.basename(src)),
        "",
    ] + sim.summarize(cfg, rows, graded, other)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\nĐã ghi " + os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main(sys.argv[1:])
