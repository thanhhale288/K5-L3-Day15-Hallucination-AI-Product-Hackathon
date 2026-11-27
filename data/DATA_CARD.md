# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Dataset 1 · Review app người bán (bằng chứng pain)

| | |
|---|---|
| Dùng để làm gì | đào bằng chứng pain (`evidence/`), ≥ 1/3 câu thử viết theo lời review |
| Từ đâu | Google Play, 300 review mới nhất × 3 app: `com.shopee.shopeeseller`, `com.tiktokshop.seller`, `com.sc.lazada` (lang `vi`, country `vn`, sort NEWEST) |
| Xử lý những bước gì | bỏ tên/ảnh người viết, băm `reviewId`, che SĐT/email (script: `evidence/crawl_reviews.py`); bản Lazada theo `crawl-spec.md` ở `data/lazada/reviews/` |
| Số dòng / số đoạn | 900 (hợp lệ sau khi bỏ trùng và review < 10 ký tự: Shopee 267, TikTok 173, Lazada 168) |
| Phiên bản / ngày lấy | 27/11/2026 · `google-play-scraper==1.2.7` |
| Nhãn | thật |
| Giới hạn | nghiêng về người đang bực; không phân biệt shop nhỏ/lớn; nhiều review nói về lỗi app; mẫu Lazada trải từ 06/2024. Toàn văn không commit (`raw-*`). Đếm theo từ khoá mới là sơ bộ, đang đọc tay |

## Dataset 2 · Bảng phí tạm v0 (`data/synthetic/fee_rules_v0.csv`)

| | |
|---|---|
| Dùng để làm gì | nguồn để TÍNH phí cho công cụ (`lookup_fee_rule`, `expected_amount`) và cho mọi script sinh data, đến khi có `data/fee_rules.csv` chính thức |
| Từ đâu | nhóm tự dựng: mốc ngày đổi phí 2026 lấy từ báo chí / blog (`CONTEXT.md`), tỉ lệ theo ngành tự ước tính (script: `data/fee_engine.py --write-v0`) |
| Xử lý những bước gì | 3 sàn × 6 ngành × loại shop × khoảng hiệu lực; kiểm bằng đơn mẫu H4 (`python data/fee_engine.py --check` → 123.520 / 28.520) |
| Số dòng / số đoạn | 90 luật |
| Phiên bản / ngày lấy | v0 · 27/11/2026 |
| Nhãn | `synthetic` — cột `da_doi_chieu`: `bao_chi` hoặc `gia_dinh`, **không có dòng `chinh_thuc`** |
| Giới hạn | chưa khớp trang chính sách đã crawl; tỉ lệ Lazada và hoa hồng theo ngành của TikTok là giả định; chưa có phí ship, phí quảng cáo theo đơn |

## Dataset 3 · Đơn giả cấp đơn 3 sàn (`data/synthetic/`)

| | |
|---|---|
| Dùng để làm gì | đầu vào cho bản chạy thử và bộ câu thử (đáp án do code sinh) |
| Từ đâu | sinh có seed: `python data/make_orders.py --seed 42` (đọc bảng phí ở Dataset 2) |
| Xử lý những bước gì | 8 shop · 41 sản phẩm · 109 listing → 300 đơn (Shopee 120 · TikTok Shop 100 · Lazada 80), 03–11/2026; cài lỗi ~10% (vượt trần 8 · sai tỉ lệ theo ngày 8 · dòng lạ 7 · thiếu dòng 4 · tổng không khớp 4); 26 đơn thiếu giá vốn; 11 đơn dùng tên phí cũ; 15 nhóm so chéo sàn; 288 đoạn chữ dán (`pastes.jsonl`) |
| Số dòng / số đoạn | 300 đơn · 288 đoạn dán |
| Phiên bản / ngày lấy | seed 42 · 27/11/2026 |
| Nhãn | `synthetic`. File agent đọc: `shops, products, listings, orders, order_lines, pastes`. **Đáp án — agent không đọc:** `order_answers, line_answers, paste_answers` |
| Giới hạn | định dạng chữ dán là nhóm tự dựng, chưa đối chiếu app thật; mỗi đơn 1 sản phẩm; chưa có phí vận chuyển người bán chịu |

## Dataset 4 · File export mẫu để demo import (`data/demo_import/`)

| | |
|---|---|
| Dùng để làm gì | demo luồng "chủ shop tải file export tháng → hệ thống phân tích" (`data/import_export.py`) |
| Từ đâu | sinh có seed: `python data/make_demo_import.py` (cần `openpyxl`) |
| Xử lý những bước gì | Shop Demo, 11/2026: Shopee 262 · TikTok Shop 185 · Lazada 90 đơn; 3 chiến dịch quảng cáo; file giá vốn; 6 câu chuyện cài sẵn (xem README) |
| Số dòng / số đoạn | 537 đơn |
| Phiên bản / ngày lấy | seed 42 · 27/11/2026 |
| Nhãn | `synthetic`. Đáp án `_dap_an_2026-11.json` — agent không đọc |
| Giới hạn | tên cột **mô phỏng**, không phải định dạng export chính thức; kết quả import file thật ghi vào `data/imported/` (không commit) |

## Dataset 5 · Ngữ cảnh shop theo tháng (`data/synthetic/stores.csv`, `store_months.csv`)

| | |
|---|---|
| Dùng để làm gì | ngữ cảnh shop, persona chi phí, câu chuyện demo (hướng cũ, không dùng để chấm) |
| Từ đâu | sinh có seed: `python data/generate_synthetic.py --dirty` (seed 42). File `07_Ecommerce_Seller_Store.xlsx` là nguồn ngoài nhóm tự tìm (data luyện tập giả lập), chỉ phân tích, không dùng làm đầu vào |
| Số dòng / số đoạn | 150 shop × 12 tháng = 1.800 dòng |
| Nhãn | `synthetic` |
| Giới hạn | bảng phí mốc 2025 (chưa đọc `fee_rules`); cấp tháng, không có đơn |

**Data `synthetic`:** tất cả các bộ trên trừ Dataset 1 là nhóm tự sinh bằng script có seed, chạy lại ra cùng file. **Không phải bằng chứng pain.** Người kiểm tay: __ (ghi số dòng đã kiểm).
