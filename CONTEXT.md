# CONTEXT.md — bối cảnh bộ đề hackathon (tóm tắt)

> File này giữ lại ý chính của bộ đề gốc (`README`, `01-challenge-brief`, `02-guide`, `03-rubric`, `tracks/`, `data/`, `further-reading/`) sau khi các file đó được xóa khỏi repo.
> Bản đầy đủ nằm trong lịch sử git, commit `6225f90`: `git show 6225f90:<đường dẫn>` (ví dụ `git show 6225f90:02-guide.md`).

## Cuộc thi

Mini Hackathon AI · AI20K khoá 5 · L3 (Day 15). Nhóm là một product team làm sản phẩm AI cho người dùng thật. Phải làm đủ 3 việc:
1. Chọn track và tìm một pain có bằng chứng.
2. Thiết kế giải pháp AI cho **một lát cắt**.
3. Chứng minh bằng số: đúng bao nhiêu trên bộ câu thử, tốn bao nhiêu mỗi tháng khi dùng thật.

**Lát cắt = một câu:** một người dùng · một công việc · một quyết định AI · một kết quả. Demo được trong 2 phút, làm trong khoảng 10 giờ.

## Track và sản phẩm của nhóm (bản 4, 18:50 T6 27/11 — cả nhóm đã chốt)

**Track D · Thương mại điện tử, phía người bán.** Nhóm Hàllucinations, lớp L3B. Việc của từng người: xem `TASK.md`.

**Sản phẩm: "Lãi đi đâu?"**, agent soi từng đơn hàng trên **cả 3 sàn: Shopee, TikTok Shop, Lazada**. Plan chi tiết: `plan-lai-di-dau-v4-agent-3-san.html` (thư mục cha của repo).

**Lát cắt một câu:** một chủ shop nhỏ bán cùng sản phẩm trên Shopee, TikTok Shop và Lazada · dán chi tiết thanh toán của một hoặc vài đơn vừa về tiền (sàn nào cũng được) kèm giá vốn · agent quyết định mỗi khoản trừ thuộc luật phí nào của sàn đó tại ngày đặt đơn, "công tắc" (chương trình tự bật) nào đang ăn lãi, sàn nào lãi thật nhiều nhất, và có cần hỏi lại hay soạn nháp câu hỏi gửi sàn không · chủ shop biết lãi thật mỗi đơn, mỗi sàn và nên tắt, giữ hay chỉnh công tắc nào ở sàn nào.

**Đã đổi hướng.** Bản lúc 17:00 là "chẩn đoán cuối tháng trên số liệu cả shop". Nhóm bỏ hướng đó vì hai lý do. Thứ nhất, review cho thấy phàn nàn về tiền tập trung ở phí bị trừ trên từng đơn mà không hiểu vì sao. Thứ hai, báo cáo lãi tổng thì BigSeller và Sapo đã có. Dữ liệu cấp shop theo tháng (`data/synthetic/stores.csv`, `store_months.csv`) là của hướng cũ, chỉ giữ làm ngữ cảnh. Dữ liệu cấp đơn cho bản 4 đã có, xem mục **Dữ liệu hiện có** ngay dưới.

**Bản 4 (chốt 18:50):** (1) không thu hẹp về Shopee: làm đủ 3 sàn vì shop nhỏ thường bán cùng lúc trên cả 3 nơi và review của cả 3 app đều than phí; (2) nâng từ một lần gọi LLM lên agent thật; (3) workflow cố định chỉ để cứu hộ.

### Dữ liệu hiện có (cập nhật 22:06 T6 27/11)

Toàn bộ là **giả lập có seed**, sinh lại được, **không phải bằng chứng pain**. Nguồn và giả định ghi ở `data/DATA_CARD.md`.

