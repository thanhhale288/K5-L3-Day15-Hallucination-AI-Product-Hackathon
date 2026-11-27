# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Dataset 1 · Review Lazada Seller Center (Google Play)

| | |
|---|---|
| Dùng để làm gì | dữ liệu thăm dò để gán nhãn seller pain; chưa dùng làm số liệu pain đã kiểm chứng |
| Từ đâu | Google Play, app `com.sc.lazada`, [Lazada Seller Center](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) |
| Xử lý những bước gì | lấy 300 review mới nhất (`vi`, `vn`); bỏ tên/ảnh; hash ID; NFC + gộp khoảng trắng; khử trùng ID và nội dung; che SĐT/email/mã dài/link; giữ dòng ngắn nhưng loại khỏi mẫu số (script: `evidence/crawl_lazada.py`) |
| Số dòng / số đoạn | 300 lấy về; 101 trùng bỏ; 199 dòng còn; 31 dòng ngắn loại khỏi mẫu số; N=168 hợp lệ. Review 1–2 sao: 81/168 (48.2%). Khoảng ngày review hợp lệ: xem `data/lazada/reviews/lazada_crawl_summary.json`. |
| Phiên bản / ngày lấy | `google-play-scraper==1.2.7` · 2026-11-27 · newest |
| Nhãn | dữ liệu thật công khai; chưa gán nhãn |
| Giới hạn | review Play có selection bias về người bực; không phân biệt shop nhỏ/lớn, và có thể nói về app thay vì phí; khử trùng nội dung làm mẫu sau lọc nhỏ hơn 300 |

**Data `synthetic` (nhóm tự sinh):** ghi cách sinh (prompt / script), seed, người kiểm, số dòng đã kiểm tay. Data tự dựng **không phải bằng chứng pain**.

## Dataset 2 · Chính sách Lazada

| | |
|---|---|
| Dùng để làm gì | nguồn dự kiến cho kho chính sách RAG |
| Từ đâu | các URL công khai trong `data/lazada/policies/manifest.csv` |
| Xử lý những bước gì | đã thử tải HTML công khai; trang trả khung ứng dụng JavaScript, không có nội dung bài chính sách trong HTML tĩnh |
| Số dòng / số đoạn | 4 URL đã ghi manifest; 0 chunk hợp lệ; `data/lazada/policies/chunks.jsonl` để trống |
| Phiên bản / ngày lấy | 2026-11-27 |
| Nhãn | dữ liệu chính sách chưa được thu thập |
| Giới hạn | chưa dùng các URL này làm căn cứ trả lời; cần lấy nội dung bài từ trang render đầy đủ rồi làm sạch và chunk |
