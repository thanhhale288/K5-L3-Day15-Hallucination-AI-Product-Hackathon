# Soát `data/fee_rules.csv` (TH-4 → HA-7)

Sinh bằng `python data/build_fee_rules.py`. Bảng được đối chiếu với kho chính sách gộp `data/policies/chunks.jsonl`.

- **Bản 1** (commit `6d91fba`) đối chiếu với kho cũ.
- **Bản 1.1** (28/11/2026) đối chiếu với corpus mới ở commit `741c0ab`. Corpus này gồm 1.089 chunk, trong đó Shopee lấy từ `banhang.shopee.vn/edu` và `help.shopee.vn`.

**Nguyên tắc:** tỉ lệ, trần, ngày và `rule_id` được **giữ đúng như bảng tạm v0**, vì đáp án `eval/benchmark.csv` và `data/synthetic/line_answers.csv` sinh từ các số đó. Bảng chỉ thêm `chunk_id` và `ten_cu`, và chỉ nâng `da_doi_chieu` khi trang chính thức khớp cả số lẫn ngày. Muốn sửa số theo các mục dưới thì phải **sinh lại data giả và đáp án cùng lúc** (TH-6, MI-7), không sửa riêng một bên.

## Tóm tắt (bản 1.1)

| Sàn | Số luật | Có `chunk_id` | `chinh_thuc` | `bao_chi` | `gia_dinh` |
|---|---|---|---|---|---|
| Shopee | 36 | 29 | 3 | 5 | 28 |
| TikTok Shop | 32 | 27 | 1 | 2 | 29 |
| Lazada | 23 | 0 | 0 | 0 | 23 |

Có 56 `chunk_id`. Cả 56 đều có trong corpus mới và đúng sàn (`tests/test_tools.py` kiểm điều này).

## Đổi ở bản 1.1: sửa liên kết theo corpus mới

Corpus mới không còn các bài `shopee-77243`, `shopee-77262` và `shopee-166085`. Ngoài ra, 2 ID vẫn còn tồn tại nhưng sau khi chunk lại đã trỏ sang nội dung khác. Tổng cộng **30 dòng** được sửa. Mọi đoạn thay thế đều đã được đọc tay.

| Luật (số dòng) | ID cũ | ID mới | Nội dung đoạn mới |
|---|---|---|---|
| Phí cố định, shop thường (12) | `shopee-77243#054` (không còn) | `shopee-10666#001` | Định nghĩa phí cố định, không ghi tỉ lệ |
| Phí cố định, Mall (12) | `shopee-77262#027` (không còn) | `shopee-21087#001` | Định nghĩa phí cố định Mall, không ghi tỉ lệ |
| Phí xử lý giao dịch 6%, shop thường (1) | `shopee-77243#053` (không còn) | `shopee-2150#002` | 6% từ 01/05/2026 (không thuộc Mall) |
| Phí xử lý giao dịch 6%, Mall (1) | `shopee-77262#026` (không còn) | `shopee-2150#002` | 6% từ 08/05/2026 (Shopee Mall) |
| Phí hạ tầng (1) | `shopee-77243#056` (không còn) | `shopee-25223#001` | "mức thu 3.000Đ … mỗi đơn hàng … tạo từ 01/07/2025" → nâng lên **`chinh_thuc`** |
| Tiếp thị liên kết (1) | `shopee-183831#004` (đã trôi sang mục "2.1 Thông tin đăng ký") | `shopee-183831#006` | Mục 4.2: Phí Hoa Hồng PPS = Tỷ Lệ Hoa Hồng × Giá Trị Mua Thuần |
| Phí vận chuyển trả hàng (1) | `shopee-77251#010` (đã trôi sang mục 7.2 "người bán **không** chịu") | `shopee-77251#009` | Mục 7.1: người bán chịu phí vận chuyển hoàn trả |
| Voucher đồng tài trợ (1) | `shopee-166085#007` (không còn) | **để trống** | Xem lệch số 2 bên dưới |

4 ID của TikTok Shop đã được kiểm lại nội dung và vẫn đúng.

## Khớp trang chính thức → `chinh_thuc`