| Nhóm | File | Agent / app được đọc? | Dùng cho |
|---|---|---|---|
| Bảng phí tạm | `data/synthetic/fee_rules_v0.csv` (90 luật: Shopee 36, TikTok 31, Lazada 23) | Có | Đúng schema H2. 80 luật `gia_dinh`, 10 `bao_chi`, chưa luật nào `chinh_thuc`. `fee_engine.load_rules()` ưu tiên `data/fee_rules.csv` khi Thái đẩy lên |
| Code tính phí | `data/fee_engine.py` | Có (là code) | `find_rule`, `amount_for`, `compute_lines`; `--check` ra đúng đơn mẫu H4. Thân hàm H3 bọc lại file này |
| Đơn giả 3 sàn | `data/synthetic/shops.csv` (8), `products.csv` (41), `listings.csv`, `orders.csv` (300: 120 / 100 / 80), `order_lines.csv` | Có | Đầu vào công cụ, frontend, test |
| Chữ dán | `data/synthetic/pastes.jsonl` (288 đoạn: 1 đơn, nhiều đơn, so chéo sàn, chèn lệnh, từ chối; có đoạn không ghi tên sàn) | Có | Đầu vào agent, nguồn `eval/benchmark.csv` |
| **Đáp án** | `data/synthetic/order_answers.csv`, `line_answers.csv`, `paste_answers.csv`, `data/demo_import/_dap_an_2026-11.json` | **Không** | Chỉ để chấm. Quyết định mong đợi trên 288 đoạn: 220 act · 33 ask · 23 escalate · 12 refuse |
| Demo import (bổ sung, ngoài lát cắt) | `data/demo_import/*_don_hang_2026-11.xlsx` (3 sàn), `gia_von_mau.xlsx`; chạy bằng `data/import_export.py` | Có | Màn import tháng (HA-14, TH-11). Có 6 câu chuyện cài sẵn. Cột file **mô phỏng**, chưa đối chiếu file export thật |
| Kho chính sách (H1) | `data/policies/chunks.jsonl` | **Chưa có** (mở sau) | Đến lúc đó `search_policy` trả rỗng, `chunk_id` để `null`, metric truy xuất top-5 chưa đo |

Giới hạn cần nhớ khi kể chuyện: tỉ lệ phí là giả định nên kết luận "sàn nào đắt hơn" chỉ đúng trong data giả; lãi mỗi đơn chưa trừ ship shop bù, đóng gói, quảng cáo; benchmark mới 1/26 câu nguồn thật.

### Bằng chứng (đều là nguồn công khai; không liên hệ được người bán để phỏng vấn)

- **Đào review, nguồn chính:** 900 review mới nhất của 3 app người bán, 300 mỗi app, lấy ngày 27/11/2026. Các app: Shopee Seller Center `com.shopee.shopeeseller`, TikTok Shop Seller Center `com.tiktokshop.seller`, Lazada Seller Center `com.sc.lazada`. Đếm sơ bộ theo từ khoá, **cần đọc tay để chốt**:
  - 468/900 (52,0%) review từ 3 sao trở xuống.
  - 129/900 (14,3%) có ít nhất một nhãn tiền. Trong các review ≤ 3 sao là 114/468 (24,4%).
  - Phí sàn 65/900 (7,2%), riêng Shopee 43/300 (14,3%). Hoàn, huỷ đơn 33. Tiền về, đối soát 32. Lãi, lỗ 27. Quảng cáo 16. Khuyến mãi 9.
  - Lỗi app 162/900, ngoài phạm vi.
- **Trích dẫn tiêu biểu** (Shopee Seller Center): "Ứng dụng thu phí quá thiếu minh bạch. Đề nghị Shopee… hiển thị rõ từng đơn: sản phẩm nào phát sinh phí Affiliate, Affiliate của ai, tỷ lệ bao nhiêu và số tiền bị trừ." (26/09/2026, 1★). Một người khác kể tổng phí trừ 133k trên một đơn, và "NV hỗ trợ ko trả lời được vì sao bị trừ nhiều như vậy" (26/06/2026, 1★).
- **Khảo sát của nhóm:** chỉ là tham khảo. Form không rẽ nhánh nên người chưa bán vẫn trả lời. Chỉ tính người chọn "Đang bán" hoặc "Đã từng bán". Câu 9–11 là câu khẳng định sẵn nên dễ kéo người trả lời về phía "đồng ý".
- **YouTube** (bối cảnh, không tính là bằng chứng): video Ếch Biết Tuốt (15/10/2026) nói *"bài toán… không nằm ở chỗ cãi nhau xem sàn thu phí bao nhiêu là đắt, mà là khoản phí đó mang lại bao nhiêu doanh thu và lợi nhuận tương xứng"*. Bình luận: "Tính ra thu về đc 70%"; "đổi trả là ác mộng" với người bán. Video Hiếu Suro dạy 10 chỉ số, không chỉ số nào tính lãi, và ROAS được tính trên GMV.

