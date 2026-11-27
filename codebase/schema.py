"""Hợp đồng H4 (Huy giữ): JSON agent trả ra. Frontend (Hà), API (Thái), eval (Minh) chỉ đọc theo file này.

Một đơn  → AgentResult.  Dán nhiều đơn (2–5) → SessionResult, mỗi đơn bên trong là một AgentResult.

Quy ước chung:
  - Tiền: số nguyên VNĐ. Khoản trừ ÂM (vd -10395), khoản cộng DƯƠNG. Không có số thập phân trừ share_of_profit.
  - Ngày: "YYYY-MM-DD". Sàn: "shopee" | "tiktok" | "lazada".
  - Khoá luôn có mặt; không có giá trị thì để null (không bỏ khoá). Danh sách rỗng thì để [].

AgentResult
  decision           "act" | "ask" | "escalate" | "refuse"
                       act      đủ dữ liệu, mọi dòng khớp luật → lãi thật + 1–2 việc nên làm
                       ask      thiếu giá vốn, thiếu dòng, tổng các dòng không khớp tiền về → `question`
                       escalate có dòng lệch luật (vượt trần, sai tỉ lệ theo ngày) hoặc dòng lạ không khớp luật
                                → `draft_to_platform` (nháp, chủ shop tự gửi)
                       refuse   né phí, gian lận, dữ liệu shop khác, lệnh chèn trong chữ dán → `refusal_reason`
  platform, order_id, order_date
  lines              [Line]  mọi khoản trừ / giảm trên đơn (không gồm dòng giá bán)
  payout             tiền về (số hiển thị trên chi tiết thanh toán)
  cogs               giá vốn của cả đơn (giá vốn 1 sp × số lượng); null nếu chưa có
  profit             payout - cogs; null nếu chưa có giá vốn
  switches           [Switch] các khoản công tắc (chương trình shop tự bật), lớn nhất trước
  actions            [Action] tối đa 2 việc nên làm, chỉ việc làm được trong sàn
  question           câu hỏi lại (decision=ask), còn lại null
  draft_to_platform  nháp câu hỏi gửi sàn (decision=escalate), còn lại null
  refusal_reason     lý do từ chối (decision=refuse), còn lại null
  trace_id           mã trace, vd "run-3/0007" hoặc "app/…"

Line     {name, amount, type, rule_id, expected, delta, chunk_id, source_url}
           type      "bat_buoc" | "cong_tac" | "khong_khop"
           rule_id   rule_id trong data/fee_rules.csv (H2); null nếu không khớp luật nào
           expected  số đúng luật (âm) từ expected_amount; null nếu không có luật
           delta     amount - expected (0 = đúng luật); null nếu không có luật
           chunk_id  chunk trong kho chính sách (H1); null khi kho chưa có hoặc không tìm thấy
Switch   {name, amount, share_of_profit}   amount dương = số tiền công tắc ăn mất mỗi đơn;
                                            share_of_profit = amount / profit (null nếu profit ≤ 0 hoặc null)
Action   {text, gain_per_order}            gain_per_order: lãi thêm mỗi đơn (VNĐ) từ switch_what_if, hoặc null

SessionResult
  decision             quyết định chung: refuse > ask > escalate > act (lấy mức "cần người" cao nhất của các đơn)
  orders               [AgentResult]
  platform_comparison  {product, rows: [{platform, profit, top_switch}], best_platform}
                       chỉ có khi ≥ 2 sàn cùng sản phẩm, còn lại null
  session_state_id     mã phiên để Ask làm tiếp không phải tách lại từ đầu; null nếu không cần
  trace_id
"""

DECISIONS = ("act", "ask", "escalate", "refuse")
LINE_TYPES = ("bat_buoc", "cong_tac", "khong_khop")
PLATFORMS = ("shopee", "tiktok", "lazada")
# Mức "cần người" khi gộp nhiều đơn thành một quyết định phiên
DECISION_PRIORITY = {"refuse": 3, "ask": 2, "escalate": 1, "act": 0}

AGENT_RESULT_KEYS = ("decision", "platform", "order_id", "order_date", "lines", "payout", "cogs", "profit",
                     "switches", "actions", "question", "draft_to_platform", "refusal_reason", "trace_id")
LINE_KEYS = ("name", "amount", "type", "rule_id", "expected", "delta", "chunk_id", "source_url")
SWITCH_KEYS = ("name", "amount", "share_of_profit")
ACTION_KEYS = ("text", "gain_per_order")
SESSION_RESULT_KEYS = ("decision", "orders", "platform_comparison", "session_state_id", "trace_id")


