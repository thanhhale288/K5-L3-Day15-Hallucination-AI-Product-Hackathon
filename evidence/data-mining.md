# Đào data — review của 3 app người bán

> Nguồn chính của bằng chứng pain (R1). Người giữ: Hà. Repo chỉ chứa số tổng hợp, nhãn (không có nguyên văn) và
> tối đa 2 câu trích mỗi review. File thô `evidence/reviews/raw-label-sheet.csv` không commit.

## 1. Cách đếm (viết trước khi gán nhãn)

- **Data:** 900 review mới nhất trên Google Play, 300 mỗi app, lấy ngày 27/11/2026 bằng `evidence/crawl_reviews.py`
  (`google-play-scraper`). Danh sách app, ngày review cũ nhất / mới nhất: `evidence/reviews/manifest.csv`.

  | App | Mã app | Review cũ nhất → mới nhất |
  |---|---|---|
  | Shopee Seller Center | `com.shopee.shopeeseller` | 11/01/2026 → 26/11/2026 |
  | TikTok Shop Seller Center | `com.tiktokshop.seller` | 10/07/2026 → 26/11/2026 |
  | Lazada Seller Center | `com.sc.lazada` | 07/06/2024 → 22/11/2026 |

- **Bước 1, lọc từ khoá** (cột `goi_y_nhan`, `LABEL_KEYWORDS` trong `crawl_reviews.py`): 116/900 review có ít nhất
  một nhãn tiền, 784 review còn lại là `khac`. *(Số 129 ghi ở `CONTEXT.md` là lần đếm từ khoá trước đó; chạy lại
  trên file thô hiện tại ra 116.)*
- **Bước 2, gán nhãn đầy đủ** theo schema `crawl-spec.md` A4 trên hai mẫu:
  - **Mẫu A:** cả 116 review có nhãn từ khoá, để đo từ khoá đúng bao nhiêu.
  - **Mẫu B:** 100 review chọn ngẫu nhiên (`random.Random(42)`) trong 784 review không có nhãn, để đo từ khoá bỏ sót bao nhiêu.
- **Ai gán nhãn:** AI gán (`labeler = ai:claude-opus-5-5`), người kiểm tay ≥ 30 dòng và ghi tỉ lệ khớp ở mục 6.
  Kết quả: `evidence/reviews/labels-ai.csv`. Script đếm: `python evidence/count_reviews.py`.
- **Mẫu số:** 900 review (300 mỗi app). Không khử trùng vì đã kiểm, 900 `review_key` là 900 review khác nhau.

### Định nghĩa nhãn

`is_seller_pain = 1` khi người viết là người bán và kể một vấn đề khi bán hàng. Gán `0` cho các trường hợp: người mua,
spam (quảng cáo vay tiền), lời khen, hoặc chê chung không nói việc gì ("app lởm"). "Quảng cáo" hiện trong app làm
phiền người dùng là `loi_app`, không phải `quang_cao`.

| Nhãn `topic` | Nghĩa | Ví dụ (rút gọn) |
|---|---|---|
| `phi_san` | Phí sàn, hoa hồng, chiết khấu, thuế khấu trừ, "bị trừ" khoản phí | "phí sàn 30% thu về trừ vốn bán không có tí lời gì" · "đơn 180k mà ăn tận 51k" |
| `tien_ve_doi_soat` | Tiền về, đối soát, rút tiền, khoản trừ không giải thích được | "tổng phí trừ 133k… NV hỗ trợ ko trả lời được vì sao" · "đối soát số dư thâm hụt" |
| `hoan_tra` | Hoàn hàng, bom hàng, trả hàng làm shop mất tiền | "khách trả hàng là mất 58k" · "phí trả hàng 40k" |
| `quang_cao` | Chi phí quảng cáo của shop | "trừ tiền quảng cáo tự động vô độ" · "100k quảng cáo ko ra nổi đơn" |
| `voucher_khuyen_mai` | Voucher, đồng tài trợ, chương trình tự bật | "tự động join các chương trình km rồi trừ phí khủng" |
| `van_chuyen`, `khoa_tai_khoan_vi_pham`, `loi_app`, `khac` | Ngoài phạm vi tiền | — |

**Pain về tiền** = `is_seller_pain = 1` VÀ có ít nhất một trong 5 nhãn đầu. `mentions_profit = 1` khi review nói rõ lỗ,
không còn lãi hoặc tiền về quá ít.

## 2. Đọc trước, đếm sau

Ba điều thấy được khi đọc, trước khi đếm:
1. Người bán ít khi than mức phí trừu tượng. Họ kể con số trên một đơn cụ thể ("đơn 180k mà ăn tận 51k") và nói không ai giải thích được khoản đó.
2. Họ hay gộp mọi khoản thành một tỉ lệ ("30%", "40% giá bán"), tức là không tách được khoản nào bắt buộc, khoản nào do chương trình tự bật.
3. Có một nhóm review than bị "tự join" chương trình, "tự đăng ký gói dịch vụ" rồi bị trừ tiền. Đây đúng là khái niệm "công tắc" của sản phẩm.

## 3. Kết quả

Chạy `python evidence/count_reviews.py`:

| Đếm gì | x / N | % |
|---|---|---|
| Từ khoá gắn nhãn tiền, đọc lại đúng là pain về tiền (mẫu A) | 88 / 116 | 75,9% |
| Từ khoá bỏ sót: review không nhãn nhưng là pain về tiền (mẫu B) | 3 / 100 | 3,0% |
| **Pain về tiền đã xác nhận** trên toàn bộ | **88 / 900** | **9,8%** |
| Pain về tiền, ước lượng gồm cả phần từ khoá bỏ sót (88 + 3% × 784) *(ước lượng, mẫu B n = 100)* | ≈ 112 / 900 | ≈ 12,4% |
| Phí sàn (đã xác nhận) | 62 / 900 | 6,9% |
| Riêng Shopee: pain về tiền · phí sàn | 56 / 300 · 44 / 300 | 18,7% · 14,7% |
| Riêng TikTok Shop: pain về tiền · phí sàn | 14 / 300 · 6 / 300 | 4,7% · 2,0% |
| Riêng Lazada: pain về tiền · phí sàn | 18 / 300 · 12 / 300 | 6,0% · 4,0% |
| Trong 88 review pain về tiền: phí sàn · hoàn trả · tiền về / đối soát · quảng cáo · voucher | 62 · 30 · 20 · 7 · 6 | 70,5% · 34,1% · 22,7% · 8,0% · 6,8% |
| Trong 88 review pain về tiền: nói rõ lỗ hoặc lãi mỏng | 25 / 88 | 28,4% |
| Trong 88 review pain về tiền: từ 3 sao trở xuống | 85 / 88 | 96,6% |

Số theo app chỉ tính mẫu A. Mẫu B có 3 review bị bỏ sót, cả 3 đều của Shopee.

## 4. Ví dụ cụ thể (tối đa 2 câu, không tên, link app + ngày review)

1. "Ứng dụng thu phí quá thiếu minh bạch. Đề nghị Shopee xem xét lại các khoản phí và hiển thị rõ từng đơn: sản phẩm nào phát sinh phí Affiliate, Affiliate của ai, tỷ lệ bao nhiêu và số tiền bị trừ." — `f8d36f7bd98d` · Shopee Seller Center · 26/09/2026 · 1★ · [Google Play](https://play.google.com/store/apps/details?id=com.shopee.shopeeseller&hl=vi&gl=VN)
2. "tôi bán 1 sản phẩm giá 249k*2sl họ trừ phần trợ giá của shop 49k tổng phí trừ 133k khi tôi vào thắc mắc thì NV hỗ trợ ko trả lời được vì sao bị trừ nhiều như vậy." — `7ce0babeac94` · Shopee Seller Center · 26/06/2026 · 1★
3. "HÚT MÁU NGƯỜI QUÁ GHÊ, mé đơn 180k mà ăn tận 51k trong khi tik tok shop chỉ lấy phí 19k." — `5f2459e1da09` · Lazada Seller Center · 15/09/2024 · 1★ · [Google Play](https://play.google.com/store/apps/details?id=com.sc.lazada&hl=vi&gl=VN)
4. "đăng sản phẩm nhanh nhưng hay bị trừ phí lạ dù đã đăng kí gói hoàn phí ship đơn hoàn nhưng vẫn bị -25k -35k -30k????" — `0e68daaaa20e` · TikTok Shop Seller Center · 17/09/2026 · 3★ · [Google Play](https://play.google.com/store/apps/details?id=com.tiktokshop.seller&hl=vi&gl=VN)
5. "Tự động join các chương trình km rồi trừ phí khủng, 600gram trừ 250k phí vận chuyển, không giải quyết đền bù, chiếm đoạt tiền shop" — `4069bda8600b` · Lazada Seller Center · 12/10/2024 · 1★
6. "phí đủ thứ từ đầu năm đến giờ tăng phí lên 2 lần cộng thêm phí đồng tài trợ + dồn chiếm hết 29%-31%." — `e8962e8c9398` · Shopee Seller Center · 18/06/2026 · 1★
7. "khách trả hàng là mất 58k nhé. bán ko lời mà thấy âm phủ luôn rồi" — `446971078d81` · TikTok Shop Seller Center · 15/09/2026 · 1★

Ngày ghi sau tên app là ngày đăng review. Ngày xem: 27/11/2026.

## 5. Giới hạn của data

- Review Google Play nghiêng về người đang bực (85/88 review pain về tiền từ 3 sao trở xuống) và không cho biết quy mô shop. Đây là **tín hiệu có pain**, không đo được tỉ lệ người bán gặp pain.
- 300 review mới nhất của Lazada trải từ 06/2024, trong khi Shopee và TikTok chỉ vài tháng gần đây, nên so sánh giữa các app là so trên các khoảng thời gian khác nhau.
- Nhãn do AI gán. Chưa đủ 30 dòng người kiểm thì các số trên vẫn là số sơ bộ.
- Mẫu B chỉ có 100 dòng, nên con số ước lượng ≈ 12,4% có sai số lớn. Số chắc chắn là 88/900 đã xác nhận.

## 6. Người kiểm tay

`python evidence/make_check_sheet.py` chọn 30 dòng theo 4 nhóm (seed 2026) ra `evidence/reviews/raw-check-30.xlsx` kèm nguyên văn
(file này không commit). Điền cột `human_check`: `dong_y`, hoặc `sua:<trường>=<giá trị đúng>`. Rồi chạy
`python evidence/make_check_sheet.py --merge` và `count_reviews.py`, mục 5 sẽ in tỉ lệ khớp. Ghi kết quả vào đây:

- Người kiểm: __ · số dòng: __ · khớp: __/__ (__%)