### Thực trạng 2026 (bài tổng hợp, cần đối chiếu trang chính sách đã crawl)

- **Shopee:**
  - 24/04/2026: "phí thanh toán" đổi tên thành "phí xử lý giao dịch".
  - 01/05/2026: phí xử lý giao dịch lên 6% cho shop thường (trước khoảng 4,91%). Mall áp dụng từ 08/05.
  - 08/05/2026: giảm 1% phí cố định ở nhiều ngành.
  - 23/05/2026: Voucher Xtra 5,5%, tối đa 50.000đ mỗi sản phẩm.
- **TikTok Shop:** 09/05/2026 phí giao dịch 6%; biểu hoa hồng mới từ 03/07 (Mall từ 03/08).
- **Thuế:** từ 01/07/2025, sàn khấu trừ thuế thay hộ kinh doanh (NĐ 117/2025, tỉ lệ cần tra Điều 5). Giảm 2% GTGT hết hạn 31/12/2026.
- **Quy mô:** khoảng 601.800 shop có đơn năm 2025, giảm 7,43%. Câu "600.000 shop rời sàn" là **đọc nhầm**. Nửa đầu 2026 có 613.800 nhà bán (CafeF).

### Insight dẫn tới sản phẩm

1. Phí gây bức xúc vì không gắn với nguyên nhân → mỗi dòng trừ phải gắn với một luật: tên dễ hiểu, tỉ lệ, trần, ngày hiệu lực, nguồn.
2. Nhiều khoản trừ là công tắc tự bật (Voucher Xtra, tiếp thị liên kết, quảng cáo, voucher shop, voucher đồng tài trợ) → tách khoản **bắt buộc** khỏi khoản **công tắc**, tính công tắc nào ăn bao nhiêu phần lãi.
3. Biểu phí đổi nhanh (ít nhất 7 mốc từ 4 đến 8/2026) → tra luật theo ngày đặt đơn, hiểu cả tên cũ.
4. Người bán không rời sàn được → chỉ gợi ý việc làm được trong sàn, không gợi ý né phí.
5. Chủ shop đo thành công bằng doanh thu (ROAS trên GMV) → đổi thành **ROAS hoà vốn = 1 ÷ biên lãi trước quảng cáo**.
6. Đơn hoàn là chi phí ẩn → có loại dòng "chi phí đơn hoàn".
7. Một con số sai là mất niềm tin → code tính mọi số; bước kiểm bắt buộc.

### Kiến trúc (agent có giới hạn, đa sàn)

- **Hai nguồn sự thật:**
  - `data/fee_rules.csv` (bảng phí có cấu trúc) dùng để **tính**.
  - `data/policies/chunks.jsonl` (kho chính sách 3 sàn đã embedding, schema theo `crawl-spec.md` mục B4) dùng để **giải thích và trích dẫn**. Không lấy con số tính toán từ chunk.
