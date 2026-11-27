# Đào data — cách đếm và kết quả

> Điền ở guide bước 1.2. Ôn lại: ngày 2, ngày 6 · lab ngày 2, lab ngày 6.
> Không đào data thì xoá file này. Script / công thức đếm để trong repo (vd `evidence/count.py` hoặc ghi công thức Sheets ngay dưới), người khác chạy lại phải ra cùng số.
> Repo chỉ chứa số đã tổng hợp và vài dòng ví dụ — không chép lại nguyên file data.

## 1. Cách đếm — viết TRƯỚC khi chạy

- Data dùng: 300 review mới nhất Google Play của app Lazada Seller Center (`com.sc.lazada`), lấy ngày 2026-11-27.
- Đếm gì: review 1–2 sao · trên các dòng còn lại sau khử trùng và loại review rỗng/ngắn hơn 10 ký tự · không gán nhãn seller pain trong lượt này.
- **Mẫu số là gì:** N=168 review sau khử trùng nội dung và loại 31/199 dòng có `content_len < 10`; 101 dòng lặp trong lượt 300 được loại trước đó.
- Script / công thức: `evidence/crawl_lazada.py`; kết quả tổng hợp ở `data/lazada/reviews/lazada_crawl_summary.json`.

## 2. Đọc trước, đếm sau

Đã lấy 300 review; thống kê sao bên dưới chỉ mô tả tập review, chưa coi là bằng chứng seller pain. Chưa gán topic/is_seller_pain.

## 3. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| Review 1–2 sao | 81 / 168 | 48.2% | mẫu sau khử trùng + bỏ dòng ngắn |
| Review 3–5 sao | 87 / 168 | 51.8% | mẫu sau khử trùng + bỏ dòng ngắn |

Ghi dạng "x/N (y%)". "Nhiều bạn…" không phải số.

## 4. Ví dụ cụ thể

Các dòng ví dụ trong tập 1–2 sao (chưa gán `is_seller_pain`):

1. `128e47368b56` · 2026-11-23 · Lazada Seller Center · [Google Play](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) · xem 2026-11-27.
2. `81afec992b3c` · 2026-11-06 · Lazada Seller Center · [Google Play](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) · xem 2026-11-27.
3. `0c0e177a93a0` · 2026-09-28 · Lazada Seller Center · [Google Play](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) · xem 2026-11-27.
4. `662b4d2c2eda` · 2026-07-04 · Lazada Seller Center · [Google Play](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) · xem 2026-11-27.
5. `3c4dc4ea7cd6` · 2026-06-19 · Lazada Seller Center · [Google Play](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) · xem 2026-11-27.

## 5. Giới hạn của data

Data cho biết người ta **làm gì**, không cho biết **vì sao**. Review Play nghiêng về người bực, không phân biệt quy mô shop, và có thể nói về app thay vì phí; chưa có nhãn người kiểm để xác định seller pain.
→ Kiểm lại bằng phỏng vấn / khảo sát nào: cần gán nhãn thủ công theo định nghĩa topic trong crawl-spec trước khi dùng làm tỷ lệ pain.
