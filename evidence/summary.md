# Tổng hợp bằng chứng pain

> Hà giữ file này, chấm ở rubric R1.
> - Chạy lại số đếm: `python evidence/count_reviews.py`. Cách đếm chi tiết: `evidence/data-mining.md`.
> - Kiểm trích dẫn có đúng nguyên văn và không quá 2 câu: `python evidence/check_quotes.py` (cần file thô, xem mục 3).

## 1. Nguồn đã dùng và đối chiếu ngưỡng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| **Đào data:** 900 review Google Play của 3 app người bán | ☑ **Đạt** (đối chiếu từng tiêu chí ở bảng dưới) | `evidence/data-mining.md`, `evidence/reviews/labels-ai.csv`, `evidence/reviews/manifest.csv`, `evidence/count_reviews.py` |
| Phỏng vấn (≥ 3 người bán ngoài nhóm) | ☐ | Không làm: nhóm không quen người bán nào để hẹn phỏng vấn |
| Khảo sát (≥ 20 người ngoài nhóm, đúng người dùng) | ☐ | Chỉ tham khảo, không tính là bằng chứng (lý do ở mục 4) |

Ngưỡng đào data (guide 1.2, rubric R1) và chỗ đáp ứng:

| Tiêu chí | Đáp ứng ở đâu |
|---|---|
| Đếm được: **x/N và %**, N là toàn bộ review đã đọc, kể cả review không liên quan | Mục 2 (mẫu số 900, và 300 mỗi app) |
| **Cách chọn mẫu và cách đếm ghi trước** khi gán nhãn | Mục 2 bên dưới; chi tiết ở `data-mining.md` §1 |
| **Mỗi nhãn có một câu định nghĩa** | `data-mining.md` §1, bảng "Định nghĩa nhãn" |
| **Người khác chạy lại được** | `crawl_reviews.py` (lấy review) → `labels-ai.csv` (nhãn từng review) → `count_reviews.py` (in mọi số ở mục 2) |
| **≥ 5 ví dụ / trích dẫn nguyên văn**, có nguồn, bỏ tên, mỗi review ≤ 2 câu, có link và ngày xem | Mục 3: 7 trích dẫn, đủ 3 app |
| **Ghi giới hạn** của data | Mục 5 và `data-mining.md` §5 |
| Không dùng nguồn không được tính (người trong nhóm, data giả lập, trò chuyện với AI) | Chỉ review công khai của người bán thật. Data giả trong `data/synthetic/` không dùng ở đây |

## 2. Cách chọn mẫu và số chính

**Mẫu (chốt trước khi đọc):**
- Lấy **300 review mới nhất** của mỗi app trên Google Play, **mọi mức sao**, lấy ngày 27/11/2026 bằng `evidence/crawl_reviews.py`. Tổng **N = 900**.
- Ba app:
  - Shopee Seller Center (`com.shopee.shopeeseller`), 11/01 → 26/11/2026
  - TikTok Shop Seller Center (`com.tiktokshop.seller`), 10/07 → 26/11/2026
  - Lazada Seller Center (`com.sc.lazada`), 07/06/2024 → 22/11/2026
- Khoảng ngày lấy từ `evidence/reviews/manifest.csv`.

**Cách đếm (chốt trước khi gán nhãn):**
- Bộ lọc từ khoá chọn 116/900 review có nhãn tiền.
- Gán nhãn đầy đủ trên 2 mẫu:
  - **Mẫu A:** cả 116 review đó.
  - **Mẫu B:** 100 review chọn ngẫu nhiên trong 784 review còn lại (seed 42).
- **Pain về tiền** = người viết là người bán **và** có ít nhất 1 nhãn tiền: phí sàn, tiền về / đối soát, hoàn trả, quảng cáo, voucher / chương trình.

**Số chính** (`python evidence/count_reviews.py`):
- **Pain về tiền đã xác nhận: 88/900 review (9,8%).**
  - Nếu tính cả phần bộ lọc từ khoá bỏ sót thì ước lượng ≈ 112/900 (≈ 12,4%) *(ước lượng, mẫu B n = 100)*.
