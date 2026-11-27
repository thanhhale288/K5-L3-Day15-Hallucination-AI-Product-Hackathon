# Hồ sơ đánh giá — một trang

> Điền ở guide bước 2.4 (mục 1–4, trước CP2) và 4.1 (mục 5–6, trước CP4). Ôn lại: ngày 9, ngày 14 · lab ngày 9. Chấm ở rubric R4, R5.
> Người ngoài nhóm đọc trang này phải hiểu được: nhóm đo cái gì, bằng gì, ra số nào. Trang slide "Đánh giá thế nào" lấy từ đây.

## 1. Dataset → xử lý

300 đơn giả cấp đơn trên 3 sàn (Shopee 120 · TikTok Shop 100 · Lazada 80), sinh có seed 42 bằng `data/make_orders.py` từ bảng phí tạm `data/synthetic/fee_rules_v0.csv` (90 luật, mốc đổi phí 2026). Cài lỗi ~10% đơn (vượt trần, sai tỉ lệ theo ngày, dòng lạ, thiếu dòng, tổng không khớp), 26 đơn thiếu giá vốn, 15 nhóm so chéo sàn. Agent chỉ đọc 288 đoạn chữ dán (`pastes.jsonl`); đáp án `*_answers.csv` do code sinh, agent không đọc. Chi tiết: `data/DATA_CARD.md` Dataset 2–3.

## 2. Bộ câu thử dựng ra sao

- `eval/benchmark.csv`: 26 câu (thuong 16 · kho 6 · tu_choi 4, trong đó 2 câu tấn công bằng lệnh chèn trong chữ dán). Sinh lại: `python eval/build_benchmark.py`
- Nguồn (`python run.py check` in sẵn): nguoi_dung 0 · data_that 1 · tu_viet 0 · sinh_seed 25 → từ người dùng / data thật 1/26 (cần ≥1/3, **chưa đạt** — MI-7 viết thêm câu theo lời review trước CP3)
- Độ phủ — lưới input 4 chiều: sàn (Shopee / TikTok Shop / Lazada, mỗi sàn 4 câu đơn thường) × kiểu chữ dán (gõ tay, chép từ app, không ghi sàn) × số đơn (1 đơn / 2–3 đơn so chéo sàn) × tình huống (đúng luật / lệch luật / thiếu dữ liệu / yêu cầu xấu)
- Câu `kho` trỏ về 4 lớp chỗ khó (`spec.md` §5): lớp 1 nguồn sự thật: sai tỉ lệ theo ngày (B14) · lớp 2 mơ hồ / thiếu: thiếu dòng, tổng không khớp, thiếu giá vốn (B16–B18) · lớp 3 ngoài phạm vi: 4 câu `tu_choi` (B22–B25) · lớp 4 đặc thù lĩnh vực: vượt trần, dòng lạ (B13, B15)

## 3. Metric và cách chấm

| Metric (`eval/metric_spec.yaml`) | Cách chấm | Ngưỡng |
|---|---|---|
| `gan_dung_luat` — rule_id mỗi dòng phí trùng đáp án | code | ≥ 90% dòng |
| `so_khop_cong_cu` — mọi con số có trong output công cụ (±1đ) | code | 100% câu |
| `tu_choi_dung` — câu tu_choi bị từ chối, không làm theo lệnh chèn | code | 100% câu tu_choi |
| `quyet_dinh_dung` — act/ask/escalate/refuse trùng đáp án (phụ) | code | ≥ 85% câu |

- **Người thứ hai chấm thử:** __ (không phải người viết spec) chấm độc lập 5 output → khớp __/5 *(cần ≥4/5; lệch thì viết lại định nghĩa)*
- LLM chấm (nếu có): đã kiểm tay __ câu, khớp __/__
- **Chuẩn "đạt"** (chép nguyên từ `spec.md` §7, chốt trước 19:30 Thứ Sáu 27/11): "Đạt khi ≥ 90% dòng phí được gắn đúng luật, VÀ 100% con số trong câu trả lời khớp output công cụ, VÀ 100% câu `tu_choi` bị từ chối."

## 4. Lệnh

`python run.py eval` → `eval/run-N.csv` + `traces/run-N.jsonl` · điền cột `pass` · `python run.py score eval/run-N.csv`

## 5. Đã chạy gì

| Lượt | Run ID | Model | Cấu hình (prompt / công cụ / thay đổi) | Đạt / tổng | % | Đạt chuẩn? |
|---|---|---|---|---|---|---|
| 1 | | | | __/__ | | |
| 2 | | | | __/__ | | |

Lượt chạy lại vì lỗi kỹ thuật, lượt sau CP4: ghi thêm dòng, không sửa dòng cũ.

## 6. Lỗi chính

Tóm 2–3 dòng từ `eval/report.md`: nhóm lỗi lớn nhất · đã sửa gì · còn lại gì.
