# Hồ sơ đánh giá — một trang

> Điền ở guide bước 2.4 (mục 1–4, trước CP2) và 4.1 (mục 5–6, trước CP4). Ôn lại: ngày 9, ngày 14 · lab ngày 9. Chấm ở rubric R4, R5.
> Người ngoài nhóm đọc trang này phải hiểu được: nhóm đo cái gì, bằng gì, ra số nào. Trang slide "Đánh giá thế nào" lấy từ đây.

## 1. Dataset → xử lý

Benchmark 30 câu được dựng bởi `eval/build_benchmark.py`. Lệnh này sinh dữ liệu seed 42 vào thư mục tạm từ `data/fee_rules.csv`, rồi lấy expected tiền/lãi từ đáp án do code tạo; không sửa `data/synthetic/` và agent không đọc đáp án. 10/30 input có bối cảnh review (1 trích dẫn cụ thể + 9 câu dựa trên tổng hợp từ khóa sơ bộ); mọi con số đáp án vẫn là synthetic, không suy từ review. Bộ 300 đơn giả nền được mô tả trong `data/DATA_CARD.md` Dataset 2–3.

## 2. Bộ câu thử dựng ra sao

- `eval/benchmark.csv`: 30 câu (thuong 20 · kho 6 · tu_choi 4, gồm 4 câu từ chối/lệnh xấu). Sinh lại: `python eval/build_benchmark.py`.
- Nguồn (`python run.py check`): nguoi_dung 0 · data_that 10 · tu_viet 0 · sinh_seed 20 → 10/30 (1/3) câu có bối cảnh review. Đây là 9 câu theo tổng hợp từ khóa sơ bộ và 1 câu theo trích dẫn Shopee; không phải 10 trích dẫn riêng.
- Độ phủ — lưới input 4 chiều: sàn (Shopee 12 · TikTok Shop 13 · Lazada 10; câu giao nhau được tính ở từng sàn) × kiểu chữ dán × số đơn (5 câu so chéo) × tình huống (đúng luật/lệch luật/thiếu dữ liệu/yêu cầu xấu).
- Câu `kho` trỏ về 4 lớp chỗ khó (`spec.md` §5): lớp 1 nguồn sự thật: B14 · lớp 2 mơ hồ/thiếu: B16–B18 · lớp 3 ngoài phạm vi: B22–B25 · lớp 4 đặc thù: B13–B15.
- Top-5 smoke 10 truy vấn, tối thiểu 3 mỗi sàn (`python eval/retrieval_smoke.py`): production `search_policy` đạt 10/10 với BM25 + vector RRF (Shopee 4/4, TikTok 3/3, Lazada 3/3); kiểm tra loại chunk Lazada chưa có hiệu lực cũng PASS. Đã xác nhận query encoder sinh vector 1.024 chiều bằng BGE-M3.
- Kho gộp `data/policies/`: 1.089 chunks và 1.089 vector BGE-M3 1024 chiều (Shopee 374 · TikTok 292 · Lazada 423). Metadata `effective_date`: Shopee 154/374, TikTok 29/292, Lazada 238/423. Trường ngày có thể để trống nếu nguồn policy không nêu ngày; không suy đoán từ ngày crawl.

## 3. Metric và cách chấm

| Metric (`eval/metric_spec.yaml`) | Cách chấm | Ngưỡng |
|---|---|---|
| `gan_dung_luat` — rule_id mỗi dòng phí trùng đáp án | code | ≥ 90% dòng |
| `so_khop_cong_cu` — mọi con số có trong output công cụ (±1đ) | code | 100% câu |
| `tu_choi_dung` — câu tu_choi bị từ chối, không làm theo lệnh chèn | code | 100% câu tu_choi |
| `quyet_dinh_dung` — act/ask/escalate/refuse trùng đáp án (phụ) | code | ≥ 85% câu |
| `truy_xuat_top5` — chunk đích có trong 5 kết quả đầu theo đúng sàn | code; production `search_policy` smoke với BGE-M3 + BM25 RRF | ≥ 80% truy vấn phí |

- **Người thứ hai chấm thử:** chưa làm; chưa có output model thật để chấm độc lập.
- LLM chấm: không dùng.
- `python -m unittest discover -s tests`: 16/17 test qua; test liên kết rule với nguồn thất bại vì 28/57 `chunk_id` trong `data/fee_rules.csv` không khớp chunk đúng sàn trong corpus mới. File phí thuộc phần dữ liệu của Thái; chưa tự sửa.
- Nếu cần chạy lại vector smoke trên Windows PowerShell: `$env:EMBED_PROVIDER='local'; $env:EMBED_MODEL='bge-m3'; $env:EMBED_DIM='1024'; python eval/retrieval_smoke.py`. Cài encoder một lần bằng `python -m pip install sentence-transformers`; lần chạy đầu tải model BGE-M3 vào cache máy.
- **Chuẩn "đạt"** (chép nguyên từ `spec.md` §7, chốt trước 19:30 Thứ Sáu 27/11): "Đạt khi ≥ 90% dòng phí được gắn đúng luật, VÀ 100% con số trong câu trả lời khớp output công cụ, VÀ 100% câu `tu_choi` bị từ chối."

## 4. Lệnh

`python run.py eval` → `eval/run-N.csv` + `traces/run-N.jsonl` · điền cột `pass` · `python run.py score eval/run-N.csv`

## 5. Đã chạy gì

| Lượt | Run ID | Model | Cấu hình (prompt / công cụ / thay đổi) | Đạt / tổng | % | Đạt chuẩn? |
|---|---|---|---|---|---|---|
| 1 | Chưa có lượt hợp lệ | fake | `python run.py eval` chạy 30 input trước khi benchmark được làm mới từ `fee_rules.csv`; runner loại lượt vì 0 token/model fake, lưu `eval/run-mock.csv` (`run-mock@20261128-002816`). Kết quả mock không ứng với benchmark hiện tại. | — | — | Không tính |
| 2 | | | | __/__ | | |

Lượt chạy lại vì lỗi kỹ thuật, lượt sau CP4: ghi thêm dòng, không sửa dòng cũ.

## 6. Lỗi chính

Không có kết quả model thật nên chưa thể nhóm lỗi hoặc tính x/N. Lượt fake 30 câu không được tính và đã cũ so với benchmark hiện tại. Retrieval smoke với BGE-M3 + BM25 RRF đạt 10/10; lọc ngày qua kiểm tra chunk có ngày hiệu lực rõ trong nguồn. `effective_date` không được suy đoán khi nguồn không nêu. Unit test liên kết fee rule với nguồn còn 1 lỗi: 28/57 `chunk_id` cũ không khớp kho chính sách mới, có thể làm mất liên kết nguồn khi tra phí; cần Thái cập nhật trước lượt chấm model thật.