- **Shopee Seller Center là nơi than nhiều nhất:** 56/300 (18,7%) review than về tiền, trong đó 44/300 (14,7%) than phí sàn.
  - TikTok Shop: 14/300 (4,7%).
  - Lazada: 18/300 (6,0%).
- **Trong 88 review đó, khoản bị than nhiều nhất** (một review có thể có nhiều nhãn):
  - phí sàn 62 (70,5%)
  - hoàn trả 30 (34,1%)
  - tiền về / đối soát 20 (22,7%)
  - quảng cáo 7 (8,0%)
  - voucher / chương trình 6 (6,8%)
- **25/88 (28,4%)** nói rõ là lỗ hoặc gần như không còn lãi. **85/88 (96,6%)** là review từ 3 sao trở xuống.
- **Bộ lọc từ khoá chỉ là bước nháp:** 88/116 (75,9%) review nó gắn nhãn tiền là đúng; nó bỏ sót 3/100 review trong phần còn lại.
- **Nhãn đã được người kiểm:** AI gán nhãn, Hà đọc lại 30 dòng (chọn theo 4 nhóm, có seed), khớp 28/30 (93%). 2 dòng lệch chỉ đổi chủ đề của review không phải pain, nên các số trên không đổi.

Không phỏng vấn nên không có bảng P1–P3.

## 3. Trích dẫn nguyên văn (≤ 2 câu mỗi review, không tên người viết)

- Tất cả trích từ Google Play, **ngày xem 27/11/2026**. Ngày ghi trong từng dòng là ngày đăng review.
- Mã `review_key` tra được trong `evidence/reviews/labels-ai.csv` (app, ngày, số sao, nhãn).
- Chính tả và viết hoa được giữ nguyên như người viết.

