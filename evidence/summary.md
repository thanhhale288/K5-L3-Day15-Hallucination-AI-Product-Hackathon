# Tổng hợp bằng chứng pain

> Hà giữ. Chấm ở rubric R1. Số đếm chạy lại bằng `python evidence/count_reviews.py`; cách đếm ở `evidence/data-mining.md`.

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data: 900 review Google Play của 3 app người bán (x/N, cách đếm chạy lại được, ≥ 5 ví dụ) | ☑ | `evidence/data-mining.md`, `evidence/reviews/labels-ai.csv`, `evidence/count_reviews.py` |
| Phỏng vấn (≥ 3 người bán ngoài nhóm) | ☐ | Không làm: nhóm không quen người bán nào để hẹn phỏng vấn |
| Khảo sát (≥ 20 người ngoài nhóm, đúng người dùng) | ☐ | Chỉ tham khảo, không tính là bằng chứng (lý do ở mục 4) |

## 2. Số chính

- **Pain về tiền đã xác nhận: 88/900 review (9,8%)**. Ước lượng gồm cả phần từ khoá bỏ sót là ≈ 112/900 (≈ 12,4%) *(ước lượng, mẫu kiểm n = 100)*.
- **Shopee Seller Center là nơi than nhiều nhất:** 56/300 (18,7%) review than về tiền, trong đó 44/300 (14,7%) than phí sàn. TikTok Shop 14/300 (4,7%), Lazada 18/300 (6,0%).
- **Trong 88 review đó, khoản bị than nhiều nhất:** phí sàn 62 (70,5%), hoàn trả 30 (34,1%), tiền về / đối soát 20 (22,7%), quảng cáo 7, voucher / chương trình 6. 25/88 (28,4%) nói rõ là lỗ hoặc gần như không còn lãi.
- **Bộ lọc từ khoá chỉ là bước nháp:** 88/116 (75,9%) review được nó gắn nhãn tiền là đúng; nó bỏ sót 3/100 review trong phần còn lại.
- **Nhãn đã được người kiểm:** AI gán nhãn, Hà đọc lại 30 dòng (chọn theo 4 nhóm, có seed), khớp 28/30 (93%). 2 dòng lệch chỉ đổi chủ đề của review không phải pain, nên các số trên không đổi.

Không phỏng vấn nên không có bảng P1–P3.

## 3. Trích dẫn nguyên văn (≤ 2 câu, không tên người viết)

Tất cả lấy trên Google Play, xem ngày 27/11/2026. Mã `review_key` tra được trong `labels-ai.csv`.

