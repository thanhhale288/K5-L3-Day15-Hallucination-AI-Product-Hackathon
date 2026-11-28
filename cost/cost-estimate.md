# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): ≥3 kiểu — tỉ lệ, số phiên / người / tháng, số lượt hỏi / phiên. Nguồn: __
- **Số người dùng thật** 3 kịch bản: thấp **1.800** · cơ sở **9.000** · cao **27.000** shop / tháng. Nguồn: xem mục "Câu chuyện 3 kịch bản" ngay dưới (Hà).

### Câu chuyện 3 kịch bản (HA-12, Hà viết; số tiền điền khi Thái chạy `simulate`)

Mốc chung: **~601.800 shop có đơn năm 2025** (Metric, theo `CONTEXT.md`). Sản phẩm dành cho shop bán **≥ 2 sàn**, ước **30% ≈ 180.000 shop** *(tự ước tính, giống `spec.md` §2)*. Mỗi shop dùng 4–8 phiên / tháng tuỳ persona (`cost/personas.yaml`).

| Kịch bản | Bao nhiêu shop dùng | Chuyện gì xảy ra | Phiên / tháng *(tự ước tính)* |
|---|---|---|---|
| **Thấp** | 1% của 180.000 ≈ **1.800** | Chỉ những shop từng bị trừ phí lạ (như review "đơn 180k mà ăn tận 51k") tìm đến, dán vài đơn khi thấy tiền về ít, dùng 4 phiên / tháng | 1.800 × 4 ≈ 7.200 |
| **Cơ sở** | 5% ≈ **9.000** | Shop đa sàn dùng mỗi tuần 1–2 lần để soát đơn mới về tiền, so cùng sản phẩm giữa các sàn; khoảng 1/3 phiên có Ask hoặc Escalate | 9.000 × 8 ≈ 72.000 |
| **Cao** | 15% ≈ **27.000** | Đi kèm một công cụ quản lý đơn (BigSeller, Sapo) hoặc cộng đồng người bán chia sẻ; mỗi phiên dán 3 đơn để so sàn | 27.000 × 8 ≈ 216.000 |

Đọc bảng chi phí ở mục 2 theo câu chuyện này: **chi phí / tháng = số phiên × chi phí / phiên**, rồi **chia cho tỉ lệ đạt** của lượt 2 (Minh), không coi như đạt 100%. Câu hỏi cần trả lời ở mục 3: chi phí mỗi shop mỗi tháng có nhỏ hơn nhiều so với thứ shop lấy lại được không. Thứ lấy lại gồm ~2 giờ soát đơn mỗi tháng (8 lần × 15 phút, *tự ước tính*) và các khoản bị trừ sai mà shop phát hiện ra (data demo có 4 đơn Voucher Xtra vượt trần, mỗi đơn thu dư 25.350–51.800đ: `frontend/samples/import-thang-11.json`).
- **Giá** ≥2 mức model (từ `further-reading/model-prices.md` của repo đề, có link + ngày xem): __ · __
- **Tỉ lệ đạt** dùng để tính: __/__ (__%) — lượt `run-__` (lượt 2)
- Đo token trên model __, tính giá model __ và __

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-__.csv` · run ID __ · __ phiên · seed __

*(dán bảng từ `cost/simulate-N-summary.md`)*

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp | / tháng — cơ sở | / tháng — cao | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): ~8 lần × 15 phút ≈ 2 giờ soát đơn *(tự ước tính)*, cộng khoản thu sai phát hiện được (chưa có số trên shop thật)
- Chi phí / người / tháng (cơ sở, model __): __
- **Kết luận một dòng — đáng làm không:** __

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: model rẻ hơn · cache · cắt ngữ cảnh · giới hạn bước — mỗi cần gạt đổi chi phí bao nhiêu
- Chi phí ngoài model: hosting, lưu trữ, giờ công người duyệt
- Quy mô nào thì bài toán còn đáng làm
