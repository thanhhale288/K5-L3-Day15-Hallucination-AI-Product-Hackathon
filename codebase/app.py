"""Bản chạy thử: dòng lệnh (mặc định) hoặc API HTTP cho frontend (TH-7, TH-11). Chỉ thư viện chuẩn.

    python run.py                                   dòng lệnh: gõ đầu vào → answer() trong agent.py → in kết quả
    python codebase/app.py --serve [--port 8000]    API HTTP (mặc định 127.0.0.1:8000)

API (chi tiết, ví dụ gọi: docs/api.md):
  POST /soi-don  JSON {"text", "cogs"?, "session_state_id"?} → AgentResult hoặc SessionResult (H4, codebase/schema.py),
                 đúng nguyên hình dạng H4. Header: X-Trace-Id, X-Session-State-Id (khi agent hỏi lại), X-Model-Calls,
                 X-Tool-Calls, X-Tokens-In, X-Tokens-Out. Trace mỗi lượt → traces/api/<ngày>.jsonl (không commit).
  POST /import   multipart/form-data: exports (1..n file xlsx export của sàn), cogs (file giá vốn, tuỳ chọn),
                 platform (tuỳ chọn) → JSON phân tích của data/import_export.py; file ghi vào data/imported/ (không commit).
  GET  /health   tình trạng (model đang dùng, bảng phí).
Không công cụ nào có tác động ra ngoài: API chỉ đọc dữ liệu, tính và soạn nháp.
"""
import os
import sys

for _stream in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _where(e):
    """File (trong codebase/) gây lỗi khi nạp: SyntaxError có e.filename, lỗi khác lấy khung cuối của traceback."""
    import traceback
    path = getattr(e, "filename", None) or (traceback.extract_tb(e.__traceback__)[-1].filename if e.__traceback__ else "")
    if not path:
        return "codebase/"
    p = os.path.abspath(path)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.relpath(p, base).replace(os.sep, "/") if p.startswith(base) else path

def main() -> int:
    try:
        import tracing
        from agent import answer
    except Exception as e:  # lỗi cú pháp, thiếu thư viện… trong codebase/
        print("Không nạp được codebase/ — lỗi ở %s: %s: %s" % (_where(e), type(e).__name__, e))
        print("Sửa lỗi rồi chạy lại. Cách nối model: docs/connect-model.md")
        return 1
    print("Bản chạy thử — gõ đầu vào rồi Enter. Thoát: Ctrl+C (hoặc Enter 2 lần với dòng trống).")
    blank = 0
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text:
            blank += 1
            if blank >= 2:
                return 0
            continue
        blank = 0
        tracing.begin("app")
        try:
            result = answer(text)
        except NotImplementedError as e:
            tracing.end()
            print("Chưa nối model: %s" % e)
            return 1
        except Exception as e:  # lỗi gọi model: báo rồi cho hỏi tiếp
            tracing.end()
            print("[lỗi] %s: %s" % (type(e).__name__, e))
            continue
        s, _ = tracing.end()
        print(result.get("output", "") if isinstance(result, dict) else result)
        print("   (model: %s · gọi model %d lần · công cụ %d lần · token vào %d / ra %d)"
              % (", ".join(s["models"]) or "—", s["model_calls"], s["tool_calls"], s["tokens_in"], s["tokens_out"]))


# ═══════════════════════════════ API HTTP (TH-7 /soi-don · TH-11 /import) ═══════════════════════════════
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_TRACES = os.path.join(ROOT, "traces", "api")       # .gitignore: chữ dán có thể là đơn thật của shop
IMPORTED = os.path.join(ROOT, "data", "imported")      # .gitignore: file export thật của shop
MAX_JSON_BYTES = 1_000_000
MAX_UPLOAD_BYTES = 20_000_000
MAX_TEXT_CHARS = 20_000
EXPOSE = "X-Trace-Id, X-Session-State-Id, X-Model-Calls, X-Tool-Calls, X-Tokens-In, X-Tokens-Out"


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


def _vnd(v):
    return "{:,}đ".format(int(v)).replace(",", ".")


def cogs_text(cogs):
    """Giá vốn nhập riêng ở form → một dòng chữ nối sau chữ dán (agent đọc như dữ liệu, code vẫn tính mọi số).
    Nhận: số (giá vốn MỘT sản phẩm), chuỗi, hoặc {mã / tên sản phẩm: số}."""
    if cogs is None or cogs == "" or cogs == {}:
        return ""
    if isinstance(cogs, bool):
        raise ApiError(400, "cogs phải là số, chuỗi hoặc {sản phẩm: số}")
    if isinstance(cogs, (int, float)):
        if cogs < 0:
            raise ApiError(400, "cogs không được âm")
        return "Giá vốn mỗi sản phẩm: %s" % _vnd(round(cogs))
    if isinstance(cogs, str):
        return "Giá vốn: %s" % cogs.strip()[:300]
    if isinstance(cogs, dict):
        parts = []
        for k, v in list(cogs.items())[:20]:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
                raise ApiError(400, "cogs[%r] phải là số ≥ 0" % k)
            parts.append("%s %s" % (str(k)[:80], _vnd(round(v))))
        return "Giá vốn mỗi sản phẩm: " + "; ".join(parts)
    raise ApiError(400, "cogs phải là số, chuỗi hoặc {sản phẩm: số}")