1. "Ứng dụng thu phí quá thiếu minh bạch. Đề nghị Shopee xem xét lại các khoản phí và hiển thị rõ từng đơn: sản phẩm nào phát sinh phí Affiliate, Affiliate của ai, tỷ lệ bao nhiêu và số tiền bị trừ."
   — [Shopee Seller Center](https://play.google.com/store/apps/details?id=com.shopee.shopeeseller&hl=vi&gl=VN) · đăng 26/09/2026 · 1★ · nhãn `phi_san`, `tien_ve_doi_soat` · (`f8d36f7bd98d`)
2. "tôi bán 1 sản phẩm giá 249k*2sl họ trừ phần trợ giá của shop 49k tổng phí trừ 133k khi tôi vào thắc mắc thì NV hỗ trợ ko trả lời được vì sao bị trừ nhiều như vậy."
   — [Shopee Seller Center](https://play.google.com/store/apps/details?id=com.shopee.shopeeseller&hl=vi&gl=VN) · đăng 26/06/2026 · 1★ · nhãn `phi_san`, `tien_ve_doi_soat`, `voucher_khuyen_mai` · (`7ce0babeac94`)
3. "phí đủ thứ từ đầu năm đến giờ tăng phí lên 2 lần cộng thêm phí đồng tài trợ + dồn chiếm hết 29%-31%."
   — [Shopee Seller Center](https://play.google.com/store/apps/details?id=com.shopee.shopeeseller&hl=vi&gl=VN) · đăng 18/06/2026 · 1★ · nhãn `phi_san`, `voucher_khuyen_mai` · (`e8962e8c9398`)
4. "đăng sản phẩm nhanh nhưng hay bị trừ phí lạ dù đã đăng kí gói hoàn phí ship đơn hoàn nhưng vẫn bị -25k -35k -30k????"
   — [TikTok Shop Seller Center](https://play.google.com/store/apps/details?id=com.tiktokshop.seller&hl=vi&gl=VN) · đăng 17/09/2026 · 3★ · nhãn `phi_san`, `tien_ve_doi_soat`, `hoan_tra` · (`0e68daaaa20e`)
5. "khách trả hàng là mất 58k nhé. bán ko lời mà thấy âm phủ luôn rồi"
   — [TikTok Shop Seller Center](https://play.google.com/store/apps/details?id=com.tiktokshop.seller&hl=vi&gl=VN) · đăng 15/09/2026 · 1★ · nhãn `hoan_tra` · (`446971078d81`)
6. "HÚT MÁU NGƯỜI QUÁ GHÊ, mé đơn 180k mà ăn tận 51k trong khi tik tok shop chỉ lấy phí 19k."
   — [Lazada Seller Center](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) · đăng 15/09/2024 · 1★ · nhãn `phi_san` · (`5f2459e1da09`)
7. "Tự động join các chương trình km rồi trừ phí khủng, 600gram trừ 250k phí vận chuyển, không giải quyết đền bù, chiếm đoạt tiền shop"
   — [Lazada Seller Center](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN) · đăng 12/10/2024 · 1★ · nhãn `phi_san`, `voucher_khuyen_mai` · (`4069bda8600b`)

Trích dẫn 6 và 7 đăng năm 2024, vì 300 review mới nhất của Lazada trải từ 06/2024 (giới hạn ở mục 5).

### Bối cảnh từ YouTube (không tính là bằng chứng)

- ["Vì Sao Nhiều Chủ Shop Muốn Thoát Khỏi Các Sàn Thương Mại Điện Tử Shopee, TiktokShop,.."](https://www.youtube.com/watch?v=oEwbf3F2oV0) (kênh Ếch Biết Tuốt, 15/10/2026 theo ghi chép của nhóm).
  - Video nói *"bài toán… không nằm ở chỗ cãi nhau xem sàn thu phí bao nhiêu là đắt, mà là khoản phí đó mang lại bao nhiêu doanh thu và lợi nhuận tương xứng"*.
  - Bình luận dưới video: "Tính ra thu về đc 70%"; "đổi trả là ác mộng".
- ["10 Chỉ Số Phải BIẾT khi bán hàng trên sàn TMĐT | Hiếu Suro"](https://www.youtube.com/watch?v=bZuylc8ZaO0).
  - Video dạy 10 chỉ số, không có chỉ số nào tính lãi, và ROAS được tính trên GMV.
  - Đây là lý do sản phẩm đổi sang **ROAS hoà vốn = 1 ÷ biên lãi trước quảng cáo**.

## 4. Các nguồn có khớp nhau không

Review nói phí bị trừ theo từng đơn mà không ai giải thích được (trích dẫn 1, 2, 4), và chương trình tự bật ăn vào lãi (trích dẫn 3, 7).

Video YouTube khớp ở ý "phí phải so với lợi nhuận nó mang lại". Video cũng cho thấy người bán đang được dạy đo hiệu quả bằng doanh thu thay vì lãi.

**Khảo sát của nhóm chỉ để tham khảo, không đưa vào số chính:**
- Form không rẽ nhánh, nên người chưa từng bán vẫn trả lời hết.
- Câu 9–11 viết dạng khẳng định sẵn, nên dễ kéo người trả lời về phía "đồng ý".
- Nếu dùng thì chỉ tính người chọn "Đang bán" hoặc "Đã từng bán".

## 5. Giới hạn và kết luận

**Giới hạn:**
- Review nghiêng về người đang bực (85/88 review pain về tiền từ 3 sao trở xuống) và không cho biết quy mô shop. Đây là tín hiệu có pain, **không đo được tỉ lệ người bán gặp pain**.
- Khoảng thời gian của 3 app khác nhau (Lazada từ 06/2024), nên so sánh giữa các app chỉ là tương đối.
- Nhãn do AI gán; người kiểm mới đọc 30/216 dòng.

**Kết luận:** giả thuyết "chủ shop đa sàn bị trừ nhiều khoản trên từng đơn mà không biết khoản nào bắt buộc, khoản nào là chương trình tự bật đang ăn lãi" **đúng về hướng**. Phàn nàn về tiền tập trung ở phí trên từng đơn và việc không ai giải thích được khoản trừ, nhiều nhất ở Shopee.

**Điều vẫn chưa biết:**
- Bao nhiêu phần trăm người bán gặp pain này.
- Họ mất bao nhiêu phút mỗi lần đối soát.
- Shop nhỏ có sẵn sàng dán chi tiết thanh toán vào một công cụ hay không.

Kiểm tiếp bằng 2–3 người bán dùng thử (`validation/log.md`).
