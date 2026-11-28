#!/usr/bin/env python3
"""Cầu AG-UI cho frontend "Lãi đi đâu?" (Hà giữ). Thư viện chuẩn Python, không thêm phụ thuộc.

Bọc agent của Huy (`codebase/agent.py: answer(text, session_state_id)`) thành một endpoint AG-UI
(https://docs.ag-ui.com): nhận `RunAgentInput` (JSON), trả luồng sự kiện SSE.

  python frontend/agui/server.py                 # http://localhost:8000/agent
  python frontend/agui/server.py --port 9000
  AGENT_CODEBASE=/đường/dẫn/codebase python frontend/agui/server.py   # chạy với agent ở thư mục khác

Sự kiện phát ra trong một lượt:
  RUN_STARTED → STEP_STARTED/FINISHED (mỗi note() của agent: kế hoạch, bước kiểm, fallback…)
  → TOOL_CALL_START/ARGS/END/RESULT (mỗi lần agent gọi một công cụ trong tools.py, đúng thứ tự thật)
  → STATE_SNAPSHOT {result: AgentResult | SessionResult, session_state_id, …}
  → TEXT_MESSAGE_START/CONTENT/END (tóm tắt bằng chữ, mọi số lấy từ result) → RUN_FINISHED (hoặc RUN_ERROR)

Lệnh từ giao diện (`forwardedProps.command`), để chủ shop thao tác trên đề xuất:
  {"type": "soi"}  (mặc định)  tin nhắn cuối của người dùng là chữ dán; nếu state có session_state_id của
                               một câu Ask thì gửi tin nhắn đó làm câu trả lời (agent làm tiếp, không tách lại).
  {"type": "what_if", "order_id", "switch", "new_rate"}  thử đổi tỉ lệ một công tắc (0 = tắt): gọi
                               expected_amount + switch_what_if của tools.py. Số do code tính, không qua LLM.
Không có công cụ nào tác động ra ngoài: agent chỉ soạn nháp, chủ shop tự bấm trên sàn.
"""
from __future__ import annotations

