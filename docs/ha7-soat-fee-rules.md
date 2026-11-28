# HA-7 · Soát nghiệp vụ `data/fee_rules.csv` bản 1 (gửi Thái)

Người soát: Hà · 28/11/2026 · bản soát: 91 luật (Shopee 36 · TikTok 32 · Lazada 23; `chinh_thuc` 3 · `bao_chi` 8 · `gia_dinh` 80).
Đối chiếu với các mốc ở `CONTEXT.md` › Thực trạng 2026. Mình không sửa file, chỉ ghi ý kiến. Thái quyết định sửa hay giữ.

## Khớp mốc, giữ nguyên

| Khoản | Kiểm gì | Kết quả |
|---|---|---|
| Shopee phí cố định | Giảm 1% từ 08/05/2026 ở mọi ngành, cả shop thường và Mall | ✅ |
| Shopee phí xử lý giao dịch | Đổi tên từ "phí thanh toán" ngày 24/04 (có `ten_cu`); 6% shop thường từ 01/05, Mall từ 08/05 | ✅ |
| Shopee Voucher Xtra | 5,5%, trần 50.000đ **mỗi sản phẩm** từ 23/05 (`fee_engine.amount_for` nhân trần với số lượng) | ✅ |
| Shopee phí hạ tầng | 3.000đ / đơn | ✅ (`bao_chi`) |
| TikTok phí giao dịch | 6% từ 09/05 | ✅ |
| TikTok hoa hồng nền tảng | Biểu mới 03/07 cho shop thường, 03/08 cho Mall | ✅ ngày; tỉ lệ từng ngành vẫn `gia_dinh` |
| Loại bắt buộc / công tắc | Voucher Xtra, Voucher Extra, Freeship Max, tiếp thị liên kết (3 sàn), voucher đồng tài trợ là `cong_tac`; còn lại `bat_buoc` | ✅ đúng khái niệm "công tắc = shop tự bật" |

## Cần Thái xem lại

1. **TikTok `phi_xu_ly_don_hang` 3.000đ / đơn, `chinh_thuc`, hiệu lực từ 27/10/2025.** Không đơn TikTok nào trong `data/synthetic/order_lines.csv` có dòng này (0/100 đơn). Nếu luật đúng, đơn giả đang thiếu một khoản bắt buộc. Đề xuất: chạy lại `make_orders.py`, hoặc ghi chú vì sao đơn giả không có dòng này.
2. **Phí vận chuyển trả hàng cố định 20.000đ / đơn ở cả 3 sàn (`gia_dinh`).** Thực tế đây là phí ship theo đơn: review kể 32k, 40k, 58k (`evidence/data-mining.md`). Nếu agent so dòng này với 20.000đ, nó sẽ báo "lệch luật" sai rồi soạn nháp khiếu nại sai. Đề xuất: đổi `base` thành kiểu "theo thực tế", hoặc để `expected = actual` cho dòng này, và ghi rõ trong DATA_CARD.
3. **Thuế khấu trừ 1,5% `ap_dung = tat_ca`.** Theo NĐ 117/2025, sàn chỉ khấu trừ thay **hộ kinh doanh**, công ty tự kê khai. `fee_engine.compute_lines` đã bỏ dòng thuế khi `seller_type ≠ ho_kinh_doanh`, nhưng `lookup_fee_rule` vẫn trả luật này cho mọi shop. Tỉ lệ 1,5% còn là `gia_dinh`, cần tra Điều 5 NĐ 117.
4. **Shopee Voucher Xtra trước 23/05 (4%, trần 50.000đ, `gia_dinh`).** Chưa thấy nguồn nói Voucher Xtra có trần trước mốc 23/05. Nếu không có nguồn thì bỏ trần ở dòng này, hoặc ghi chú là giả định.
5. **TikTok Phí Voucher Extra đổi tỉ lệ đúng ngày 09/05,** trùng mốc phí giao dịch, nhưng là `gia_dinh`. Cần nguồn, hoặc ghi chú rằng mốc này là nhóm đặt cho trùng.
6. **Lazada cả 23 luật đều `gia_dinh` và không có `chunk_id`,** dù `data/lazada/policies/` đã crawl. Ưu tiên gắn nguồn cho phí thanh toán 4% và Freeship Max 5% (trần 40.000đ), vì hai khoản này xuất hiện ở gần mọi đơn Lazada.
7. **`ten_cu` dùng `|` có khoảng trắng hai bên** (vd `Hoa hồng tiếp thị liên kết | Phí Affiliate`). `tools._names` đã strip nên vẫn khớp, chỉ cần giữ một quy ước trong DATA_CARD.

## Ảnh hưởng tới demo

Đơn mẫu H4 `DEMO-0412` không bị ảnh hưởng bởi các điểm trên, vẫn ra 123.520đ / 28.520đ (`python data/fee_engine.py --check`).
Điểm 2 ảnh hưởng tới màn import: `import_export.py` có thể đếm sai số đơn "lệch luật" ở dòng phí trả hàng. Bộ demo hiện tại chưa gặp vì phí trả hàng trong data demo đều là 20.000đ.
