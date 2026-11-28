# Tính lại giá cho simulate-1@20261128-105032

Do `python cost/reprice.py cost/simulate-1.csv --rate-from eval/run-2.csv` sinh ra — không sửa tay. Token lấy nguyên từ `simulate-1.csv` (đo thật); giá, số người dùng và persona lấy từ `cost/personas.yaml` hiện tại; bảng tính bằng hàm `summarize` của khung.

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
| deepseek-flash cao điểm (V4.1-Flash-1017) (vào 0.3 · ra 1.2 $/1M) | $0.0221 (≈ 552 ₫) | $0.0221 (≈ 552 ₫) | $0.0170 (≈ 425 ₫) | $237.93 (≈ 5.948.224 ₫) | $1,189.64 (≈ 29.741.122 ₫) | $3,568.93 (≈ 89.223.366 ₫) | $0.1322 (≈ 3.305 ₫) |
| deepseek-flash thấp điểm (vào 0.15 · ra 0.6 $/1M) | $0.0110 (≈ 276 ₫) | $0.0110 (≈ 276 ₫) | $0.0085 (≈ 212 ₫) | $118.96 (≈ 2.974.112 ₫) | $594.82 (≈ 14.870.561 ₫) | $1,784.47 (≈ 44.611.683 ₫) | $0.0661 (≈ 1.652 ₫) |
| deepseek-v4-pro cao điểm (V4-Pro-0813) (vào 1.32 · ra 3.96 $/1M) | $0.0924 (≈ 2.309 ₫) | $0.0924 (≈ 2.309 ₫) | $0.0711 (≈ 1.777 ₫) | $997.05 (≈ 24.926.364 ₫) | $4,985.27 (≈ 124.631.822 ₫) | $14,955.82 (≈ 373.895.467 ₫) | $0.5539 (≈ 13.848 ₫) |
| deepseek-v4-pro thấp điểm (vào 0.66 · ra 1.98 $/1M) | $0.0462 (≈ 1.155 ₫) | $0.0462 (≈ 1.155 ₫) | $0.0355 (≈ 888 ₫) | $498.53 (≈ 12.463.182 ₫) | $2,492.64 (≈ 62.315.911 ₫) | $7,477.91 (≈ 186.947.734 ₫) | $0.2770 (≈ 6.924 ₫) |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.3) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: deepseek-chat. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
- Tỷ giá: 1 USD = 25.000 ₫ ((tự ước tính) làm tròn, chưa lấy tỷ giá ngân hàng ngày chạy).