import argparse
import functools
import inspect
import json
import os
import queue
import sys
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODEBASE = Path(os.environ.get("AGENT_CODEBASE") or ROOT / "codebase").resolve()
sys.path.insert(0, str(CODEBASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(CODEBASE.parent)  # agent và tools đọc data/ theo đường dẫn tương đối với gốc repo

import tracing  # noqa: E402
import tools  # noqa: E402
import agent  # noqa: E402
from summary import summarize, switch_info, vnd  # noqa: E402

RUN_LOCK = threading.Lock()  # agent giữ trạng thái module (SESSIONS, patch công cụ): chạy từng lượt một
TOOL_LABEL = {
    "check_lines_sum": "Kiểm tổng các dòng", "lookup_fee_rule": "Tra luật phí", "search_policy": "Tìm đoạn chính sách",
    "expected_amount": "Tính số đúng luật", "unit_profit": "Tính lãi thật", "switch_what_if": "Thử đổi công tắc",
    "breakeven_roas": "ROAS hoà vốn", "compare_platforms": "So sàn", "ask_user": "Hỏi lại chủ shop",
    "draft_platform_question": "Soạn nháp gửi sàn",
}


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class Run:
    """Một lượt AG-UI: gom sự kiện vào hàng đợi để luồng HTTP đẩy ra dần (SSE)."""

    def __init__(self, inp: dict):
        self.inp = inp
        self.thread_id = inp.get("threadId") or _id("thread")
        self.run_id = inp.get("runId") or _id("run")
        self.state = dict(inp.get("state") or {})
        self.q: queue.Queue = queue.Queue()

    def emit(self, type_: str, **fields):
        self.q.put({"type": type_, **fields})

    def text(self, content: str):
        mid = _id("msg")
        self.emit("TEXT_MESSAGE_START", messageId=mid, role="assistant")
        for i in range(0, len(content), 40):  # chia nhỏ để giao diện thấy chữ chạy
            self.emit("TEXT_MESSAGE_CONTENT", messageId=mid, delta=content[i:i + 40])
        self.emit("TEXT_MESSAGE_END", messageId=mid)

    def tool_events(self, name: str, args: dict, call):
        tid, parent = _id("tool"), _id("msg")
        self.emit("TOOL_CALL_START", toolCallId=tid, toolCallName=name, parentMessageId=parent)
        self.emit("TOOL_CALL_ARGS", toolCallId=tid, delta=json.dumps(args, ensure_ascii=False, default=str))
        self.emit("TOOL_CALL_END", toolCallId=tid)
        try:
            out = call()
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}"}
            self.emit("TOOL_CALL_RESULT", messageId=_id("msg"), toolCallId=tid, role="tool",
                      content=json.dumps(out, ensure_ascii=False, default=str))
            raise
        self.emit("TOOL_CALL_RESULT", messageId=_id("msg"), toolCallId=tid, role="tool",
                  content=json.dumps(out, ensure_ascii=False, default=str))
        return out

    def step(self, name: str):
        self.emit("STEP_STARTED", stepName=name)
        self.emit("STEP_FINISHED", stepName=name)

    # ── các lệnh ──
    def last_user_text(self) -> str:
        for m in reversed(self.inp.get("messages") or []):
            if m.get("role") == "user":
                c = m.get("content")
                return c if isinstance(c, str) else " ".join(p.get("text", "") for p in c or [] if isinstance(p, dict))
        return ""

    def do_soi(self):
        text = self.last_user_text().strip()
        if not text:
            self.text("Bạn dán chi tiết thanh toán của 1–5 đơn vào ô chat giúp mình.")
            return
        prev = self.state.get("result") or {}
        sid = self.state.get("session_state_id") if prev.get("decision") == "ask" else None
        originals = {k: tools.TOOLS[k] for k in getattr(agent, "H3_TOOLS", list(tools.TOOLS)) if k in tools.TOOLS}
        orig_note = agent.note

        def wrap(name, fn):
            sig = inspect.signature(getattr(fn, "__wrapped__", fn))

            # Agent gọi công cụ cả theo tên lẫn theo vị trí; giữ __wrapped__ để tool_catalog() vẫn đọc đúng chữ ký.
            @functools.wraps(fn)
            def wrapped(*a, **kw):
                try:
                    args = dict(sig.bind_partial(*a, **kw).arguments)
                except TypeError:
                    args = {"args": list(a), **kw}
                return self.tool_events(name, args, lambda: fn(*a, **kw))
            return wrapped

        def note(msg):
            orig_note(msg)
            self.step(str(msg)[:160])

        if agent.ai.MODEL_PROVIDER == "fake":
            self.step("AI giả (chưa nối model, MODEL_PROVIDER trống): agent đi theo kịch bản cố định của đơn DEMO-0412, "
                      "kết quả chỉ đúng với đơn đó")
        try:
            for k, fn in originals.items():
                tools.TOOLS[k] = wrap(k, fn)
            agent.note = note
            tracing.begin("agui")
            out = agent.answer(text, session_state_id=sid) if sid else agent.answer(text)
        finally:
            tracing.end()
            tools.TOOLS.update(originals)
            agent.note = orig_note
        result = out.get("result") or json.loads(out["output"])
        self.state.update(result=result, session_state_id=out.get("session_state_id"),
                          trace_id=result.get("trace_id"), what_if=[], switch_info=switch_info(result, tools._rule_by_id),
                          model=agent.ai.MODEL_PROVIDER)
        self.emit("STATE_SNAPSHOT", snapshot=self.state)
        self.text(summarize(result))

    def do_what_if(self, cmd: dict):
        result = self.state.get("result") or {}
        orders = result.get("orders") or [result]
        o = next((x for x in orders if x.get("order_id") == cmd.get("order_id")), None)
        if not o:
            self.text("Mình không tìm thấy đơn đó trong kết quả đang mở.")
            return
        line = next((ln for ln in o.get("lines") or [] if ln["name"] == cmd.get("switch")), None)
        if not line or line.get("type") != "cong_tac":
            self.text("Chỉ thử đổi được các khoản công tắc (chương trình shop tự bật).")
            return
        rate = float(cmd.get("new_rate") or 0)
        qty = int(cmd.get("qty") or 1)
        info = next((x for x in switch_info(result, tools._rule_by_id) if x["order_id"] == o["order_id"] and x["switch"] == line["name"]), {})
        base = info.get("base")
        if rate and line.get("rule_id") and base:
            new = self.tool_events("expected_amount",
                                   {"rule_id": line["rule_id"], "base_amount": base, "qty": qty, "shop_rate": rate},
                                   lambda: tools.TOOLS["expected_amount"](line["rule_id"], int(base), None, qty,
                                                                          shop_rate=rate))["expected"]
        else:
            new = 0
        w = self.tool_events("switch_what_if",
                             {"lines": o["lines"], "switch": line["name"], "new_value": new, "profit": o.get("profit")},
                             lambda: tools.TOOLS["switch_what_if"](o["lines"], line["name"], new, o.get("profit")))
        entry = {"order_id": o["order_id"], "switch": line["name"], "new_rate": rate, **w}
        self.state["what_if"] = [x for x in self.state.get("what_if") or []
                                 if not (x["order_id"] == o["order_id"] and x["switch"] == line["name"])] + [entry]
        self.emit("STATE_SNAPSHOT", snapshot=self.state)
        how = "tắt" if not rate else f"đổi sang {rate:g}%"
        msg = (f"Nếu {how} **{line['name']}** ở đơn {o['order_id']}: lãi mỗi đơn từ {vnd(o.get('profit'))} "
               f"thành **{vnd(w.get('profit_after'))}** (+{vnd(w.get('gain_per_order'))}).")
        if w.get("max_order_drop_pct") is not None:
            msg += f" Số đơn được phép giảm tối đa {w['max_order_drop_pct']:.0f}% mà tổng lãi không thấp hơn trước."
        self.text(msg + " Bạn là người quyết định có đổi trên sàn hay không.")

    def run(self):
        self.emit("RUN_STARTED", threadId=self.thread_id, runId=self.run_id)
        try:
            cmd = (self.inp.get("forwardedProps") or {}).get("command") or {"type": "soi"}
            with RUN_LOCK:
                if cmd.get("type") == "what_if":
                    self.do_what_if(cmd)
                else:
                    self.do_soi()
            self.emit("RUN_FINISHED", threadId=self.thread_id, runId=self.run_id)
        except Exception as e:  # lỗi model / công cụ: báo cho giao diện, không treo luồng
            traceback.print_exc()
            self.emit("RUN_ERROR", message=f"{type(e).__name__}: {e}")
        finally:
            self.q.put(None)


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/health"):
            body = json.dumps({"ok": True, "agent": str(CODEBASE), "model": agent.ai.MODEL_PROVIDER}).encode()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.rstrip("/") != "/agent":
            self.send_error(404)
            return
        try:
            inp = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except json.JSONDecodeError:
            self.send_error(400, "RunAgentInput không phải JSON")
            return
        run = Run(inp)
        threading.Thread(target=run.run, daemon=True).start()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        while (ev := run.q.get()) is not None:
            self.wfile.write(b"data: " + json.dumps(ev, ensure_ascii=False, default=str).encode() + b"\n\n")
            self.wfile.flush()

    def log_message(self, fmt, *args):
        sys.stderr.write("[agui] " + fmt % args + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("AGUI_PORT", 8000)))
    a = ap.parse_args()
    print(f"AG-UI: http://localhost:{a.port}/agent · agent: {CODEBASE} · model: {agent.ai.MODEL_PROVIDER}")
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