class SoiDon:
    """POST /soi-don. Một lượt = một trace (cùng định dạng traces/run-N.jsonl, có sự kiện "final"),
    nên scripts/check_traces.py kiểm được cả trace của API. Khoá: tracing và SESSIONS của agent là biến
    toàn cục, nên mỗi lúc chỉ chạy một lượt agent (đủ cho demo)."""

    def __init__(self):
        import threading
        import time
        import tracing
        from agent import answer
        self.tracing, self.answer, self.lock = tracing, answer, threading.Lock()
        self.run_id = "api@" + time.strftime("%Y%m%d-%H%M%S")
        self.n = 0

    def __call__(self, body):
        import time
        if not isinstance(body, dict):
            raise ApiError(400, "body phải là object JSON")
        sid = body.get("session_state_id") or None
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ApiError(400, "thiếu \"text\": chữ dán 1–5 đơn (hoặc câu trả lời khi có session_state_id)")
        if len(text) > MAX_TEXT_CHARS:
            raise ApiError(413, "text dài quá %d ký tự" % MAX_TEXT_CHARS)
        if sid is not None and not isinstance(sid, str):
            raise ApiError(400, "session_state_id phải là chuỗi")
        extra = cogs_text(body.get("cogs"))
        text = text.strip() + ("\n" + extra if extra else "")
        with self.lock:
            self.n += 1
            case = "api-%s-%03d" % (time.strftime("%Y%m%d-%H%M%S"), self.n)
            self.tracing.begin(case)
            try:
                res = self.answer(text, session_state_id=sid) if sid else self.answer(text)
            except NotImplementedError as e:
                self.tracing.end()
                raise ApiError(503, "chưa nối model: %s" % e)
            except Exception as e:
                summary, events = self.tracing.end()
                self._write(case, events + [{"kind": "final", "output": "", "error": "%s: %s" % (type(e).__name__, e)}])
                raise ApiError(500, "lỗi khi soi đơn (%s); trace %s" % (type(e).__name__, case))
            summary, events = self.tracing.end()
        result = res.get("result") if isinstance(res, dict) else None
        if not isinstance(result, dict):
            raise ApiError(500, "agent không trả AgentResult / SessionResult")
        self._write(case, events + [{"kind": "final", "output": res.get("output", ""), "error": ""}])
        headers = {"X-Trace-Id": case, "X-Model-Calls": summary["model_calls"], "X-Tool-Calls": summary["tool_calls"],
                   "X-Tokens-In": summary["tokens_in"], "X-Tokens-Out": summary["tokens_out"]}
        new_sid = res.get("session_state_id") or result.get("session_state_id")
        if new_sid:
            headers["X-Session-State-Id"] = new_sid
        return result, headers

    def _write(self, case, events):
        import json
        import time
        os.makedirs(API_TRACES, exist_ok=True)
        path = os.path.join(API_TRACES, time.strftime("%Y-%m-%d") + ".jsonl")
        with open(path, "a", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(dict({"run_id": self.run_id, "case": case}, **e), ensure_ascii=False, default=str) + "\n")