1. "Ứng dụng thu phí quá thiếu minh bạch. Đề nghị Shopee xem xét lại các khoản phí và hiển thị rõ từng đơn: sản phẩm nào phát sinh phí Affiliate, Affiliate của ai, tỷ lệ bao nhiêu và số tiền bị trừ." — [Shopee Seller Center](https://play.google.com/store/apps/details?id=com.shopee.shopeeseller&hl=vi&gl=VN), 26/09/2026, 1★ (`f8d36f7bd98d`)
2. "tôi bán 1 sản phẩm giá 249k*2sl họ trừ phần trợ giá của shop 49k tổng phí trừ 133k khi tôi vào thắc mắc thì NV hỗ trợ ko trả lời được vì sao bị trừ nhiều như vậy." — [Shopee Seller Center](https://play.google.com/store/apps/details?id=com.shopee.shopeeseller&hl=vi&gl=VN), 26/06/2026, 1★ (`7ce0babeac94`)
3. "HÚT MÁU NGƯỜI QUÁ GHÊ, mé đơn 180k mà ăn tận 51k trong khi tik tok shop chỉ lấy phí 19k." — [Lazada Seller Center](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) (`5f2459e1da09`)
4. "đăng sản phẩm nhanh nhưng hay bị trừ phí lạ dù đã đăng kí gói hoàn phí ship đơn hoàn nhưng vẫn bị -25k -35k -30k????" — [TikTok Shop Seller Center](https://play.google.com/store/apps/details?id=com.tiktokshop.seller&hl=vi&gl=VN), 3★ (`0e68daaaa20e`)
5. "Tự động join các chương trình km rồi trừ phí khủng, 600gram trừ 250k phí vận chuyển, không giải quyết đền bù, chiếm đoạt tiền shop" — [Lazada Seller Center](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN), 1★ (`4069bda8600b`)
6. "phí đủ thứ từ đầu năm đến giờ tăng phí lên 2 lần cộng thêm phí đồng tài trợ + dồn chiếm hết 29%-31%." — [Shopee Seller Center](https://play.google.com/store/apps/details?id=com.shopee.shopeeseller&hl=vi&gl=VN), 1★ (`e8962e8c9398`)
7. "khách trả hàng là mất 58k nhé. bán ko lời mà thấy âm phủ luôn rồi" — [TikTok Shop Seller Center](https://play.google.com/store/apps/details?id=com.tiktokshop.seller&hl=vi&gl=VN), 1★ (`446971078d81`)

Ngày đăng của trích dẫn 3–7 ghi ở `evidence/data-mining.md` mục 4.

### Bối cảnh từ YouTube (không tính là bằng chứng)

- ["Vì Sao Nhiều Chủ Shop Muốn Thoát Khỏi Các Sàn Thương Mại Điện Tử Shopee, TiktokShop,.."](https://www.youtube.com/watch?v=oEwbf3F2oV0) (kênh Ếch Biết Tuốt, 15/10/2026 theo ghi chép của nhóm). Video nói *"bài toán… không nằm ở chỗ cãi nhau xem sàn thu phí bao nhiêu là đắt, mà là khoản phí đó mang lại bao nhiêu doanh thu và lợi nhuận tương xứng"*. Bình luận dưới video: "Tính ra thu về đc 70%"; "đổi trả là ác mộng".
- ["10 Chỉ Số Phải BIẾT khi bán hàng trên sàn TMĐT | Hiếu Suro"](https://www.youtube.com/watch?v=bZuylc8ZaO0). Video dạy 10 chỉ số, không có chỉ số nào tính lãi, và ROAS được tính trên GMV. Đây là lý do sản phẩm đổi sang **ROAS hoà vốn = 1 ÷ biên lãi trước quảng cáo**.

## 4. Các nguồn có khớp nhau không

Review nói phí bị trừ theo từng đơn mà không ai giải thích được (trích dẫn 1, 2, 4), và chương trình tự bật ăn vào lãi
(trích dẫn 5, 6). Video YouTube khớp ở ý "phí phải so với lợi nhuận nó mang lại". Video cũng cho thấy người bán đang
được dạy đo hiệu quả bằng doanh thu thay vì lãi.

**Khảo sát của nhóm chỉ để tham khảo, không đưa vào số chính:** form không rẽ nhánh nên người chưa từng bán vẫn trả lời
hết; câu 9–11 viết dạng khẳng định sẵn nên dễ kéo người trả lời về phía "đồng ý". Nếu dùng thì chỉ tính người chọn "Đang bán" hoặc "Đã từng bán".

## 5. Kết luận

Giả thuyết "chủ shop đa sàn bị trừ nhiều khoản trên từng đơn mà không biết khoản nào bắt buộc, khoản nào là chương
trình tự bật đang ăn lãi" **đúng về hướng**. Phàn nàn về tiền tập trung ở phí trên từng đơn và việc không ai giải
thích được khoản trừ, nhiều nhất ở Shopee.

Điều vẫn chưa biết:
- Bao nhiêu phần trăm người bán gặp pain này. Review chỉ cho thấy pain có thật, không đo được tỉ lệ.
- Họ mất bao nhiêu phút mỗi lần đối soát.
- Shop nhỏ có sẵn sàng dán chi tiết thanh toán vào một công cụ hay không.

Kiểm tiếp bằng 2–3 người bán dùng thử (`validation/log.md`).
