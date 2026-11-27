# data/demo_import — file export mẫu để demo luồng import

> **Giả lập.** "Shop Demo" không phải shop thật. Cột trong file mô phỏng file export của Shopee, TikTok Shop và Lazada theo hiểu biết của nhóm, **không phải định dạng chính thức**. Trước khi demo, nên đối chiếu với một file export thật (lấy từ tài khoản của thành viên, đã che thông tin), rồi sửa `EXPORT_FORMATS` trong `data/make_demo_import.py` cho khớp.

## Các file

| File | Nội dung | Agent đọc? |
|---|---|---|
| `shopee_don_hang_2026-11.xlsx` | Sheet `Đơn hàng`: 262 đơn tháng 11/2026, mỗi khoản phí một cột (ghi số dương). Sheet `Quảng cáo`: 2 chiến dịch. Sheet `Đọc tôi` | Có (qua import) |
| `tiktok_don_hang_2026-11.xlsx` | 185 đơn, tên cột kiểu TikTok Shop, 1 chiến dịch quảng cáo | Có |
| `lazada_don_hang_2026-11.xlsx` | 90 đơn, tên cột kiểu Lazada | Có |
| `gia_von_mau.xlsx` | File chủ shop tự điền. Sheet `Giá vốn`: SKU, ngành, giá vốn (DM-BS01 để trống). Sheet `Thông tin shop`: loại shop theo từng sàn | Có |
| `_dap_an_2026-11.json` | **Đáp án:** các câu chuyện cài sẵn trong tháng, số liệu theo SKU × sàn, quảng cáo | **Không** |

## Câu chuyện cài sẵn (hệ thống phải tìm ra)

1. **DM-AO01, áo thun:** hoa hồng tiếp thị liên kết ăn **96% lãi** trên TikTok Shop và 50% trên Shopee.
2. **DM-TN01, tai nghe, Shopee:** **4 đơn Phí Voucher Xtra bị trừ vượt trần** 50.000đ/sản phẩm → Escalate (soạn nháp câu hỏi gửi sàn).
3. **DM-VA01 và DM-QJ01 trên TikTok Shop:** tỉ lệ trả hàng 22–27% → phí vận chuyển trả hàng.
4. **Quảng cáo "Serum - Tìm kiếm" (Shopee):** ROAS 2,26, thấp hơn mức hoà vốn 2,7 → phần doanh số do quảng cáo mang về đang lỗ.
5. **Lazada:** 3 đơn có "Phí khác" không khớp luật nào → Escalate.
6. **DM-BS01:** chưa nhập giá vốn → Ask.

## Chạy

```bash
python -m pip install openpyxl
python data/make_demo_import.py                       # sinh lại bộ file (seed 42)
python data/import_export.py data/demo_import/*_don_hang_*.xlsx --cogs data/demo_import/gia_von_mau.xlsx
```

`import_export.py` tự nhận sàn theo tên cột, chuẩn hoá về cùng schema với `data/synthetic/orders.csv` và `order_lines.csv`, rồi tính bằng code:
- lãi theo sàn và theo SKU × sàn;
- công tắc nào ăn lãi nhiều nhất;
- dòng phí nào lệch luật (so với bảng phí);
- dòng "Phí khác" không khớp luật nào;
- tỉ lệ trả hàng;
- ROAS so với ROAS hoà vốn.

Kết quả ghi vào `data/imported/<tên>/`. Thư mục này nằm trong `.gitignore`, vì khi demo với file export thật thì đó là **dữ liệu thật của shop**, không được commit.

Phí tính theo `data/fee_rules.csv` (Thái giữ). Nếu chưa có file này thì tính theo `data/synthetic/fee_rules_v0.csv`, là bảng tạm chưa đối chiếu với chính sách của sàn.
