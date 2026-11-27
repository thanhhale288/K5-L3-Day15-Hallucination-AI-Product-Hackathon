# frontend — "Lãi đi đâu?"

Hà giữ. React 19 + Vite + [Astryx](https://github.com/meta/astryx) (theme neutral, chữ component tiếng Việt).
Frontend **chỉ đọc** JSON `AgentResult` / `SessionResult` (hợp đồng H4, `codebase/schema.py`) và JSON phân tích của
`data/import_export.py`. Không tự cộng trừ số nào.

## Chạy

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 — chế độ mẫu, đọc frontend/samples/*.json
```

Mở thẳng một mẫu (tiện khi demo hoặc quay video): `?mau=demo-0412.json`, `?mau=session-3-san.json`,
`?mau=ask-thieu-gia-von.json`, `?mau=refuse.json`, `?mau=act-lazada.json`, `?mau=escalate-lech-luat.json`;
màn import có sẵn data demo: `?view=import&demo=1`.

### Nối API thật (HA-8)

```bash
VITE_USE_API=1 npm run dev                       # gọi /soi-don, /import qua proxy tới http://localhost:8000
VITE_USE_API=1 API_TARGET=http://localhost:9000 npm run dev
VITE_API_URL=https://api.example npm run build   # bản build gọi thẳng URL này
```

## API frontend đang gọi (đề xuất cho TH-7, TH-11; Thái đổi thì báo Hà)

| Endpoint | Gửi | Nhận |
|---|---|---|
| `POST /soi-don` | JSON `{"text": "<chữ dán 1–5 đơn>", "cogs": 95000 \| null, "session_state_id": "s-0042" \| null}`. `session_state_id` chỉ có khi đang trả lời một câu Ask; `cogs` là giá vốn MỘT sản phẩm | `AgentResult` (1 đơn) hoặc `SessionResult` (≥ 2 đơn), đúng `codebase/schema.py` |
| `POST /import` | `multipart/form-data`: `files` (1–3 file xlsx export), `cogs` (file giá vốn xlsx) | Nội dung `phan_tich.json` của `data/import_export.py` |

## File

| File | Việc |
|---|---|
| `src/pages/SoiDonPage.tsx` | Màn chính (HA-6): dán đơn bên trái, hoá đơn đã soi bên phải |
| `src/components/InvoiceView.tsx` | Một `AgentResult`: tiền về / giá vốn / lãi, chip bắt buộc · công tắc · không khớp, dòng lệch luật, nháp gửi sàn, Ask, Refuse |
| `src/components/SessionView.tsx` | `SessionResult`: thẻ so sánh sàn + tab từng đơn |
| `src/pages/ImportPage.tsx` | Màn import tháng (HA-14, demo bổ sung): lãi theo sàn và SKU, đơn cần soi, ROAS so với hoà vốn |
| `src/api.ts` | Gọi API, hoặc trả mẫu khớp mã đơn trong chữ dán |
| `src/types.ts` | Bản TypeScript của H4 |
| `samples/make_samples.py` | Sinh lại toàn bộ JSON mẫu: `python frontend/samples/make_samples.py` (cần `openpyxl` cho mẫu import) |

## Mẫu là gì

`samples/*.json` do `make_samples.py` sinh: gọi đúng các công cụ trong `codebase/tools.py` theo thứ tự cố định
(không có LLM), đầu vào là `data/synthetic/` (đơn giả có seed). Không đọc file đáp án. Câu từ chối là chữ mẫu.
`import-thang-11.json` là output của `data/import_export.py` trên bộ "Shop Demo" giả lập.

Lưu ý khi đọc mẫu: đơn mẫu H4 `DEMO-0412` ra **escalate**, không phải act, vì dòng "Phí dịch vụ khác" −2.000đ không
khớp luật nào. Theo `schema.py`, có dòng không khớp luật thì quyết định là escalate.
