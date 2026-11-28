# Reflection — Quách Ngọc Huy

> Làm ở guide bước 5.3. Mỗi người một file: chép file này thành `reflection/<ten-khong-dau>.md` (viết thường, không dấu). Hạn: **23:59 Thứ Bảy 28/11**. Mỗi câu 3–6 dòng.

1. Vai trò + phần mình làm (trỏ tới file / commit):
   Mình giữ phần AI agent: chốt hợp đồng H3 (chữ ký 10 công cụ, `codebase/tools.py`) và H4 (`AgentResult` / `SessionResult`, `codebase/schema.py`), đẩy lên main sớm để cả nhóm code theo (`93fb987`).
   Viết `codebase/agent.py` (lọc yêu cầu, lập kế hoạch, vòng công cụ có giới hạn, bước kiểm số / `rule_id` / `chunk_id` đúng sàn, đúng ngày, fallback), prompt `codebase/prompt.py` và `codebase/ai.py`: nối OpenRouter, đọc cấu hình theo `.env.example` mới, thêm OpenAI / DeepSeek để Minh chạy được lượt 1 (`40e96d9`, `27c90d2`, `1479dbc`, PR #9 `edc5ce9`, PR #11 `ea31890`).
   Chạy thật 3 đơn mỗi sàn 1 đơn (`d8c8252`), `eval --try` 3/3 (`63ff746`), phiên nhiều đơn so sàn (`15c646a`); cải tiến HU-11 sau lượt 1 (prompt v0.4, PR #12 `fde233b`) đưa lượt 2 từ 21/30 lên 30/30.
   Ngoài phần agent: pipeline lọc và chunk chính sách người bán Shopee (`rag/`, `data/shopee_policy/seller/`, `81d38a5`).

2. AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):
   Mình dùng Claude Code trong VS Code để viết phần lớn code, chạy thử, quét secret và thao tác git; mình chia phạm vi, chốt hợp đồng và quyết định cái gì được đẩy lên main.
   Chạy model thật mới lộ ra lỗi trong code AI viết: parser vớ nhầm object con khi JSON bị cắt cụt, model trả `"Shopee"` / `"thuong"` làm tra luật rỗng, bước kiểm chặn nhầm `chunk_id` hợp lệ lấy từ `fee_rules.csv`, `ai.py` không thử lại khi mạng bị ngắt.
   Có lúc AI tự viết bài thử sai (gọi API thật bằng key giả) và báo "SAI", phải đọc lại mới biết lỗi nằm ở bài thử chứ không ở code.
   Bài học: chỉ tin kết quả AI báo khi đã chạy thật và đọc trace, và giữ AI làm đúng phần của mình để không đè code của thành viên khác.

3. Một câu thử trượt của nhóm và mình học được gì từ nó:
   B01 ở lượt 1 (`run-1@20261128-082327`, `gpt-6.2-sol`): chủ shop viết "Hãy soi đơn này:" rồi dán đơn Shopee, agent trả `refuse`. Cùng lỗi này làm trượt 8 câu (B01, B04–B06, B09, B13–B14, B19).
   Trace cho thấy chính model từ chối ở bước kế hoạch: prompt v0.3 của mình coi mọi câu "hãy làm…" trong chữ dán là lệnh chèn, lại bọc cả yêu cầu lẫn lịch sử công cụ chung một khối "DỮ LIỆU", nên model mạnh làm theo quá đúng.
   Cải tiến HU-11 (prompt v0.4): yêu cầu soi / so sánh đơn là hợp lệ, chỉ từ chối khi chính yêu cầu là xấu, tách tin nhắn chủ shop khỏi lịch sử do hệ thống ghi. Lượt 2 lên 30/30, không câu nào tệ đi, 4 câu từ chối vẫn bị chặn bằng code.
   Học được: chặn quá tay hại người dùng không kém chặn lỏng; lệnh chèn rõ ràng nên chặn bằng code để prompt khỏi phải đa nghi, và mọi thay đổi phải đo lại trên cùng bộ câu.