def agent_result(**fields) -> dict:
    """AgentResult đủ khoá, khoá thiếu để null / []. Khoá lạ bị từ chối để không lệch hợp đồng."""
    unknown = set(fields) - set(AGENT_RESULT_KEYS)
    if unknown:
        raise KeyError("khoá không có trong AgentResult: %s" % ", ".join(sorted(unknown)))
    out = {k: None for k in AGENT_RESULT_KEYS}
    out.update(lines=[], switches=[], actions=[])
    out.update(fields)
    out["lines"] = [{k: ln.get(k) for k in LINE_KEYS} for ln in out["lines"] or []]
    out["switches"] = [{k: s.get(k) for k in SWITCH_KEYS} for s in out["switches"] or []]
    out["actions"] = [{k: a.get(k) for k in ACTION_KEYS} for a in out["actions"] or []][:2]
    return out


def session_result(orders: list, platform_comparison=None, session_state_id=None, trace_id=None) -> dict:
    """SessionResult; decision chung = mức cần người cao nhất trong các đơn."""
    decision = max((o["decision"] for o in orders), key=DECISION_PRIORITY.get, default="act")
    return {"decision": decision, "orders": orders, "platform_comparison": platform_comparison,
            "session_state_id": session_state_id, "trace_id": trace_id}


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_agent_result(r) -> list:
    """Danh sách lỗi hợp đồng (rỗng = hợp lệ). Chỉ kiểm hình dạng, không kiểm số đúng hay sai."""
    if not isinstance(r, dict):
        return ["AgentResult phải là object"]
    err = ["thiếu khoá %s" % k for k in AGENT_RESULT_KEYS if k not in r]
    err += ["khoá lạ %s" % k for k in r if k not in AGENT_RESULT_KEYS]
    if err:
        return err
    d = r["decision"]
    if d not in DECISIONS:
        err.append("decision=%r không thuộc %s" % (d, DECISIONS))
    if r["platform"] is not None and r["platform"] not in PLATFORMS:
        err.append("platform=%r không thuộc %s" % (r["platform"], PLATFORMS))
    for k in ("payout", "cogs", "profit"):
        if r[k] is not None and not _is_int(r[k]):
            err.append("%s phải là số nguyên VNĐ hoặc null" % k)
    for i, ln in enumerate(r["lines"] if isinstance(r["lines"], list) else []):
        if not isinstance(ln, dict) or set(ln) != set(LINE_KEYS):
            err.append("lines[%d] phải có đúng các khoá %s" % (i, LINE_KEYS))
            continue
        if ln["type"] not in LINE_TYPES:
            err.append("lines[%d].type=%r không thuộc %s" % (i, ln["type"], LINE_TYPES))
        for k in ("amount", "expected", "delta"):
            if ln[k] is not None and not _is_int(ln[k]):
                err.append("lines[%d].%s phải là số nguyên VNĐ hoặc null" % (i, k))
    for k in ("lines", "switches", "actions"):
        if not isinstance(r[k], list):
            err.append("%s phải là danh sách" % k)
    if isinstance(r["actions"], list) and len(r["actions"]) > 2:
        err.append("actions tối đa 2 việc")
    need = {"ask": "question", "escalate": "draft_to_platform", "refuse": "refusal_reason"}
    if d in need and not r[need[d]]:
        err.append("decision=%s cần %s" % (d, need[d]))
    if d == "act" and (r["cogs"] is None or r["profit"] is None):
        err.append("decision=act cần cogs và profit (thiếu giá vốn thì phải ask)")
    return err


def validate_session_result(s) -> list:
    if not isinstance(s, dict):
        return ["SessionResult phải là object"]
    err = ["thiếu khoá %s" % k for k in SESSION_RESULT_KEYS if k not in s]
    err += ["khoá lạ %s" % k for k in s if k not in SESSION_RESULT_KEYS]
    if err:
        return err
    if s["decision"] not in DECISIONS:
        err.append("decision=%r không thuộc %s" % (s["decision"], DECISIONS))
    if not isinstance(s["orders"], list) or not s["orders"]:
        return err + ["orders phải là danh sách AgentResult, ít nhất 1 đơn"]
    for i, o in enumerate(s["orders"]):
        err += ["orders[%d]: %s" % (i, e) for e in validate_agent_result(o)]
    pc = s["platform_comparison"]
    if pc is not None:
        if not isinstance(pc, dict) or set(pc) != {"product", "rows", "best_platform"}:
            err.append("platform_comparison phải có đúng product, rows, best_platform")
        elif len({row.get("platform") for row in pc["rows"]}) < 2:
            err.append("platform_comparison chỉ có khi ≥ 2 sàn")
    return err
