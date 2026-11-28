# API "Lãi đi đâu?" (TH-7, TH-11)

Dành cho frontend: HA-8 dùng màn soi đơn, HA-14 dùng màn import. API chạy bằng thư viện chuẩn của Python, không cần cài thêm gì. Riêng `/import` cần `openpyxl` (đã có trong `requirements.txt`).

```
python codebase/app.py --serve              # http://127.0.0.1:8000
python codebase/app.py --serve --port 8765  # đổi cổng
```

Model lấy theo `.env` (`MODEL_PROVIDER` …). Để trống thì chạy AI giả: luồng vẫn chạy hết, nhưng luôn trả đơn mẫu DEMO-0412.

CORS mở cho mọi origin (bản demo chạy trên máy). Mọi body đều là JSON UTF-8. Khi lỗi, body có dạng `{"error": "…"}`.

## `POST /soi-don`: soi 1–5 đơn

Request (`Content-Type: application/json`):

```json
{
  "text": "chữ dán chi tiết thanh toán của 1–5 đơn (sàn nào cũng được)",
  "cogs": 95000,
  "session_state_id": null
}
```

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `text` | có | Chữ dán, tối đa 20.000 ký tự. Khi đang trả lời câu hỏi của agent thì đây là **câu trả lời** của chủ shop |
| `cogs` | không | Giá vốn nhập ở form. Nhận một số (giá vốn **một** sản phẩm), một chuỗi, hoặc `{"SP-031": 95000}`. Giá trị được nối vào sau chữ dán để agent đọc; mọi phép tính vẫn do code làm |
| `session_state_id` | không | Gửi lại mã phiên lấy từ lượt trước khi agent hỏi lại (Ask), để agent làm tiếp mà không tách đơn lại từ đầu |

Response `200`: **đúng nguyên** `AgentResult` (khi dán 1 đơn) hoặc `SessionResult` (khi dán nhiều đơn) theo hợp đồng H4 (`TASK.md`, `codebase/schema.py`). Nếu có `orders` thì đó là `SessionResult`.

Các header (đã mở `Access-Control-Expose-Headers` để frontend đọc được):

| Header | Ý nghĩa |
|---|---|
| `X-Trace-Id` | Mã trace của lượt này, trùng với `trace_id` trong body. Trace nằm ở `traces/api/<ngày>.jsonl` |
| `X-Session-State-Id` | Chỉ có khi `decision = "ask"`. Gửi lại ở `session_state_id` cùng câu trả lời. Với `SessionResult` thì mã này cũng nằm trong body |
| `X-Model-Calls`, `X-Tool-Calls`, `X-Tokens-In`, `X-Tokens-Out` | Số lần gọi model / công cụ và số token, để hiện "chi phí lượt này" nếu cần |

Vì `AgentResult` không được có khoá lạ (H4), mã phiên của Ask một đơn chỉ đi qua header.

Luồng Ask:

```js
let r = await fetch(API + "/soi-don", {method: "POST", headers: {"Content-Type": "application/json"},
                                      body: JSON.stringify({text: pasted})});
let result = await r.json();
if (result.decision === "ask") {
  const sid = r.headers.get("X-Session-State-Id") || result.session_state_id;
  // hiện result.question, chủ shop trả lời → gửi tiếp
  r = await fetch(API + "/soi-don", {method: "POST", headers: {"Content-Type": "application/json"},
                                    body: JSON.stringify({text: answer, session_state_id: sid})});
}
```

Mã lỗi:

| Mã | Khi nào |
|---|---|
| `400` | Body không phải JSON, thiếu `text`, `cogs` âm hoặc sai kiểu |
| `413` | `text` hoặc body quá lớn |
| `415` | Không phải `application/json` |
| `500` | Lỗi khi soi đơn (vẫn ghi trace) |
| `503` | Chưa nối model |

Mỗi lúc chỉ chạy một lượt agent, các request đến sau sẽ chờ. Như vậy là đủ cho demo.

## `POST /import`: phân tích file export tháng (demo bổ sung, ngoài lát cắt)

Request `multipart/form-data`:

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `exports` | có, lặp được | File `.xlsx` export đơn hàng của Shopee / TikTok Shop / Lazada. Sàn được nhận theo tên cột |
| `cogs` | không | File giá vốn `.xlsx` (sheet "Giá vốn" + "Thông tin shop", mẫu: `data/demo_import/gia_von_mau.xlsx`) |
| `platform` | không | `shopee` \| `tiktok` \| `lazada`, khi không tự nhận ra sàn |

```js
const fd = new FormData();
for (const f of exportFiles) fd.append("exports", f);
if (cogsFile) fd.append("cogs", cogsFile);
const res = await (await fetch(API + "/import", {method: "POST", body: fd})).json();
```

Response `200`:

```json
{
  "import_id": "imp-20261128-073428-8d84e7",
  "bang_phi": "fee_rules.csv",
  "files": [{"file": "shopee_don_hang_2026-11.xlsx", "platform": "shopee", "orders": 262, "unknown_columns": []}],
  "co_gia_von": true,
  "luu_tai": "data/imported/imp-20261128-073428-8d84e7",
  "phan_tich": {
    "theo_san": {},
    "theo_sku_san": [],
    "dong_lech_luat": [],
    "phi_khac_khong_khop": [],
    "quang_cao": [],
    "bang_phi": "fee_rules.csv"
  }
}
```

- `phan_tich` giống hệt `phan_tich.json` mà `python data/import_export.py …` ghi ra: lãi theo sàn và theo SKU, các dòng lệch luật, công tắc ăn lãi, ROAS so với hoà vốn.
- Mọi con số do code tính.
- `400` khi file không phải `.xlsx`, không nhận ra sàn, hoặc thiếu file export. Body tối đa 20 MB.
- File tải lên và kết quả lưu ở `data/imported/<import_id>/`, thư mục này đã nằm trong `.gitignore` vì có thể là dữ liệu thật của shop.

## `GET /health`

```json
{"ok": true, "model_provider": "fake", "model": "fake", "bang_phi": "fee_rules.csv",
 "endpoints": ["POST /soi-don", "POST /import", "GET /health"]}
```

## Kiểm trace (TH-8)

```
python scripts/check_traces.py traces/api/2026-11-28.jsonl
python scripts/check_traces.py traces/run-1.jsonl --csv eval/run-1.csv
```