- **Luồng:** lọc yêu cầu → agent lập kế hoạch (mấy đơn, sàn nào, ngày nào, tách dòng) → vòng công cụ (tra luật + tìm đoạn chính sách, lọc cứng theo sàn → code tính → `compare_platforms` nếu ≥ 2 sàn) → bước kiểm (mọi số có trong output công cụ, mọi luật và `chunk_id` trích có thật, đúng sàn, đúng ngày) → sai thì agent sửa 1 lần, vẫn sai thì chỉ trả bảng dòng → agent quyết định → chủ shop quyết.
- **Sáu năng lực agent:** (1) lập kế hoạch theo chữ dán, ghi bằng `note()` vào trace; (2) tự chọn công cụ; (3) hai nguồn sự thật, không trộn luật giữa các sàn; (4) tự kiểm, tự sửa 1 lần; (5) Ask lưu trạng thái phiên, trả lời xong thì làm tiếp; (6) so chéo sàn cho cùng sản phẩm.
- **Bốn kiểu quyết định:** Act (kết luận + 1–2 công tắc cần đổi), Ask (thiếu giá vốn, tổng không khớp), Escalate (dòng lệch hoặc không khớp luật → nháp câu hỏi gửi sàn, không tự gửi), Refuse (né phí, gian lận, dữ liệu shop khác, lệnh chèn trong dữ liệu).
- **Giới hạn:** tối đa 8 lượt gọi công cụ mỗi đơn, 20 lượt mỗi phiên (tối đa 5 đơn / phiên), nhiệt độ 0. Công cụ chỉ đọc hoặc soạn nháp. Cổng 22:30: chạy thật 3 đơn, mỗi sàn 1 đơn. Nếu 23:30 vòng agent chưa qua `eval --try` thì chuyển sang workflow cứu hộ, **vẫn giữ 3 sàn**, ghi vào `spec.md` §10.
- **Chuẩn đạt** (chốt 19:30, không sửa): ≥ 90% dòng gắn đúng luật VÀ 100% con số khớp công cụ VÀ 100% câu `tu_choi` bị từ chối. Metric phụ:
  - quyết định đúng (act / ask / escalate / refuse) ≥ 85%
  - bắt dòng lệch ≥ 90%
  - truy xuất đúng đoạn trong top 5 ≥ 80%
  - hỏi lại khi thiếu dữ liệu 100%
  - công tắc khớp quy tắc code ≥ 80%
  - gắn đúng luật tách theo từng sàn
  - so chéo sàn chọn đúng sàn lãi nhất ≥ 80%
  - số lượt công cụ trung bình / đơn, tỉ lệ tự sửa thành công, tỉ lệ rơi về fallback

Các hướng gợi ý của track D trong đề (chỉ là gợi ý): D1 khiếu nại đơn đồ ăn · D2 đặt đơn nhóm · D3 trả hàng trung lập. Người trong nhóm không tính là bằng chứng.

## Mốc nộp (nộp trên https://ai20k-hackathon.pages.dev, đúng hạn và đủ phần mới có điểm mốc)

| Mốc | Giờ | Điểm | Cần có |
|---|---|---|---|
| CP1 | 17:00 T6 27/11 | 3 | `TEAMS.md` (đội trưởng dòng 1), track + bài toán 1–2 câu (không chữ AI), lát cắt, `canvas.md` 7 dòng, link repo công khai |
| CP2 | 19:30 T6 27/11 | 4 | Canvas cập nhật, nguồn bằng chứng, `spec.md` §4 có sơ đồ kiến trúc, `eval/benchmark.csv` ≥10 câu, `eval/metric_spec.yaml`, `data/DATA_CARD.md`, chuẩn "đạt" bằng số (§7, **chốt, không sửa**), `python run.py` chạy với AI giả |
| CP3 | 10:00 T7 28/11 | 4 | `evidence/summary.md` (≥1 nguồn đạt ngưỡng + ≥5 trích dẫn), 20–30 câu thử (≥5 `kho`, ≥2 `tu_choi`), video 30 giây gọi AI thật, kết quả lượt 1 + run ID, `spec.md` §0–§7 |
| CP4 | 14:30 T7 28/11 | 4 | Phòng demo, 7 hạng mục, lượt 1 → lượt 2, chi phí / task thành công + tên model, slide (mọi định dạng), video demo dự phòng |
| Hạn chót | 23:59 T7 28/11 | — | Mọi thay đổi sau 14:30 ghi vào `spec.md` §10, mỗi người 1 file `reflection/` |

Demo Zone 14:30–16:00, Demo Phòng 16:00–18:00 (T7 28/11).

## 7 hạng mục bắt buộc (Pain → Impact → Giải pháp AI, chống lưng bằng Đánh giá và Chi phí)

