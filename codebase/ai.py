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


def _env(name):
    return (os.environ.get(name) or "").strip()


# Cấu hình model cho vai trò AGENT (xem .env.example mục 1–3). Biến mới có giá trị thì ưu tiên; để trống thì dùng
# biến cũ MODEL_PROVIDER / MODEL_NAME / API_KEY như trước (tương thích ngược). Tên 3 biến module giữ nguyên.
MODEL_PROVIDER = (_env("LLM_AGENT_PROVIDER") or _env("MODEL_PROVIDER") or "fake").lower()
MODEL_NAME = _env("LLM_AGENT_MODEL") or _env("MODEL_NAME")

# Nhà cung cấp theo kiểu OpenAI (/chat/completions): tiền tố biến .env + địa chỉ mặc định (.env.example mục 1).
OPENAI_COMPATIBLE = {
    "openrouter": ("OPENROUTER", "https://openrouter.ai/api/v1"),
    "openai": ("OPENAI", "https://api.openai.com/v1"),
    "deepseek": ("DEEPSEEK", "https://api.deepseek.com"),
}
_PREFIX, _DEFAULT_BASE = OPENAI_COMPATIBLE.get(MODEL_PROVIDER, ("", ""))
# Key theo nhà cung cấp (mục 1, vd OPENAI_API_KEY) ưu tiên hơn API_KEY chung (mục 3).
API_KEY = (_env(_PREFIX + "_API_KEY") if _PREFIX else "") or _env("API_KEY")
BASE_URL = ((_env(_PREFIX + "_BASE_URL") if _PREFIX else "") or _DEFAULT_BASE).rstrip("/")


TEMPERATURE = 0          # HU-5: nhiệt độ 0 để chạy lại ra cùng kết quả
MAX_TOKENS = 8192        # trần token ra mỗi lượt; final có 5 đơn cần chỗ, chạm trần thì JSON bị cắt cụt
SHOW_RAW = False         # True: in nguyên phản hồi API khi cần tìm tên trường


def post_json(url, headers, body, timeout=120, retries=4):
    """POST JSON, trả JSON phản hồi. Thử lại khi bị giới hạn lượt (429), lỗi máy chủ (5xx)
    hoặc lỗi mạng tạm thời (kết nối bị ngắt, timeout)."""
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
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:   # HTTPError đã bắt ở trên
            if i < retries - 1:
                time.sleep(2 ** i * 2)
                continue
            raise RuntimeError("Lỗi mạng khi gọi model sau %d lần thử: %s: %s" % (retries, type(e).__name__, e))


def call_chat(system, user):
    """Chat Completions kiểu OpenAI cho openrouter / openai / deepseek. Token lấy từ usage của API, không ước lượng.
    OpenAI: model mới dùng max_completion_tokens thay cho max_tokens; model không cho đặt temperature thì gửi lại
    một lần không có temperature (dùng mặc định của model)."""
    if not MODEL_NAME or not API_KEY:
        raise RuntimeError("MODEL_PROVIDER=%s cần tên model (LLM_AGENT_MODEL hoặc MODEL_NAME) và key (%s_API_KEY hoặc "
                           "API_KEY) trong .env" % (MODEL_PROVIDER, _PREFIX))
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = {"model": MODEL_NAME, "messages": messages, "temperature": TEMPERATURE}
    body["max_completion_tokens" if MODEL_PROVIDER == "openai" else "max_tokens"] = MAX_TOKENS
    url, headers = BASE_URL + "/chat/completions", {"Authorization": "Bearer " + API_KEY}
    try:
        data = post_json(url, headers, body)
    except RuntimeError as e:
        msg = str(e).lower()
        if not msg.startswith("http 400"):
            raise
        if "temperature" in msg and "temperature" in body:          # model chỉ nhận temperature mặc định
            body.pop("temperature")
        elif "max_tokens" in msg and "max_tokens" in body:          # model đòi max_completion_tokens
            body["max_completion_tokens"] = body.pop("max_tokens")
        else:
            raise
        data = post_json(url, headers, body)
    if "error" in data and not data.get("choices"):
        raise RuntimeError("%s báo lỗi: %s" % (MODEL_PROVIDER, json.dumps(data["error"], ensure_ascii=False)[:300]))
    u = data.get("usage") or {}
    if "prompt_tokens" not in u or "completion_tokens" not in u:
        raise RuntimeError("Phản hồi %s thiếu usage (prompt_tokens / completion_tokens): %s"
                           % (MODEL_PROVIDER, json.dumps(u, ensure_ascii=False)))
    return {"text": data["choices"][0]["message"].get("content") or "",
            # trả đúng tên model đã cấu hình để cost/ tra bảng giá (OpenAI có thể trả tên bản snapshot có ngày)
            "model": MODEL_NAME,
            # completion_tokens (OpenAI / OpenRouter / DeepSeek) đã gồm token suy luận nếu model có
            "tokens_in": u["prompt_tokens"], "tokens_out": u["completion_tokens"]}


call_openrouter = call_chat   # tên cũ, giữ để không vỡ chỗ nào còn gọi


@model_call
def call_model(system: str, user: str) -> dict:
    if MODEL_PROVIDER == "fake":
        last = (user.strip().splitlines() or [""])[-1]
        return {"text": "[câu trả lời giả — chưa nối model] " + last[:60], "model": "fake", "tokens_in": 0, "tokens_out": 0}
    if MODEL_PROVIDER in OPENAI_COMPATIBLE:
        r = call_chat(system, user)
        return {"text": r["text"], "model": r["model"], "tokens_in": int(r["tokens_in"]),
                "tokens_out": int(r["tokens_out"])}
    raise NotImplementedError(
        "chưa viết phần gọi model thật cho MODEL_PROVIDER=%s trong codebase/ai.py — hỗ trợ: %s "
        "(xem .env.example mục 1–3)" % (MODEL_PROVIDER, ", ".join(OPENAI_COMPATIBLE)))
