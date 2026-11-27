# Soát `data/fee_rules.csv` bản 1 (TH-4 → HA-7)

Sinh bằng `python data/build_fee_rules.py`, đối chiếu với kho chính sách gộp `data/policies/chunks.jsonl` (ngày crawl 27/11/2026).

**Nguyên tắc bản 1:** tỉ lệ, trần, ngày và `rule_id` **giữ đúng như bảng tạm v0**, vì đáp án `eval/benchmark.csv` và `data/synthetic/line_answers.csv` được sinh từ các số đó. Bản này chỉ thêm `chunk_id`, `ten_cu` và nâng `da_doi_chieu` ở chỗ trang chính thức khớp cả số lẫn ngày. Muốn sửa số theo các mục dưới đây thì phải **sinh lại data giả và đáp án cùng lúc** (TH-6, MI-7), không sửa riêng một bên.

## Tóm tắt

| Sàn | Số luật | Có `chunk_id` | `chinh_thuc` | `bao_chi` | `gia_dinh` |
|---|---|---|---|---|---|
| Shopee | 36 | 30 | 2 | 6 | 28 |
| TikTok Shop | 32 | 27 | 1 | 2 | 29 |
| Lazada | 23 | 0 | 0 | 0 | 23 |

## Khớp trang chính thức → `chinh_thuc`

- **Shopee · phí xử lý giao dịch 6%** (shop thường từ 01/05/2026; Mall từ 08/05/2026). Nguồn: `shopee-77243#053` (Điều khoản dịch vụ §16, mọi phương thức thanh toán 6%) và `shopee-77262#026` (Điều khoản Shopee Mall 2.12.1, hiệu lực 08/05/2026).
- **TikTok Shop · phí xử lý đơn hàng 3.000đ/đơn từ 27/10/2025** (`tiktok-8858869405370113#004`). **Luật mới**, v0 chưa có. Đơn giả hiện tại chưa có dòng này, nên khi sinh lại đơn TikTok (TH-6) cần thêm vào.

## Lệch giữa v0 và trang chính thức (cần Hà quyết)

1. **TikTok · phí giao dịch:** v0 ghi 5% đến 08/05 và 6% từ 09/05/2026 (theo báo). Trang chính thức (`tiktok-753295858337537#002`) ghi công thức "từ 00:00 ngày 01/04/2026" và ví dụ dùng **6,00%**. Mốc 6% có thể là 01/04 chứ không phải 09/05. Đơn TikTok đặt từ 01/04 đến 08/05 đang bị tính 5%.
   Công thức chính thức tính trên *số tiền khách trả + chiết khấu của nền tảng − phần hoàn*, còn v0 tính trên *giá − voucher shop*.
2. **Shopee · phí xử lý giao dịch:** công thức chính thức có cộng *phí vận chuyển người mua trả* vào căn cứ. v0 chỉ lấy *giá − voucher shop*. Đơn giả chưa có phí ship nên chưa lệch số.
3. **Shopee · voucher đồng tài trợ:** trang chính thức (`shopee-166085#007`, hiệu lực 23/05/2026) có **trần 50.000đ mỗi sản phẩm** người bán chịu. v0 chưa có trần. Đơn giả tối đa 15.000đ nên chưa lệch số. Tỉ lệ chia sẻ 50% là *(tự ước tính)*.
4. **Lazada · phí cố định LazMall (từ 04/06/2026):** bảng chính thức (`lazada-phi-co-dinh-lazmall#001…`) ghi khoảng **15–17,8%** cho Thời trang và 2,9–20,8% cho Điện tử (theo ngành cấp 3, đã gồm GTGT). v0 ghi 9–11% *(tự ước tính)*. Đây là chỗ lệch lớn nhất. Vì vậy **chưa gắn `chunk_id`**, tránh để agent trích đoạn ghi số khác với số code tính.
5. **TikTok · hoa hồng nền tảng:** mốc 03/07 (shop thường) và 03/08 (Mall) khớp tiêu đề tệp đính kèm "phí suất tiêu chuẩn từ 3-7-2026 và phí suất mall từ 3-8-2026". Nhưng **tỉ lệ theo ngành nằm trong PDF chưa trích**, nên tỉ lệ v0 vẫn là *(tự ước tính)*. Có thêm mốc 20/10/2026 cho Mall ngành Sách (không thuộc 6 ngành của bộ data giả).

## Chưa có nguồn trong kho (giữ `bao_chi` / `gia_dinh`, `chunk_id` để trống)

- Shopee: Voucher Xtra (không đoạn nào trong kho Seller nhắc "Xtra"), phí thanh toán 4,91% trước 24/04, tỉ lệ phí cố định theo ngành, thuế khấu trừ NĐ 117/2025.
- TikTok Shop: Phí Voucher Extra, hoa hồng nhà sáng tạo, thuế khấu trừ.
- Lazada: phí thanh toán 4%, Freeship Max 5% trần 40.000đ, affiliate, phí cố định shop thường. Kho Lazada mới có 4 bài; bài "Điều khoản dịch vụ Nhà Bán Hàng (hiệu lực 29/09/2026)" có trong manifest nhưng **chưa được chunk**.

## Đề xuất crawl thêm (bạn phụ trách sàn)

- Lazada: chunk bài Điều khoản 29/09/2026 và trang biểu phí thanh toán / Freeship Max.
- Shopee: bài biểu phí cố định theo ngành, bài Voucher Xtra, bài phí dịch vụ hạ tầng.
- TikTok Shop: trích nội dung 2 PDF phí suất hoa hồng.
