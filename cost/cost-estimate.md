# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`, sinh bằng `python cost/make_personas.py`; đầu vào là chữ dán trong `data/synthetic/pastes.jsonl`, không đọc file đáp án):

  | Persona | Tỉ lệ shop | Phiên / shop / tháng | Lượt hỏi / phiên | Chuyện gì |
  |---|---:|---:|---:|---|
  | `soi_1_don` | 45% | 6 | 1 | dán 1 đơn vừa về tiền, đủ giá vốn |
  | `so_3_san` | 20% | 4 | 1 | dán 3 đơn cùng sản phẩm ở 3 sàn để so |
  | `thieu_gia_von` | 20% | 8 | 2 | quên giá vốn → agent hỏi (Ask) → trả lời rồi làm tiếp |
  | `dong_la` | 15% | 8 | 1 | đơn có khoản lạ → agent soạn nháp hỏi sàn (Escalate) |

  Nguồn: *(tự ước tính)* theo câu chuyện 3 kịch bản dưới đây (shop đa sàn soát đơn 4–8 lần / tháng, khoảng 1/3 phiên có Ask hoặc Escalate). Chưa có số đo trên shop thật.
  Giới hạn của khung: mỗi lượt hỏi gọi `answer()` riêng, không giữ phiên. Lượt "làm tiếp" của `thieu_gia_von` được mô phỏng bằng cách dán lại đơn kèm giá vốn, nên có thể tốn hơn một chút so với làm tiếp bằng `session_state_id`.
- **Số người dùng thật** 3 kịch bản: thấp **1.800** · cơ sở **9.000** · cao **27.000** shop / tháng. Nguồn: câu chuyện 3 kịch bản ngay dưới.

### Câu chuyện 3 kịch bản (HA-12)

Mốc chung: **~601.800 shop có đơn năm 2025** (Metric, theo `CONTEXT.md`). Sản phẩm dành cho shop bán **≥ 2 sàn**, ước **30% ≈ 180.000 shop** *(tự ước tính, giống `spec.md` §2)*. Mô phỏng dùng **cùng một tỉ lệ 4 persona cho cả 3 kịch bản**, bình quân **~6,3 phiên / shop / tháng** (mục ngay dưới); 3 kịch bản chỉ khác nhau ở số shop dùng.

| Kịch bản | Bao nhiêu shop dùng | Chuyện gì xảy ra | Phiên / tháng (× 6,3) |
|---|---|---|---|
| **Thấp** | 1% của 180.000 ≈ **1.800** | Chỉ những shop từng bị trừ phí lạ (như review "đơn 180k mà ăn tận 51k") tìm đến, dán vài đơn khi thấy tiền về ít | 1.800 × 6,3 ≈ 11.300 |
| **Cơ sở** | 5% ≈ **9.000** | Shop đa sàn dùng mỗi tuần 1–2 lần để soát đơn mới về tiền, so cùng sản phẩm giữa các sàn; khoảng 1/3 phiên có Ask hoặc Escalate | 9.000 × 6,3 ≈ 56.700 |
| **Cao** | 15% ≈ **27.000** | Đi kèm một công cụ quản lý đơn (BigSeller, Sapo) hoặc cộng đồng người bán chia sẻ | 27.000 × 6,3 ≈ 170.100 |

