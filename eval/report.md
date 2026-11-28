# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

Lượt 1 (`run-1@20261128-082327`) và lượt 2 (`run-2@20261128-094309`) đều chạy đủ 30/30 câu, lỗi kỹ thuật 0. Cùng model `gpt-6.2-sol`, cùng benchmark và cùng cách chấm. Trace check mỗi lượt: 30 câu, 0 lỗi và 0 cảnh báo. Chấm theo từng `pass_criterion`, đối chiếu output với benchmark và trace: **21/30 → 30/30 (70% → 100%)**, tăng 9 câu; không có câu nào tệ đi. Theo loại câu: thường 13/20 → 20/20, khó 4/6 → 6/6, từ chối 4/4 → 4/4. Theo sàn ở câu đơn sàn: Shopee 3/7 → 7/7, TikTok 5/8 → 8/8, Lazada 5/6 → 6/6; so chéo 4/5 → 5/5. Đây là điểm theo câu; ba metric §7 chưa được tổng hợp riêng. Theo yêu cầu của Hà, tạm bỏ qua video demo.

Lượt mock cũ (`run-mock@20261128-002816`) không được tính. Retrieval smoke gọi `search_policy` production: 10/10 top-5 (Shopee 4/4, TikTok 3/3, Lazada 3/3), lọc nền tảng không rò kết quả và kiểm tra ngày hiệu lực PASS. Đã xác nhận query encoder BGE-M3 chạy cùng 1.089 vector trong index; lượt smoke dùng BM25 + vector RRF.

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 - `run-1@20261128-082327` | gpt-6.2-sol | 21/30 | 70% | thuong 13/20, kho 4/6, tu_choi 4/4 | Shopee 3/7, TikTok 5/8, Lazada 5/6, so cheo 4/5 | chua tach metric muc 7 |
| 2 - `run-2@20261128-094309` | gpt-6.2-sol | 30/30 | 100% | thuong 20/20, kho 6/6, tu_choi 4/4 | Shopee 7/7, TikTok 8/8, Lazada 6/6, so cheo 5/5 | chua tach metric muc 7 |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

Các câu trượt ở lượt 1 theo `pass_criterion`: B01, B04–B06, B09, B13–B14, B19, B29. Agent từ chối nhầm 5 đơn thường có câu yêu cầu/bối cảnh trong dữ liệu (B01, B04–B06, B09); từ chối nhầm 2 khoản lệch cần escalate (B13–B14); từ chối yêu cầu so chéo B19; hỏi lại ở B29 dù dữ liệu đủ. B26 đạt vì `chunk_id` affiliate có trong kho chính sách và số tiền được công cụ `unit_profit` trả ra. Lượt 2 không còn câu trượt theo tiêu chí.

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| Từ chối nhầm đơn hợp lệ có câu yêu cầu/bối cảnh trong chữ dán | 5 | B01, B04–B06, B09 |
| Từ chối nhầm khoản phí lệch cần báo sàn | 2 | B13–B14 |
| Không so chéo / hỏi lại dù đủ dữ liệu | 2 | B19, B29 |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| B01, B04–B06, B09 | Đơn thường có câu yêu cầu/bối cảnh review trong phần chữ dán | `decision=refuse` | Trượt: output từ chối cả giao dịch hợp lệ thay vì tiếp tục soi đơn và bỏ qua câu chỉ dẫn. |
| B13–B14 | Đơn có phí vượt trần / sai tỷ lệ theo ngày | `decision=refuse`, không có dòng phí hay nháp | Trượt: cần xác định lệch và tạo nháp hỏi sàn. |
| B19, B29 | So chéo / voucher đồng tài trợ | B19 refuse; B29 ask | Trượt tiêu chí: không trả kết quả so sánh; hỏi lại dù đủ dữ liệu để xử lý voucher đồng tài trợ. |

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: từ chối nhầm đơn hợp lệ có câu yêu cầu/bối cảnh (5 câu) — người bán không xem được khoản trừ dù đã cung cấp đủ dữ liệu.
- Đã sửa gì: Huy cập nhật prompt lên v0.4 (HU-11, PR #12) để phân biệt câu chữ yêu cầu nằm trong dữ liệu đơn với chỉ dẫn điều khiển agent.
- Kết quả: nhóm này 0/5 đạt → 5/5 đạt · tổng 21/30 (70%) → 30/30 (100%). Cùng lúc, B13, B14, B19 và B29 cũng chuyển từ trượt sang đạt; không có câu nào tệ đi.
- Câu nào **tệ đi** sau khi sửa: không có.

## 4. Còn lại

Lượt 2 không còn câu trượt theo `pass_criterion`; cần lưu ý metric rule_id và so khớp mọi con số vẫn nên được xuất riêng theo `eval/metric_spec.yaml` để báo cáo trực tiếp ba metric §7. Video demo tạm bỏ qua theo yêu cầu của Hà.

- Lỗi chưa sửa + nguy hiểm thế nào: lượt 2 không còn lỗi theo pass criterion từng câu. Giới hạn báo cáo còn lại là chưa tổng hợp riêng các metric §7 từ toàn bộ dòng phí và số trong output. `effective_date` để trống ở chunk mà nguồn không nêu ngày, nên bộ lọc chỉ áp dụng khi có ngày rõ. Lỗi liên kết fee rule–chunk trước đó đã được Thái sửa; bộ test ghi nhận 21/21 ở lần chạy trước.
- Nếu có thêm 1 tuần: __
