# CONTEXT.md — bối cảnh bộ đề hackathon (tóm tắt)

> File này giữ lại ý chính của bộ đề gốc (`README`, `01-challenge-brief`, `02-guide`, `03-rubric`, `tracks/`, `data/`, `further-reading/`) sau khi các file đó được xóa khỏi repo.
> Bản đầy đủ nằm trong lịch sử git, commit `6225f90`: `git show 6225f90:<đường dẫn>` (ví dụ `git show 6225f90:02-guide.md`).

## Cuộc thi

Mini Hackathon AI · AI20K khoá 5 · L3 (Day 15). Nhóm là một product team làm sản phẩm AI cho người dùng thật. Phải làm đủ 3 việc:
1. Chọn track và tìm một pain có bằng chứng.
2. Thiết kế giải pháp AI cho **một lát cắt**.
3. Chứng minh bằng số: đúng bao nhiêu trên bộ câu thử, tốn bao nhiêu mỗi tháng khi dùng thật.

**Lát cắt = một câu:** một người dùng · một công việc · một quyết định AI · một kết quả. Demo được trong 2 phút, làm trong khoảng 10 giờ.

## Track của nhóm

**Track D · Thương mại điện tử** (người bán / seller, hướng lợi nhuận). Kế hoạch chi tiết nằm ở `plan-track-d-seller-profit.html` (ngoài repo, thư mục cha). Data chạy thử: `data/07_Ecommerce_Seller_Store.xlsx` + `data/DATA_CARD.md`.

Các hướng gợi ý của track D (chỉ là gợi ý): D1 xử lý khiếu nại đơn giao đồ ăn trong hạn mức · D2 đặt đơn nhóm có ràng buộc ăn uống · D3 trả hàng / hoàn tiền trung lập.
Bẫy chung: bên bị khiếu nại (quán, người bán) cũng là người dùng. Người trong nhóm không tính là bằng chứng.

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
