# Tóm tắt mô phỏng simulate-1@20261128-105032

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| soi_1_don | 21 | 1 | 47528 | 2488 | 6.1 | 14.4 |
| so_3_san | 10 | 1 | 69214 | 6732 | 6.1 | 37.2 |
| thieu_gia_von | 15 | 2 | 71077 | 3372 | 9.9 | 21.8 |
| dong_la | 4 | 1 | 49413 | 2896 | 6.0 | 17.0 |

Tỉ lệ đạt dùng để tính: 30/30 (100%) — lượt run-2@20261128-094309

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-2.csv (--rate-from). ⚠️ Lượt này chạy bằng gpt-6.2-sol, mô phỏng đo trên deepseek-chat — khác model.

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (1.800 người) | Chi phí / tháng — cơ sở (9.000 người) | Chi phí / tháng — cao (27.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| deepseek-chat (V4 Flash) (vào 0.14 · ra 0.28 $/1M) | $0.0093 (≈ 232 ₫) | $0.0093 (≈ 232 ₫) | $0.0071 (≈ 179 ₫) | $100.46 (≈ 2.511.573 ₫) | $502.31 (≈ 12.557.863 ₫) | $1,506.94 (≈ 37.673.589 ₫) | $0.0558 (≈ 1.395 ₫) |
| deepseek-v4.1-flash giờ cao điểm (vào 0.3 · ra 1.2 $/1M) | $0.0221 (≈ 552 ₫) | $0.0221 (≈ 552 ₫) | $0.0170 (≈ 425 ₫) | $237.93 (≈ 5.948.224 ₫) | $1,189.64 (≈ 29.741.122 ₫) | $3,568.93 (≈ 89.223.366 ₫) | $0.1322 (≈ 3.305 ₫) |
| deepseek-v4-pro (vào 1.32 · ra 3.96 $/1M) | $0.0924 (≈ 2.309 ₫) | $0.0924 (≈ 2.309 ₫) | $0.0711 (≈ 1.777 ₫) | $997.05 (≈ 24.926.364 ₫) | $4,985.27 (≈ 124.631.822 ₫) | $14,955.82 (≈ 373.895.467 ₫) | $0.5539 (≈ 13.848 ₫) |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.3) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: deepseek-chat. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
- Tỷ giá: 1 USD = 25.000 ₫ ((tự ước tính) làm tròn, chưa lấy tỷ giá ngân hàng ngày chạy).