def parse_multipart(content_type, body):
    """multipart/form-data → [(tên trường, tên file | None, bytes)]. Thư viện chuẩn (module cgi đã bỏ ở Python 3.13)."""
    from email import policy
    from email.parser import BytesParser
    if "boundary=" not in (content_type or ""):
        raise ApiError(400, "cần multipart/form-data có boundary")
    msg = BytesParser(policy=policy.HTTP).parsebytes(
        b"Content-Type: " + content_type.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
    if not msg.is_multipart():
        raise ApiError(400, "body multipart không hợp lệ")
    out = []
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name:
            out.append((name, part.get_filename(), part.get_payload(decode=True) or b""))
    return out


def import_files(content_type, body):
    """POST /import: lưu file vào data/imported/<import_id>/uploads/, gọi data/import_export.run_import."""
    import time
    import uuid
    parts = parse_multipart(content_type, body)
    exports = [(fn, data) for name, fn, data in parts if name in ("exports", "exports[]", "files", "files[]", "file") and fn]
    cogs = next(((fn, data) for name, fn, data in parts if name == "cogs" and fn), None)
    platform = next((data.decode("utf-8", "replace").strip() for name, fn, data in parts
                     if name == "platform" and not fn), "") or None
    if not exports:
        raise ApiError(400, "thiếu file export: gửi ≥ 1 file xlsx ở trường \"exports\"")
    if platform and platform not in ("shopee", "tiktok", "lazada"):
        raise ApiError(400, "platform phải là shopee | tiktok | lazada")
    for fn, data in exports + ([cogs] if cogs else []):
        if not data.startswith(b"PK"):   # xlsx là file zip
            raise ApiError(400, "%s không phải file .xlsx" % fn)
    import_id = "imp-%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), uuid.uuid4().hex[:6])
    up = os.path.join(IMPORTED, import_id, "uploads")
    os.makedirs(up)
    paths = []
    for i, (fn, data) in enumerate(exports, 1):     # tên file do người dùng gửi KHÔNG dùng làm đường dẫn
        p = os.path.join(up, "export_%02d.xlsx" % i)
        with open(p, "wb") as f:
            f.write(data)
        paths.append((p, os.path.basename(fn)))
    cogs_path = None
    if cogs:
        cogs_path = os.path.join(up, "gia_von.xlsx")
        with open(cogs_path, "wb") as f:
            f.write(cogs[1])
    sys.path.insert(0, os.path.join(ROOT, "data"))
    try:
        import import_export
    except SystemExit as e:      # thiếu openpyxl
        raise ApiError(503, str(e))
    try:
        r = import_export.run_import([p for p, _ in paths], cogs_path, platform, None,
                                     os.path.join(IMPORTED, import_id))
    except import_export.ImportFileError as e:
        raise ApiError(400, str(e).replace("export_", "file export "))
    for info, (_, original) in zip(r["files"], paths):
        info["file"] = original
    try:
        where = os.path.relpath(r["out_dir"], ROOT).replace(os.sep, "/")
    except ValueError:            # khác ổ đĩa (Windows)
        where = r["out_dir"]
    return {"import_id": import_id, "bang_phi": r["bang_phi"], "files": r["files"], "co_gia_von": bool(cogs),
            "luu_tai": where, "phan_tich": r["phan_tich"]}


def make_server(host="127.0.0.1", port=8000):
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    soi_don = SoiDon()
    import ai
    sys.path.insert(0, os.path.join(ROOT, "data"))
    import fee_engine

    class Handler(BaseHTTPRequestHandler):
        server_version = "LaiDiDau/1.0"

        def _send(self, status, obj, headers=None):
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Expose-Headers", EXPOSE)
            for k, v in (headers or {}).items():
                self.send_header(k, str(v))
            self.end_headers()
            self.wfile.write(data)

        def _body(self, limit):
            n = int(self.headers.get("Content-Length") or 0)
            if n > limit:
                raise ApiError(413, "body lớn quá %d byte" % limit)
            return self.rfile.read(n) if n else b""

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_GET(self):
            if self.path.split("?")[0] in ("/", "/health"):
                rules_path = fee_engine.FEE_RULES_OFFICIAL if fee_engine.FEE_RULES_OFFICIAL.exists() else fee_engine.FEE_RULES_V0
                return self._send(200, {"ok": True, "model_provider": ai.MODEL_PROVIDER,
                                        "model": ai.MODEL_NAME or ai.MODEL_PROVIDER, "bang_phi": rules_path.name,
                                        "endpoints": ["POST /soi-don", "POST /import", "GET /health"]})
            self._send(404, {"error": "không có đường dẫn %s" % self.path})

        def do_POST(self):
            route = self.path.split("?")[0]
            try:
                if route == "/soi-don":
                    if "json" not in (self.headers.get("Content-Type") or ""):
                        raise ApiError(415, "cần Content-Type: application/json")
                    try:
                        body = json.loads(self._body(MAX_JSON_BYTES).decode("utf-8") or "null")
                    except (ValueError, UnicodeDecodeError):
                        raise ApiError(400, "body không phải JSON hợp lệ")
                    result, headers = soi_don(body)
                    return self._send(200, result, headers)
                if route == "/import":
                    return self._send(200, import_files(self.headers.get("Content-Type"), self._body(MAX_UPLOAD_BYTES)))
                raise ApiError(404, "không có đường dẫn %s" % route)
            except ApiError as e:
                self._send(e.status, {"error": e.message})
            except Exception as e:  # không lộ traceback ra ngoài
                self.log_error("lỗi %s: %s", type(e).__name__, e)
                self._send(500, {"error": "lỗi máy chủ (%s)" % type(e).__name__})

        def log_message(self, fmt, *args):  # không in nội dung body (có thể là đơn thật) ra log
            sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    return ThreadingHTTPServer((host, port), Handler)


def serve(host="127.0.0.1", port=8000) -> int:
    try:
        httpd = make_server(host, port)
    except Exception as e:
        print("Không khởi động được API — lỗi ở %s: %s: %s" % (_where(e), type(e).__name__, e))
        return 1
    print("API chạy ở http://%s:%d  (POST /soi-don · POST /import · GET /health) — Ctrl+C để dừng" % (host, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true", help="chạy API HTTP thay cho dòng lệnh")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    sys.exit(serve(a.host, a.port) if a.serve else main())