Đọc bảng chi phí ở mục 2 theo câu chuyện này: **chi phí / tháng = số shop × tỉ lệ persona × phiên / tháng × chi phí / phiên của persona đó**, rồi **chia cho tỉ lệ đạt**, không coi như đạt 100%. Câu hỏi cần trả lời ở mục 3: chi phí mỗi shop mỗi tháng có nhỏ hơn nhiều so với thứ shop lấy lại được không. Thứ lấy lại gồm ~2 giờ soát đơn mỗi tháng (8 lần × 15 phút, *tự ước tính*) và các khoản bị trừ sai mà shop phát hiện ra (data demo có 4 đơn Voucher Xtra vượt trần, mỗi đơn thu dư 25.350–51.800đ: `frontend/samples/import-thang-11.json`).
- **Giá** (USD / 1 triệu token, vào / ra; bảng giá DeepSeek API Docs https://api-docs.deepseek.com/quick_start/pricing, Hà chép ngày 28/11/2026). Tính MỌI token vào theo giá **cache miss**, nên là cận trên:

  | Model | Cao điểm | Thấp điểm |
  |---|---:|---:|
  | `deepseek-flash` (V4.1-Flash-1017) | 0,30 / 1,20 | 0,15 / 0,60 |
  | `deepseek-v4-pro` (V4-Pro-0813) | 1,32 / 3,96 | 0,66 / 1,98 |

  Cao điểm là 08:00–11:00 và 13:00–17:00 giờ Việt Nam, thứ Hai–Sáu; còn lại là thấp điểm. Đây là giờ chủ shop hay soát đơn, nên **lấy giá cao điểm làm số chính**. Model agent đang gọi là `deepseek-chat`, không có trong bảng giá mới: tính theo `deepseek-flash` *(giả định `deepseek-chat` trỏ tới bản Flash)*.
- **Tỉ lệ đạt** dùng để tính: **30/30 (100%)** lượt `run-2@20261128-094309` (`--rate-from eval/run-2.csv`). Lượt 1 là 21/30 (70%), dùng làm cận dưới ở mục 2.
- **Đo token trên model `deepseek-chat`, tính giá 4 dòng trên.** Lượt eval đã chấm chạy bằng `gpt-6.2-sol` (không có key trên máy nhóm), nên tỉ lệ đạt lấy từ model khác; khung đã cảnh báo điều này.

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · run ID `simulate-1@20261128-105032` · **50 phiên** (65 lượt hỏi) · seed 42 · phiên lỗi **0/50** · trace `traces/simulate-1.jsonl`. Bảng persona chép từ `cost/simulate-1-summary.md`. Bảng chi phí chép từ `cost/simulate-1-gia-moi-summary.md`: cùng token đã đo, tính lại theo bảng giá mới bằng `python cost/reprice.py cost/simulate-1.csv --rate-from eval/run-2.csv` (gọi hàm `summarize` của khung, không gọi lại model).

| Persona | Số phiên | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| soi_1_don | 21 | 1 | 47.528 | 2.488 | 6,1 | 14,4 |
| so_3_san | 10 | 1 | 69.214 | 6.732 | 6,1 | 37,2 |
| thieu_gia_von | 15 | 2 | 71.077 | 3.372 | 9,9 | 21,8 |
| dong_la | 4 | 1 | 49.413 | 2.896 | 6,0 | 17,0 |

| Model (giá vào · ra $/1M) | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp (1.800 shop) | / tháng — cơ sở (9.000 shop) | / tháng — cao (27.000 shop) | / shop / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|
| **deepseek-flash cao điểm** (0,30 · 1,20) | $0,0221 (≈ 552đ) | $0,0221 (≈ 552đ) | $238 (≈ 5,9 triệu đ) | $1.190 (≈ 29,7 triệu đ) | $3.569 (≈ 89,2 triệu đ) | $0,132 (≈ **3.305đ**) |
| deepseek-flash thấp điểm (0,15 · 0,60) | $0,0110 (≈ 276đ) | $0,0110 (≈ 276đ) | $119 (≈ 3,0 triệu đ) | $595 (≈ 14,9 triệu đ) | $1.784 (≈ 44,6 triệu đ) | $0,066 (≈ **1.652đ**) |
| deepseek-v4-pro cao điểm (1,32 · 3,96) | $0,0924 (≈ 2.309đ) | $0,0924 (≈ 2.309đ) | $997 (≈ 24,9 triệu đ) | $4.985 (≈ 124,6 triệu đ) | $14.956 (≈ 373,9 triệu đ) | $0,554 (≈ **13.848đ**) |
| deepseek-v4-pro thấp điểm (0,66 · 1,98) | $0,0462 (≈ 1.155đ) | $0,0462 (≈ 1.155đ) | $499 (≈ 12,5 triệu đ) | $2.493 (≈ 62,3 triệu đ) | $7.478 (≈ 186,9 triệu đ) | $0,277 (≈ **6.924đ**) |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**. Với lượt 2 (100%) hai cột bằng nhau. Nếu tỉ lệ đạt chỉ như lượt 1 (70%), mọi số chia 0,7 (tính tay từ bảng trên): `deepseek-flash` cao điểm ≈ 790đ / task, ≈ **4.700đ / shop / tháng** ở kịch bản cơ sở.
- Quy đổi 25.000đ / USD *(tự ước tính)*.
- Phiên `so_3_san` và `thieu_gia_von` tốn token nhất (~70.000 token vào / phiên), vì agent tra luật và gọi công cụ cho từng đơn hoặc chạy lại đơn sau khi có giá vốn.
- Bảng chưa trừ giảm giá cache hit (Flash: 0,006 so với 0,30 $/1M lúc cao điểm). Prompt hệ thống và danh sách công cụ lặp lại ở mọi lượt nên phần cache được thực tế có thể lớn; số trên là cận trên.

## 3. So với impact

- Impact / shop / tháng (`spec.md` §2): ~8 lần × 15 phút ≈ 2 giờ soát đơn *(tự ước tính)*, cộng khoản thu sai phát hiện được (data demo: 4 đơn Voucher Xtra vượt trần, mỗi đơn thu dư 25.350–51.800đ; chưa có số trên shop thật).
- Chi phí / shop / tháng (cơ sở): **~3.300đ với `deepseek-flash` cao điểm** (số chính), ~1.650đ thấp điểm, ~13.800đ nếu dùng `deepseek-v4-pro` cao điểm; tối đa ~4.700đ (Flash cao điểm) nếu tỉ lệ đạt chỉ 70%.
- **Kết luận một dòng — đáng làm không:** có, về chi phí: với Flash, chi phí model khoảng 1.650–4.700đ mỗi shop mỗi tháng, nhỏ hơn một đơn bị thu dư (≥ 25.350đ trong data demo). Chưa chắc về giá trị: 2 giờ soát đơn là *tự ước tính*, `deepseek-chat` được giả định tính giá như Flash, và chưa có shop thật dùng thử.

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: model rẻ hơn · cache · cắt ngữ cảnh · giới hạn bước — mỗi cần gạt đổi chi phí bao nhiêu
- Chi phí ngoài model: hosting, lưu trữ, giờ công người duyệt
- Quy mô nào thì bài toán còn đáng làm
