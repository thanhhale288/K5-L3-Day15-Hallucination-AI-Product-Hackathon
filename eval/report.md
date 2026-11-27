# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

CP3 run thật chưa có. `python run.py eval` đã chạy hết 30 input ngày 28/11 nhưng runner tạo `eval/run-mock.csv` (`run-mock@20261128-002816`) do provider trả model `fake`, 0 token; runner không tạo `run-N.csv`, nên không có điểm pass hoặc run ID hợp lệ để nộp. Không chấm output giả.

Benchmark đã được làm mới từ `data/fee_rules.csv` sau lượt mock, nên lượt fake cũ không đại diện cho bộ câu hiện tại. Retrieval smoke gọi `search_policy` production: 10/10 top-5 (Shopee 4/4, TikTok 3/3, Lazada 3/3), lọc nền tảng không rò kết quả và kiểm tra ngày hiệu lực PASS. Index có 1.089 vector BGE-M3, nhưng môi trường chưa cài `sentence-transformers`, nên đường chạy là BM25 fallback, chưa phải phép đo vector hybrid.

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | | __/__ | | __/__ | __/__ | __/__ | đạt / chưa |
| 2 | | __/__ | | __/__ | __/__ | __/__ | đạt / chưa |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| vd: bịa nguồn *(ví dụ)* | | |
| vd: đoán khi thiếu thông tin *(ví dụ)* | | |
| | | |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: __ — vì sao là nhóm **đau nhất với người dùng**: __
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): __
- Kết quả: nhóm lỗi đó __/__ → __/__ · tổng __% → __%
- Câu nào **tệ đi** sau khi sửa: __

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: chưa có lượt model thật, không thể phân nhóm lỗi; chưa chạy được vector hybrid do thiếu `sentence-transformers`; effective_date còn thiếu ở Shopee 220, TikTok 263, Lazada 185 chunks nên lọc theo ngày chưa bao phủ toàn kho. Unit test liên kết fee rule với nguồn còn 1 lỗi: 28/57 `chunk_id` cũ không khớp kho chính sách mới, có thể làm mất liên kết nguồn khi tra phí.
- Nếu có thêm 1 tuần: __
