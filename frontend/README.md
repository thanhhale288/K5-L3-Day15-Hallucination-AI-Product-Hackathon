# frontend — "Lãi đi đâu?" (chat agent qua AG-UI)

Hà giữ. React 19 + Vite + [Astryx](https://github.com/meta/astryx) (theme neutral, chữ component tiếng Việt) +
[AG-UI](https://github.com/ag-ui-protocol/ag-ui) (`@ag-ui/client`). Frontend **chỉ đọc** JSON `AgentResult` /
`SessionResult` (hợp đồng H4, `codebase/schema.py`) và không tự tính số. Số what-if do bridge gọi `tools.py`.

## Chạy

```bash
cd frontend && npm install

# A. Chế độ mẫu (không cần Python): SampleAgent phát lại kết quả đã tính sẵn trong samples/
npm run dev                                   # http://localhost:5173

# B. Agent thật: 2 terminal
python frontend/agui/server.py                # terminal 1, ở gốc repo: cầu AG-UI ở http://localhost:8000/agent
cd frontend && VITE_USE_API=1 npm run dev     # terminal 2
```

- `?mau=demo-0412.json` (hoặc tên file mẫu khác trong `samples/`) tự dán sẵn đơn đó khi mở trang, tiện khi demo hay quay video. `?view=import&demo=1` mở màn import với data demo.
- `.env` chưa có `MODEL_PROVIDER` thì agent chạy **AI giả**: theo kịch bản cố định của đơn `DEMO-0412`, nên dán đơn khác vẫn ra kết quả DEMO-0412. Giao diện hiện nhãn vàng "AI giả" để không nhầm. Muốn soi đơn bất kỳ thì nối model thật (`docs/connect-model.md`).
- Chạy bridge với agent ở thư mục khác (vd branch của Huy chưa merge): `AGENT_CODEBASE=/đường/dẫn/codebase python frontend/agui/server.py`.

## Luồng

```
Chủ shop ──chat──▶ ChatPage ──RunAgentInput──▶ POST /agent (frontend/agui/server.py)
                       ▲                              │ bọc codebase/agent.py: answer(text, session_state_id)
                       └──── sự kiện AG-UI (SSE) ◀────┘ móc vào TOOLS và note() để phát sự kiện thật
```

| Sự kiện AG-UI | Lấy từ đâu | Hiện ở đâu |
|---|---|---|
| `STEP_STARTED/FINISHED` | mỗi `note()` của agent (kế hoạch, bước kiểm, fallback) | dòng chấm trong tin nhắn agent |
| `TOOL_CALL_START/ARGS/END/RESULT` | mỗi lần agent gọi một công cụ trong `tools.py`, đúng thứ tự | nhóm "Đã gọi N công cụ" (mở ra xem từng lần) |
| `STATE_SNAPSHOT` | `result` (H4), `session_state_id`, `switch_info`, `what_if`, `model` | panel kết quả bên phải |
| `TEXT_MESSAGE_*` | tóm tắt ghép từ số trong `result` (`agui/summary.py`) | bong bóng chat |
| `RUN_ERROR` | lỗi model / công cụ | banner đỏ trong chat |

### Chủ shop thao tác được gì

| Thao tác | Đi đâu |
|---|---|
| Dán đơn, chat | `messages` → agent soi đơn |
| Trả lời câu hỏi của agent (Ask, vd giá vốn) | ô trả lời trong panel hoặc gõ vào chat; bridge gửi kèm `session_state_id`, agent làm tiếp mà không tách lại từ đầu |
| Thử đổi tỉ lệ / thử tắt một công tắc | `forwardedProps.command = {type: "what_if", order_id, switch, new_rate}` → bridge gọi `expected_amount` + `switch_what_if` (code), trả lãi sau khi đổi và số đơn được phép giảm |
| "Sẽ làm" / "Bỏ qua" một đề xuất | ghi vào state dùng chung `decisions` (lượt chạy sau agent nhận được) |
| Chép nháp gửi sàn, "Đã tự gửi" | clipboard + state `draft_sent`. Agent **không** gửi gì cho sàn |

Bridge suy số căn cứ (giá × SL − voucher shop) từ các dòng phí bắt buộc tính theo tỉ lệ (vd phí cố định 9% = −17.010đ
→ 189.000đ), để biết tỉ lệ hiện tại của từng công tắc. Nếu không suy được thì chỉ còn nút "Thử tắt".

### Gửi Thái / Huy

- `frontend/agui/server.py` hiện đang làm vai `POST /soi-don` (TH-7), dưới dạng một endpoint AG-UI. Thái có thể dùng luôn, hoặc chuyển sang `codebase/app.py`. Bridge chỉ dùng thư viện chuẩn và không sửa file nào của Huy hay Thái.
- `POST /import` (TH-11) vẫn chờ Thái: gửi `multipart/form-data` gồm `files` (xlsx export) và `cogs` (xlsx giá vốn), trả về nội dung `phan_tich.json`. Màn import bật bằng `VITE_IMPORT_API=1`.

## File

| File | Việc |
|---|---|
| `agui/server.py` | Cầu AG-UI (Python thư viện chuẩn): bọc `answer()`, phát sự kiện, lệnh what-if |
| `agui/summary.py` | Tóm tắt bằng chữ + `switch_info`, dùng chung cho bridge và `make_samples.py` |
| `src/agent/laiAgent.ts` | `HttpAgent` (bridge) hoặc `SampleAgent` (phát lại mẫu), kiểu state dùng chung |
| `src/agent/useLaiAgent.ts` | Hook React: lượt chat, công cụ, bước, state |
| `src/pages/ChatPage.tsx` | Màn chat (dựng từ template `ai-chat` của Astryx) + panel kết quả |
| `src/components/InvoiceView.tsx` | Một `AgentResult`: hoá đơn, chip, công tắc kèm nút thử, đề xuất kèm "Sẽ làm / Bỏ qua", nháp, Ask |
| `src/components/SessionView.tsx` | `SessionResult`: thẻ so sánh sàn + tab từng đơn |
| `src/pages/ImportPage.tsx` | Màn import tháng (HA-14, demo bổ sung) |
| `samples/make_samples.py` | Sinh lại JSON mẫu (gọi `tools.py`, không đọc đáp án): `python frontend/samples/make_samples.py` |

Lưu ý: đơn mẫu H4 `DEMO-0412` ra **escalate**, không phải act, vì dòng "Phí dịch vụ khác" −2.000đ không khớp luật nào.