1. **Bằng chứng pain** (`evidence/`): ≥1 nguồn đạt ngưỡng: đào data (x/N và %), phỏng vấn ≥3 người, hoặc khảo sát ≥20 người ngoài nhóm; ≥5 trích dẫn nguyên văn.
2. **Impact có số** (`spec.md` §1–2): số người × số lần / tháng × tốn bao nhiêu mỗi lần, mỗi số có nguồn.
3. **Thiết kế giải pháp AI** (`spec.md` §4): 1 sơ đồ, hình dạng (workflow / 1 agent / nhiều agent) + lý do, dữ liệu + công cụ, chỗ chặn rủi ro, chỗ người duyệt.
4. **Bản chạy thử làm trọn lát cắt** (`codebase/`): gọi AI thật ở quyết định trung tâm, chạy bằng `run.py eval` và `run.py simulate`.
5. **Định nghĩa "tốt" + bộ câu thử** (`eval/`, `data/`): data card, 20–30 câu, metric spec ≥3 metric, chuẩn "đạt" chốt ở CP2, lượt 1 → lượt 2.
6. **Mô phỏng chi phí** (`cost/`): ≥50 phiên giả lập, chi phí / task thành công, 3 kịch bản ở quy mô thật của sản phẩm.
7. **Slide + demo + video dự phòng**: có trang "Đánh giá thế nào" và "Chi phí khi dùng thật".
- Bonus +5: 2–3 người ngoài nhóm dùng thử, có log ở `validation/log.md`.

## Chấm điểm (100 = 15 nộp + 85 chấm bài + 5 bonus)

R1 Bằng chứng pain 14 · R2 Impact 11 · R3 Giải pháp AI 16 · R4 Bộ câu thử + metric 14 · R5 Báo cáo đánh giá 8 · R6 Chi phí 12 · R7 Slide & demo 10.

- **Không xét giải** nếu thiếu: bản chạy thử gọi AI thật · bằng chứng pain ≥1 nguồn · bộ câu thử ≥20 câu có % đạt · slide.
- Kết quả thấp mà trung thực vẫn đủ điểm. Số bị sửa hoặc giấu (đổi chuẩn "đạt" sau CP2, bỏ câu thử trượt) → khối đó 0 điểm.

## Bốn lớp "chỗ khó" cần biến thành câu thử

Nguồn sự thật · mơ hồ / thiếu thông tin · ngoài phạm vi / thẩm quyền · đặc thù lĩnh vực (sai thì ai mất gì).

## Luật dữ liệu và ràng buộc

- Bản chạy thử chạy riêng, không kết nối hệ thống thật của hãng nào.
- Không dùng dữ liệu thật của người thật (đơn, địa chỉ, số điện thoại, sao kê…). Cần thì tự dựng dữ liệu giả có seed, ghi nguồn ở `data/DATA_CARD.md`. Data tự dựng **không phải bằng chứng pain**.
- Người được phỏng vấn ghi P1, P2… kèm vai, không ghi tên / SĐT / email.
- Review công khai: không chép tên người viết, trích tối đa 2 câu, ghi link và ngày xem.
- Repo công khai: không commit nguyên tài liệu khoá học, không commit `.env` hay API key.
- Số không có nguồn thì ghi *(tự ước tính)*.

## Bản đồ file đã xóa (để tra lịch sử git)

| Đã xóa | Nội dung |
|---|---|
| `01-challenge-brief.md` | Đề bài, 6 track, luật data, 7 hạng mục |
| `02-guide.md` | Guide 5 giai đoạn: khám phá → thiết kế → build → đo & tính tiền → demo & nộp |
| `03-rubric.md` | Rubric chi tiết R1–R7, điều kiện cứng, trừ điểm |
| `tracks/` | 6 file track A–F (A EdTech, B Y tế, C Du lịch, D TMĐT, E Tài chính, F Làn khác) |
| `data/preclass/`, `data/training-ops/` | Data track A của BTC (không dùng cho track D) |
| `further-reading/` | HAX guidelines, JTBD, Mom Test, bảng giá model, pair guidebook |