- **Shopee · phí xử lý giao dịch 6%**: shop thường từ 01/05/2026, Mall từ 08/05/2026 (`shopee-2150#002`).
- **Shopee · phí hạ tầng 3.000đ/đơn từ 01/07/2025** (`shopee-25223#001`). Mới nâng ở bản 1.1.
- **TikTok Shop · phí xử lý đơn hàng 3.000đ/đơn từ 27/10/2025** (`tiktok-8858869405370113#004`). Luật này v0 chưa có; khi sinh lại đơn TikTok (TH-6) cần thêm dòng này.

## Corpus mới xác nhận số của v0 (đề xuất nâng `chinh_thuc`, chưa làm, cần Hà duyệt)

- **Shopee · Voucher Xtra 5,5%, trần 50.000đ/sản phẩm, từ 23/05/2026**: `shopee-18182#003` khớp đúng luật `shopee_voucher_xtra_2026-05-23`. Luật này đang để trống `chunk_id`, `da_doi_chieu=bao_chi`.
- **TikTok Shop · phí giao dịch 6% từ 09/05/2026**: `tiktok-8858869405370113#003` ghi "Từ ngày 09 tháng 05 năm 2026, phí suất của phí giao dịch là 6,00%". Điều này khớp mốc của v0, nên **mục "mốc 01/04 hay 09/05" ở bản 1 đã có câu trả lời là 09/05**. (Dòng "01/04/2026" ở `tiktok-753295858337537#002` là ngày áp dụng *công thức*.)

## Lệch giữa v0 và trang chính thức (cần Hà quyết)

1. **Shopee · tỉ lệ phí cố định theo ngành:** `shopee-27540` (shop thường) và `shopee-27541` (Mall), cùng hiệu lực từ 23/05/2026, có biểu phí theo ngành cấp 3. Ví dụ ngành Thời trang của shop thường ghi **12,5–13,5% trước 23/05/2026**, còn v0 ghi 10% đến 07/05 và 9% từ 08/05 *(tự ước tính)*. v0 cũng không có mốc 23/05/2026 (shop thường) và 29/05/2026 (Mall). Vì vậy luật phí cố định chỉ trỏ tới đoạn định nghĩa, **không trỏ tới biểu phí**.
2. **Shopee · voucher đồng tài trợ:** `shopee-26053#002` (từ 23/05/2026) ghi *người bán chịu **40%** giá trị mã, tối đa 50.000đ/sản phẩm*. v0 tính 50% và không có trần *(tự ước tính)*. Mọi đoạn của bài này đều ghi 40%, nên **`chunk_id` để trống** để agent không trích 40% trong khi code tính 50%. Khi sửa thì cần tách luật trước và từ 23/05/2026 (40%, trần 50.000đ/sp) rồi sinh lại data.
3. **Shopee · phí xử lý giao dịch:** công thức chính thức có cộng *phí vận chuyển người mua trả* vào căn cứ, còn v0 chỉ lấy *giá − voucher shop*. Đơn giả chưa có phí ship nên chưa lệch số.
4. **Shopee · tiếp thị liên kết:** mục 4.2 tính hoa hồng trên *Giá Trị Mua Thuần, chưa gồm GTGT*. v0 tính trên *giá − voucher shop*.
5. **TikTok Shop · phí giao dịch:** công thức chính thức tính trên *số tiền khách trả + chiết khấu của nền tảng − phần hoàn*, còn v0 tính trên *giá − voucher shop*.
6. **TikTok Shop · hoa hồng nền tảng:** mốc 03/07 (shop thường) và 03/08 (Mall) khớp tiêu đề tệp đính kèm. Tỉ lệ theo ngành nằm trong PDF chưa trích, nên vẫn là *(tự ước tính)*.

## Chưa kiểm lại trên corpus mới

- **Lazada:** corpus mới có 68 bài, và các chunk `lazada-phi-co-dinh-lazmall#…` mà bản 1 dùng để so sánh (LazMall 15–17,8% so với v0 9–11%) **không còn**. Toàn bộ 23 luật Lazada vẫn là `gia_dinh` và chưa gắn chunk. Cần soát lại trên corpus mới.
- Shopee: phí thanh toán 4,91% trước 24/04, thuế khấu trừ NĐ 117/2025. Corpus mới đã có `shopee-24204` và `shopee-24233` nhưng chưa được đối chiếu.
- TikTok Shop: Phí Voucher Extra, hoa hồng nhà sáng tạo, thuế khấu trừ. Đã có `tiktok-2632156783101712` nhưng chưa được đối chiếu.
