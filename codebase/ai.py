"""Nối model — chỗ DUY NHẤT trong bản chạy thử gọi model AI. NHÓM VIẾT phần gọi model thật.

Hợp đồng (giữ nguyên để khung đo được token):
    call_model(system: str, user: str) -> dict với 4 khoá
        "text":       str   chữ model trả về
        "model":      str   tên model đã gọi (để tra giá ở bảng giá model)
        "tokens_in":  int   số token vào, lấy từ trường usage trong phản hồi API — KHÔNG ước lượng
        "tokens_out": int   số token ra, gồm cả token suy luận / suy nghĩ nếu API tính riêng
    @model_call (từ tracing.py) tự ghi mỗi lần gọi vào trace; agent.py gọi call_model bao nhiêu lần
    cũng được, khung tự cộng token.
    Lỗi gọi model (hết lượt, sai key, mất mạng): cứ để exception bay ra — khung ghi lỗi vào cột error.

Chế độ giả (mặc định khi .env chưa có MODEL_PROVIDER, hoặc MODEL_PROVIDER=fake):
    trả một câu giả cố định, model "fake", token 0 — để luồng chạy hết từ trước CP2 (guide bước 3.2).
    Lượt `run.py eval` / `run.py simulate` chạy bằng model giả KHÔNG được tính.

Nối model thật: điền .env (chép từ .env.example), rồi viết nhánh gọi API ở dưới theo docs/connect-model.md
(có ví dụ OpenAI, Claude, model chạy trên máy, và cách nối nhà cung cấp khác). Không dán API key vào file này.
"""
import json
import os
import time
import urllib.error
import urllib.request

from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path=os.path.join(ROOT, ".env")):
    """Đọc file .env (KEY=VALUE mỗi dòng) vào biến môi trường, không ghi đè biến đã có. Khung — không cần sửa."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
MODEL_PROVIDER = (os.environ.get("MODEL_PROVIDER") or "fake").strip().lower()
MODEL_NAME = (os.environ.get("MODEL_NAME") or "").strip()
API_KEY = (os.environ.get("API_KEY") or "").strip()


TEMPERATURE = 0          # HU-5: nhiệt độ 0 để chạy lại ra cùng kết quả
MAX_TOKENS = 8192        # trần token ra mỗi lượt; final có 5 đơn cần chỗ, chạm trần thì JSON bị cắt cụt
URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
SHOW_RAW = False         # True: in nguyên phản hồi API khi cần tìm tên trường


def post_json(url, headers, body, timeout=120, retries=4):
    """POST JSON, trả JSON phản hồi. Thử lại khi bị giới hạn lượt (429) hoặc lỗi máy chủ (5xx)."""
    data = json.dumps(body).encode("utf-8")
    for i in range(retries):
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers=dict({"Content-Type": "application/json"}, **headers))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read().decode("utf-8"))
            if SHOW_RAW:
                print(json.dumps(out, ensure_ascii=False, indent=2)[:3000])
            return out
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and i < retries - 1:
                time.sleep(2 ** i * 2)
                continue
            raise RuntimeError("HTTP %d: %s" % (e.code, msg))


def call_openrouter(system, user):
    """OpenRouter Chat Completions (định dạng OpenAI). Token lấy từ usage của API, không ước lượng."""
    if not MODEL_NAME or not API_KEY:
        raise RuntimeError("MODEL_PROVIDER=openrouter cần MODEL_NAME và API_KEY trong .env")
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    data = post_json(URL_OPENROUTER, {"Authorization": "Bearer " + API_KEY},
                     {"model": MODEL_NAME, "messages": messages, "temperature": TEMPERATURE,
                      "max_tokens": MAX_TOKENS})
    if "error" in data and not data.get("choices"):
        raise RuntimeError("OpenRouter báo lỗi: %s" % json.dumps(data["error"], ensure_ascii=False)[:300])
    u = data.get("usage") or {}
    if "prompt_tokens" not in u or "completion_tokens" not in u:
        raise RuntimeError("Phản hồi OpenRouter thiếu usage (prompt_tokens / completion_tokens): %s"
                           % json.dumps(u, ensure_ascii=False))
    return {"text": data["choices"][0]["message"].get("content") or "",
            "model": data.get("model") or MODEL_NAME,
            # completion_tokens của OpenRouter đã gồm token suy luận (reasoning) nếu model có
            "tokens_in": u["prompt_tokens"], "tokens_out": u["completion_tokens"]}


@model_call
def call_model(system: str, user: str) -> dict:
    if MODEL_PROVIDER == "fake":
        last = (user.strip().splitlines() or [""])[-1]
        return {"text": "[câu trả lời giả — chưa nối model] " + last[:60], "model": "fake", "tokens_in": 0, "tokens_out": 0}
    if MODEL_PROVIDER == "openrouter":
        r = call_openrouter(system, user)
        return {"text": r["text"], "model": r["model"], "tokens_in": int(r["tokens_in"]),
                "tokens_out": int(r["tokens_out"])}
    raise NotImplementedError(
        "chưa viết phần gọi model thật cho MODEL_PROVIDER=%s trong codebase/ai.py — nhóm dùng openrouter "
        "(xem docs/connect-model.md)" % MODEL_PROVIDER)
