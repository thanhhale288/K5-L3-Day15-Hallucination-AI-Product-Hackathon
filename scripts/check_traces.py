"""TH-8: kiểm trace có ghi ĐỦ để đọc lỗi lượt 1 / lượt 2 và tính metric phụ (spec.md §7). Chỉ thư viện chuẩn.

    python scripts/check_traces.py traces/run-1.jsonl [--csv eval/run-1.csv]
    python scripts/check_traces.py traces/run-try.jsonl
    python scripts/check_traces.py traces/api/2026-11-28.jsonl

Không sửa trace (traces/* đã chạy là bằng chứng, AGENTS.md). Thoát mã 1 nếu có LỖI; CẢNH BÁO không làm fail.

Mỗi câu (case) phải có:
  L1 sự kiện "final" (bộ chạy / API ghi) với output là JSON AgentResult / SessionResult đúng hợp đồng H4
  L2 trace_id trong output = mã câu (để mở đúng trace của một câu trượt)
  L3 mỗi lần gọi model: có tên model, token là số nguyên ≥ 0; model thật thì token > 0 (token lấy từ usage)
  L4 mỗi lần gọi công cụ: tên có trong codebase/tools.py, có input và output, không lỗi
  L5 có ghi chú "kế hoạch" (note) khi model được gọi, trừ câu bị từ chối ở bước lọc bằng code
  L6 rule_id trong output có trong output của lookup_fee_rule (trace rút gọn 300 ký tự → chỉ cảnh báo)
  L7 khớp file lượt (--csv): số lần gọi model / công cụ / token của từng câu = đếm từ trace
In thêm metric phụ đọc được từ trace: số lượt công cụ trung bình / câu, tỉ lệ tự sửa thành công, tỉ lệ fallback.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "codebase"))
MOCK_MODELS = {"fake", "mock", ""}


def tool_names():
    import tools  # noqa: F401  (nạp để @tool đăng ký)
    from tracing import TOOLS
    return set(TOOLS)


def load(path):
    cases, header = OrderedDict(), None
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except ValueError:
                cases.setdefault("?", []).append({"kind": "broken", "line": n})
                continue
            if e.get("kind") == "bench":
                header = e
                continue
            cases.setdefault(str(e.get("case")), []).append(e)
    return header, cases


def check_case(cid, events, names):
    import schema
    err, warn, info = [], [], {"decision": None, "fix": False, "fallback": False, "verify_err": False}
    if any(e["kind"] == "broken" for e in events):
        err.append("có dòng trace không phải JSON")
    models = [e for e in events if e["kind"] == "model"]
    tools_ = [e for e in events if e["kind"] == "tool"]
    notes = [str(e.get("text", "")) for e in events if e["kind"] == "note"]
    finals = [e for e in events if e["kind"] == "final"]
    info.update(model_calls=len(models), tool_calls=len(tools_),
                tokens_in=sum(int(e.get("tokens_in") or 0) for e in models),
                tokens_out=sum(int(e.get("tokens_out") or 0) for e in models))

    # L1, L2
    result = None
    if not finals:
        err.append("L1 thiếu sự kiện final (output cuối)")
    elif finals[-1].get("error"):
        err.append("L1 câu lỗi: %s" % str(finals[-1]["error"])[:160])
    else:
        try:
            result = json.loads(finals[-1].get("output") or "")
        except ValueError:
            err.append("L1 output không phải JSON")
    if isinstance(result, dict):
        shape = schema.validate_session_result(result) if "orders" in result else schema.validate_agent_result(result)
        err += ["L1 H4: " + s for s in shape[:5]]
        info["decision"] = result.get("decision")
        if result.get("trace_id") != cid:
            err.append("L2 trace_id=%r khác mã câu %r" % (result.get("trace_id"), cid))

    # L3
    for e in models:
        if e.get("error"):
            err.append("L3 lỗi gọi model: %s" % str(e["error"])[:160])
            continue
        m = str(e.get("model") or "")
        if not m:
            err.append("L3 lần gọi model không ghi tên model")
        ti, to = e.get("tokens_in"), e.get("tokens_out")
        if not (isinstance(ti, int) and isinstance(to, int) and ti >= 0 and to >= 0):
            err.append("L3 token không phải số nguyên ≥ 0 (%r / %r)" % (ti, to))
        elif m.lower() not in MOCK_MODELS and (ti == 0 or to == 0):
            warn.append("L3 model %s ghi token 0 — token phải lấy từ usage của API" % m)

    # L4
    for e in tools_:
        if e.get("name") not in names:
            err.append("L4 công cụ lạ %r (không có trong tools.py)" % e.get("name"))
        if e.get("error"):
            err.append("L4 công cụ %s lỗi: %s" % (e.get("name"), str(e["error"])[:160]))
        elif "output" not in e or "input" not in e:
            err.append("L4 công cụ %s thiếu input/output trong trace" % e.get("name"))

    # L5
    refused_in_code = any(n.startswith("refuse ở bước lọc") for n in notes)
    if models and not refused_in_code and not any(n.startswith("kế hoạch") for n in notes):
        warn.append("L5 model được gọi nhưng không có note \"kế hoạch\"")
    if not models and not refused_in_code and finals and not finals[-1].get("error"):
        warn.append("L5 không gọi model và không có note lý do (refuse ở bước lọc)")

    # L6
    if isinstance(result, dict):
        lookups = " ".join(str(e.get("output", "")) for e in tools_ if e.get("name") == "lookup_fee_rule")
        orders = result.get("orders") if "orders" in result else [result]
        for o in orders or []:
            for ln in (o or {}).get("lines") or []:
                rid = ln.get("rule_id")
                if rid and rid not in lookups:
                    warn.append("L6 rule_id %s không thấy trong output lookup_fee_rule (có thể do trace rút gọn)" % rid)

    info["fix"] = any(n.startswith("tự sửa thành công") for n in notes)
    info["fallback"] = any(n.startswith("fallback") for n in notes)
    info["verify_err"] = any(n.startswith("bước kiểm:") for n in notes)
    info["stops"] = [n for n in notes if n.startswith("dừng")]
    return err, warn, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--csv", help="file lượt tương ứng (eval/run-N.csv) để đối chiếu số lần gọi / token")
    a = ap.parse_args()
    header, cases = load(a.trace)
    names = tool_names()
    n_err = n_warn = 0
    infos = {}
    for cid, events in cases.items():
        err, warn, info = check_case(cid, events, names)
        infos[cid] = info
        n_err += len(err)
        n_warn += len(warn)
        for m in err:
            print("LỖI     %s: %s" % (cid, m))
        for m in warn:
            print("CẢNH BÁO %s: %s" % (cid, m))

    if header:   # lượt chính thức: đủ câu của bộ thử lúc chạy
        missing = [i for i in header.get("ids", []) if i not in cases]
        if missing:
            n_err += 1
            print("LỖI     trace thiếu %d câu của bộ thử: %s" % (len(missing), ", ".join(missing[:15])))

    if a.csv:    # L7
        with open(a.csv, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                i = infos.get(r["id"])
                if i is None:
                    n_err += 1
                    print("LỖI     %s: L7 có trong %s nhưng không có trong trace" % (r["id"], a.csv))
                    continue
                for k in ("model_calls", "tool_calls", "tokens_in", "tokens_out"):
                    if str(r.get(k, "")).strip() and int(float(r[k])) != i[k]:
                        n_err += 1
                        print("LỖI     %s: L7 %s=%s trong file lượt, trace đếm %d" % (r["id"], k, r[k], i[k]))

    n = len(infos) or 1
    dec = {}
    for i in infos.values():
        dec[i["decision"]] = dec.get(i["decision"], 0) + 1
    had_err = [i for i in infos.values() if i["verify_err"]]
    print("\n%s · %d câu · %d lỗi · %d cảnh báo" % (os.path.relpath(a.trace, ROOT), len(infos), n_err, n_warn))
    print("  quyết định: %s" % ", ".join("%s %d" % (k, v) for k, v in sorted(dec.items(), key=lambda x: str(x[0]))))
    print("  lần gọi công cụ trung bình / câu: %.1f · lần gọi model trung bình / câu: %.1f"
          % (sum(i["tool_calls"] for i in infos.values()) / n, sum(i["model_calls"] for i in infos.values()) / n))
    print("  bước kiểm báo lỗi: %d câu · tự sửa thành công: %d/%d · rơi về fallback: %d/%d câu"
          % (len(had_err), sum(i["fix"] for i in had_err), len(had_err), sum(i["fallback"] for i in infos.values()), len(infos)))
    stops = [s for i in infos.values() for s in i["stops"]]
    if stops:
        print("  dừng giữa chừng: %d lần (%s)" % (len(stops), "; ".join(sorted(set(s[:60] for s in stops)))))
    print("KẾT QUẢ: %s" % ("ĐẠT" if n_err == 0 else "CÓ LỖI"))
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
