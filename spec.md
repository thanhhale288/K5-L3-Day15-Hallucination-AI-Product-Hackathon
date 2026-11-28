# AI SPEC — Lãi đi đâu? Agent soi đơn đa sàn (Shopee · TikTok Shop · Lazada) · Nhóm Hàllucinations · Lớp L3B · Phòng [XXX] · Zone [X]

> Mốc nộp: §7 chốt chuẩn "đạt" tại **CP2 19:30 Thứ Sáu 27/11** · §0–§7 nộp **CP3 10:00 Thứ Bảy 28/11** · đủ §0–§10 **CP4 14:30 Thứ Bảy 28/11** · §10 changelog ghi tiếp đến **23:59 Thứ Bảy 28/11**.
> Đầu mỗi mục ghi bước guide (`02-guide.md` trong repo đề) chỉ cách điền. Mỗi mục ngắn, có số và nguồn; chi tiết để ở file được trỏ tới. Xoá dòng hướng dẫn trong ngoặc vuông khi điền xong.

Track: [ ] A · [ ] B · [ ] C · [x] D · [ ] E — bài toán (nhóm tự mở rộng, hướng lợi nhuận phía người bán): chủ shop nhỏ bán cùng sản phẩm trên Shopee, TikTok Shop và Lazada bị trừ nhiều khoản trên từng đơn, mỗi sàn một biểu phí và mốc đổi phí riêng, nên không biết khoản nào bắt buộc, khoản nào là chương trình tự bật đang ăn lãi. Lát cắt: xem §4.
Data nền: `data/07_Ecommerce_Seller_Store.xlsx` (nguồn ngoài nhóm tự tìm, là data luyện tập giả lập; đã phân tích, không dùng làm đầu vào). Data chạy thử tự sinh có seed ở `data/synthetic/`, không tính là bằng chứng pain.

## §0. Hiện tại việc này diễn ra thế nào *(guide 1.1)*
- **Luồng hiện tại** (theo hướng dẫn công khai của sàn và các bài hướng dẫn người bán; nhóm không có tài khoản người bán nên **không có ảnh chụp**):
  1. Đơn giao xong, tiền về số dư người bán. Shopee: Kênh Người Bán › Tài chính › Doanh thu › Chi tiết › Đã thanh toán ([BigSeller](https://www.bigseller.com/blog/articleDetails/shopee-tra-tien-cho-nguoi-ban-khi-nao.4996.htm), [GHN](https://ghn.vn/blogs/tip-ban-hang/phi-thanh-toan-shopee-la-gi)). TikTok Shop và Lazada có màn tương tự (quyết toán / chi tiết giao dịch).
  2. Chủ shop mở từng đơn, thấy một danh sách khoản trừ: phí cố định, phí xử lý giao dịch (tên cũ "phí thanh toán"), Voucher Xtra, tiếp thị liên kết, phí hạ tầng, thuế khấu trừ, "phí khác"… Mỗi sàn đặt tên và tỉ lệ khác nhau.
  3. Muốn biết khoản nào đúng thì tự tra trang biểu phí, nhưng biểu phí đổi ít nhất 7 mốc từ 4 đến 8/2026 (`CONTEXT.md` › Thực trạng 2026). Cũng có thể tải báo cáo thu nhập (Excel) rồi tự cộng bằng tay.
  4. Thấy khoản lạ thì hỏi kênh hỗ trợ người bán. Review cho thấy nhân viên hỗ trợ thường không giải thích được (`evidence/summary.md`, trích dẫn 2).
  5. Tính lãi thật (trừ giá vốn) thì tự làm trên Excel, hoặc dùng công cụ báo cáo lãi tổng (BigSeller, Sapo).
- **Công cụ / AI đang được dùng:** báo cáo thu nhập của chính sàn (liệt kê khoản trừ, không giải thích); BigSeller Profit Report (lãi theo đơn và theo shop, [help center](https://help.bigseller.pro/en_US/detailPage/10/1/8346/content)); Sapo (quản lý bán hàng đa kênh, chưa kiểm tính năng lãi theo đơn). Chưa thấy công cụ nào gắn từng khoản trừ với luật phí tại ngày đặt đơn: *chưa kiểm hết, tìm trên web 27/11/2026*.

## §1. Người dùng & bằng chứng *(guide 1.1, 1.2)*
- **Người dùng chính:** chủ shop nhỏ (1–5 người) bán cùng sản phẩm trên Shopee, TikTok Shop và Lazada, tự đối chiếu tiền về từng đơn.
- **Việc họ cố làm xong:** kiểm xem tiền về của từng đơn vừa thanh toán có đúng không và đơn đó lãi thật bao nhiêu, ngay khi tiền về, trên từng sàn.
- **Hôm nay họ giải bằng gì, hỏng ở đâu, vì sao chưa bỏ:** mở chi tiết thanh toán, tự tra biểu phí, tự cộng trên Excel. Hỏng ở 3 chỗ: tên phí đổi, tỉ lệ đổi theo ngày, và không phân biệt được khoản bắt buộc với chương trình shop tự bật. Chưa bỏ vì không rời sàn được, và công cụ báo cáo lãi tổng chỉ cho con số tổng, không nói khoản nào sai hay nên tắt gì.
- **Pain:** chủ shop bán đa sàn mở chi tiết thanh toán từng đơn thấy bị trừ nhiều khoản, mỗi sàn một tên gọi, tỉ lệ và mốc đổi phí riêng. Họ không biết khoản nào bắt buộc, khoản nào là chương trình tự bật đang ăn lãi, nên tiếp tục bán những đơn lãi mỏng hoặc lỗ mà không biết.
- **Bằng chứng** (chi tiết: `evidence/summary.md`, `evidence/data-mining.md`): 88/900 review mới nhất của 3 app người bán (9,8%) là pain về tiền sau khi đọc lại; ước lượng ≈ 12,4% nếu tính cả phần từ khoá bỏ sót. Shopee cao nhất, 56/300 (18,7%), riêng phí sàn 44/300 (14,7%). Trong 88 review, phí sàn chiếm 62 (70,5%); 25 review (28,4%) nói rõ lỗ hoặc gần như không còn lãi. TikTok Shop 14/300 (4,7%), Lazada 18/300 (6,0%); Lazada trải từ 06/2024 nên so giữa app là so trên khoảng thời gian khác nhau. **Số đã chốt:** AI gán nhãn, người kiểm 30 dòng khớp 28/30 (93%), 2 dòng lệch không đổi số đếm. **Kết luận:** pain có thật và tập trung ở phí trên từng đơn. Review không đo được tỉ lệ người bán gặp pain.

## §2. Impact & quyết định chọn *(guide 1.3)*

| Hướng | Bao nhiêu người gặp | Bao nhiêu lần / tháng | Mỗi lần tốn gì | Impact / tháng | Làm kịp không | Chọn? |
|---|---|---|---|---|---|---|
| **A. Soi từng đơn đa sàn** ("Lãi đi đâu?"): gắn mỗi khoản trừ với luật phí, chỉ công tắc ăn lãi, so sàn | ~601.800 shop có đơn năm 2025 (Metric, theo `CONTEXT.md`; nhóm chưa dán link gốc) × 30% bán ≥ 2 sàn *(tự ước tính)* ≈ 180.000 shop | 8 lần soát đơn *(tự ước tính: 2 lần / tuần)* | 15 phút tra biểu phí và cộng Excel *(tự ước tính)*; thêm khoản bị trừ sai không phát hiện (review: đơn 180k bị trừ 51k) | ≈ 180.000 × 8 × 15 phút ≈ 360.000 giờ | Kịp: một agent, data giả có seed, bảng phí 3 sàn đã có | ☑ |
| B. Chẩn đoán lãi cuối tháng của cả shop (hướng bản 17:00) | Cùng tập shop | 1 lần / tháng | 1–2 giờ làm báo cáo *(tự ước tính)* | ≈ 180.000 × 1 × 90 phút ≈ 270.000 giờ | Kịp, nhưng BigSeller, Sapo đã làm | ☐ |
| C. Hỗ trợ tranh chấp hoàn hàng / bom hàng | 30/88 review pain về tiền nhắc hoàn trả (34,1%) | Theo số đơn hoàn *(chưa có số)* | 50–60k mỗi đơn hoàn theo lời review *(1 review, không đại diện)* | Chưa tính được | Không kịp: cần bằng chứng tranh chấp thật, quyết định thuộc sàn (ngoài thẩm quyền) | ☐ |

- **Bằng chứng chống lưng cho từng thừa số:** "bao nhiêu người gặp" không đo được từ review (review chỉ cho tỉ lệ trong người viết review: 88/900 than về tiền, 62/900 than phí sàn). "Mỗi lần tốn gì" có 25/88 review nói rõ lỗ hoặc lãi mỏng, và trích dẫn 2–3 ở `evidence/summary.md` (133k phí trên đơn 2 × 249k; 51k trên đơn 180k). Các thừa số còn lại là *(tự ước tính)*.
- **Impact / tháng** của hướng chọn = ~180.000 shop × 8 lần × 15 phút ≈ **360.000 giờ / tháng**. Nguồn từng thừa số: số shop 601.800 lấy từ `CONTEXT.md` (Metric, năm 2025); tỉ lệ bán ≥ 2 sàn 30%, 8 lần / tháng và 15 phút / lần đều là *(tự ước tính)*, cần 2–3 người bán dùng thử để kiểm lại (`validation/log.md`).
- **Hướng đã loại và vì sao:** B, vì phàn nàn trong review tập trung ở phí trên từng đơn chứ không ở báo cáo tổng, và BigSeller, Sapo đã có báo cáo lãi tổng. B được giữ lại thành phần demo bổ sung "import file export tháng" để chọn đơn đáng soi (§4). C, vì cần dữ liệu tranh chấp thật và quyết định cuối nằm ở sàn, AI không có thẩm quyền.
- **Số lần / tháng của từng kiểu người dùng** (cho persona §8, đều *(tự ước tính)*): shop nhỏ ít đơn soi 4 lần / tháng, mỗi lần 1 đơn; shop đang bán đều 8 lần, mỗi lần 1–3 đơn; shop bán cùng sản phẩm trên 3 sàn 8 lần, mỗi lần 3 đơn để so sàn.

## §3. Giải pháp tương tự *(guide 2.1)*
- **BigSeller Profit Report** ([help](https://help.bigseller.pro/en_US/detailPage/10/1/8346/content)): đáng học là công thức lãi rõ ràng (doanh thu đơn − giá vốn + phí khác) và đồng bộ đủ Shopee, TikTok Shop, Lazada. Đáng né là đơn thiếu giá vốn thì giá vốn ghi là 0, ra lãi ảo, và chỉ có số tổng, không nói khoản nào sai luật. **Mình khác:** thiếu giá vốn thì hỏi lại (Ask), và mỗi khoản trừ gắn với một luật phí có ngày hiệu lực và nguồn.
- **Sapo (bán hàng đa kênh):** đáng học là quản lý đơn của nhiều sàn ở một chỗ. Đáng né *(chưa kiểm chi tiết tính năng lãi)* là chỉ dừng ở báo cáo. **Mình khác:** không quản lý đơn, chỉ soi một vài đơn để quyết định tắt, giữ hay chỉnh chương trình nào.
- **Báo cáo thu nhập của chính sàn** (Shopee: Tài chính › Doanh thu): đáng học là đủ dòng, đúng tên khoản. Đáng né là không giải thích khoản nào bắt buộc, khoản nào do chương trình tự bật, và không so với biểu phí tại ngày đặt đơn. **Mình khác:** dùng đúng tên dòng của sàn (kể cả tên cũ), rồi gắn chip bắt buộc / công tắc / không khớp luật và soạn nháp câu hỏi gửi sàn.

## §4. Thiết kế *(guide 2.2, 3.2)*
- **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả): Một chủ shop nhỏ bán cùng sản phẩm trên Shopee, TikTok Shop và Lazada · dán chi tiết thanh toán của một hoặc vài đơn vừa về tiền (sàn nào cũng được) kèm giá vốn · agent quyết định mỗi khoản trừ thuộc luật phí nào của sàn đó tại ngày đặt đơn, công tắc nào đang ăn lãi, sàn nào lãi thật nhiều nhất, và có cần hỏi lại hay soạn nháp câu hỏi gửi sàn không · chủ shop biết lãi thật mỗi đơn, mỗi sàn và nên tắt, giữ hay chỉnh công tắc nào ở sàn nào.
- Không làm (≥3 điều): không tự tắt chương trình hay tự gửi gì cho sàn (chỉ soạn nháp) · không kết nối API / tài khoản sàn thật · không làm báo cáo lãi cả tháng (BigSeller, Sapo đã có) · không gợi ý né phí, né thuế, buff đơn, review ảo · không chat tự do ngoài phạm vi đơn đã dán.
- **Demo bổ sung (ngoài lát cắt, không tính vào §7):** import file export tháng của 3 sàn + file giá vốn → code (`data/import_export.py`) tính lãi theo sàn và SKU, liệt kê đơn lệch luật, công tắc ăn lãi, ROAS so với hoà vốn, rồi chủ shop chọn đơn đáng soi để đưa vào luồng agent ở trên. Dùng chung bảng phí và công cụ tính, không có metric hay câu thử riêng. Đây là danh sách đơn cần soi, không phải báo cáo lãi tổng.
- **Sơ đồ** (Mermaid):

```mermaid
flowchart LR
  U[Chủ shop dán 1–5 đơn<br/>Shopee / TikTok / Lazada + giá vốn] --> G{Lọc yêu cầu<br/>code + AI}
  G -- né phí / gian lận / lệnh chèn --> R[Refuse]
  G --> P[Agent lập kế hoạch<br/>tách đơn, nhận sàn + ngày, tách dòng]
  P --> L{{Vòng công cụ ≤ 8 lượt/đơn, ≤ 20/phiên}}
  L <--> T1[(fee_rules.csv<br/>để TÍNH)]
  L <--> T2[(chunks.jsonl 3 sàn<br/>để TRÍCH)]
  L --> C[compare_platforms<br/>khi ≥ 2 sàn]
  L --> V{Bước kiểm code<br/>số · rule_id · chunk_id · sàn · ngày}
  C --> V
  V -- sai --> L2[Agent sửa 1 lần] --> V
  V -- vẫn sai --> F[Fallback: chỉ bảng dòng]
  V -- đúng --> D{Quyết định}
  D --> A[Act: lãi thật + 1–2 công tắc]
  D --> K[Ask: hỏi lại, lưu trạng thái]
  D --> E[Escalate: nháp câu hỏi gửi sàn]
  A & K & E --> H[Chủ shop quyết]
```

- **Hình dạng:** [ ] workflow cố định · [x] một agent (có giới hạn) · [ ] nhiều agent — Đầu vào thay đổi theo từng lần (1–5 đơn, 3 sàn, tên phí cũ lẫn mới, dòng lạ, thiếu giá vốn) nên số bước và công cụ cần gọi khác nhau mỗi đơn; agent tự lập kế hoạch, chọn công cụ, hỏi lại có nhớ trạng thái và tự sửa sau bước kiểm. Mọi phép tính khoá cứng trong code. Không chọn nhiều agent vì không có việc nào cần chia vai riêng, chỉ thêm chi phí và chỗ hỏng. Workflow cố định chỉ dùng để cứu hộ nếu 23:30 T6 vòng agent chưa qua `eval --try` (vẫn giữ 3 sàn).
- **AI dựa vào đâu** — mỗi công cụ (khớp `codebase/tools.py`):

  | Công cụ | Input | Output | Tác động ra ngoài? |
  |---|---|---|---|
  | `check_lines_sum` | các dòng đã tách, tiền về | khớp / lệch bao nhiêu | Không |
  | `lookup_fee_rule` | tên phí (cả tên cũ), ngày đặt, loại shop, ngành, sàn | luật khớp (`rule_id`, loại, tỉ lệ, trần, hiệu lực, `chunk_id`, nguồn) hoặc `null` | Không |
  | `expected_amount` | `rule_id`, số tiền căn cứ | số đúng luật, độ lệch | Không |
  | `unit_profit` | giá, các dòng, giá vốn | tiền về, lãi thật, phần ăn lãi của từng công tắc | Không |
  | `switch_what_if` | dòng, công tắc, giá trị mới | lãi sau khi đổi; số đơn được phép giảm mà vẫn có lợi | Không |
  | `breakeven_roas` | biên lãi trước quảng cáo | 1 ÷ biên lãi | Không |
  | `compare_platforms` | các đơn cùng sản phẩm ở ≥ 2 sàn, giá vốn | lãi thật mỗi sàn, công tắc lớn nhất mỗi sàn, sàn lãi nhất | Không |
  | `ask_user` | câu hỏi | dừng lượt, lưu trạng thái phiên | Không |
  | `draft_platform_question` | đơn, dòng, số đúng luật, số bị trừ | nháp câu hỏi để chủ shop tự gửi | Chỉ soạn nháp, không gửi |
  | `search_policy` | câu hỏi, sàn, loại chính sách, k | ≤k đoạn chính sách chính thức kèm `chunk_id`, URL, ngày hiệu lực, điểm; `[]` khi không đủ gần | Không (đọc `data/<sàn>/policies/`, vd `data/tiktok_shop/policies/`, gọi API embedding cho câu hỏi) |

- **Mức tự động:** [x] AI gợi ý, người quyết · [ ] AI tự làm khi chắc, chuyển người khi không · [ ] AI tự làm — Tắt nhầm một chương trình đang có lợi hoặc khiếu nại sai với sàn đều đắt và khó sửa, nên agent chỉ phân tích, gợi ý và soạn nháp; chủ shop bấm thật.
- **Chỗ chặn rủi ro** (rủi ro lớn nhất của lát cắt bị chặn ở đâu, bằng gì): rủi ro lớn nhất là một con số sai hoặc trích nhầm luật của sàn khác → bước kiểm bằng code: mọi số trong câu trả lời có trong output công cụ (±0,1), mọi `rule_id`/`chunk_id` có thật, đúng sàn, đúng ngày hiệu lực; sai thì agent sửa 1 lần, vẫn sai thì chỉ trả bảng dòng. Công cụ tra luật và tìm chính sách lọc cứng theo `platform`.
- **Chỗ người duyệt** (việc AI không được tự làm): tắt / chỉnh chương trình (Voucher Xtra, tiếp thị liên kết, quảng cáo, voucher), gửi câu hỏi hay khiếu nại cho sàn, đổi giá bán.
- **Nguyên tắc thiết kế** (≥3, bắt buộc G10):

  | Nguyên tắc | Chỗ cụ thể trên sơ đồ / trong bản chạy thử |
  |---|---|
  | G10 — thu hẹp phạm vi khi không chắc | Thiếu giá vốn hoặc tổng không khớp → Ask; dòng không khớp luật nào → Escalate (nháp gửi sàn), không đoán |
  | Code tính, AI phán đoán | Mọi con số từ `fee_rules.csv` qua công cụ; agent chỉ chọn luật, công tắc, quyết định |
  | Minh bạch nguồn | Mỗi dòng kèm `rule_id`, `chunk_id`, link nguồn, ngày hiệu lực, cờ `da_doi_chieu` |

- Phần nào còn giả (công cụ trả dữ liệu giả, model chế độ giả…) — ghi rõ, không giả làm thật: đơn hàng là dữ liệu giả có seed (`data/synthetic/`); một số dòng trong `fee_rules.csv` chưa có nguồn chính thức (`da_doi_chieu=gia_dinh`); trước khi nối model thật, `agent.py` chạy với AI giả.

## §5. Chỗ khó — 4 lớp + ≥6 kịch bản + 2 tấn công *(guide 2.3)*

| Kịch bản | Lớp (1–4) | Hành vi mong muốn (nói gì, hiện gì, cho làm gì tiếp) | Câu thử |
|---|---|---|---|
| Tên phí cũ hoặc mức phí đổi theo ngày; cần đúng nguồn và hiệu lực | 1 — nguồn sự thật | Tra theo platform + ngày đặt; thiếu nguồn/date thì không đoán, hỏi lại hoặc Escalate | B14, B26–B30 |
| Thiếu dòng, giá vốn hoặc tổng không khớp | 2 — mơ hồ/thiếu dữ liệu | Ask đúng thông tin còn thiếu; không đưa lợi nhuận/số tiền tự ước lượng | B16–B18 |
| So chéo cùng SKU trên nhiều sàn | 2 — mơ hồ/thiếu dữ liệu | Tách từng đơn/sàn, tính riêng; chỉ so khi đủ giá vốn và dữ liệu | B19–B21, B27–B28 |
| Vượt trần, sai tỷ lệ theo thời điểm hoặc có dòng lạ | 4 — đặc thù lĩnh vực | Dùng code đối chiếu rule và độ lệch; Escalate với bản nháp, không tự cân đối | B13–B15 |
| Yêu cầu né phí, gian lận hoặc dùng dữ liệu shop khác | 3 — ngoài phạm vi/thẩm quyền | Refuse phần sai phạm; đề nghị đối chiếu đúng luật | B22–B23 |
| *(tấn công)* Chỉ thị chèn trong nội dung chữ dán | 3 — ngoài phạm vi/thẩm quyền | Xem nội dung dán là dữ liệu không tin cậy; không làm theo lệnh chèn | B24–B25 |
| *(tấn công)* Yêu cầu sửa số/khai sai để né phí | 3 — ngoài phạm vi/thẩm quyền | Refuse, không tạo cách làm sai; giữ nguyên input để người dùng kiểm tra hợp lệ | B22–B23 |
| Review mô tả phí/tiền về khó hiểu | 1 — nguồn sự thật | Giải thích từng khoản từ rule và nguồn; review chỉ nêu pain, không dùng làm căn cứ tính | B26–B30 |

(1) nguồn sự thật · (2) mơ hồ / thiếu thông tin · (3) ngoài phạm vi / thẩm quyền · (4) đặc thù lĩnh vực (sai thì người dùng mất gì đắt nhất)

## §6. Bốn đường đi của trải nghiệm
- Mọi thứ suôn sẻ: dán 1–5 đơn, giá vốn và sàn/ngày → parse → tra `fee_rules` + `search_policy` → code tính → bước kiểm → giải thích lãi và 1–2 công tắc; chủ shop tự quyết (B01–B12, B19–B21).
- Không chắc (lớp 2): thiếu giá vốn/dòng hoặc tổng không khớp → Ask đúng trường thiếu → tiếp tục sau khi người dùng bổ sung (B16–B18).
- Không có căn cứ (lớp 1): không có rule/chunk đúng sàn và ngày → nói rõ chưa đủ căn cứ, không lấy review làm sự thật; hỏi thêm hoặc Escalate (B14, B26–B30).
- Người dùng sửa: người dùng cập nhật ngày, dòng hoặc giá vốn → chạy lại phép cộng và tính trên input mới; giữ cảnh báo cũ trong trace.
- Bị đòi ngoài phạm vi (lớp 3): yêu cầu né phí, gian lận, truy cập shop khác hoặc làm theo chỉ thị nhúng → Refuse phần đó, đưa hướng tuân thủ (B22–B25).
- Trường hợp đặc thù lĩnh vực (lớp 4): vượt trần, sai tỷ lệ, dòng lạ hoặc hoàn hàng → đối chiếu bằng code; báo delta và soạn nháp khi cần, không tự gửi (B13–B15).

## §7. Đánh giá & chuẩn "đạt" *(guide 2.4, 4.1)*
- Data card: `data/DATA_CARD.md` · bộ câu thử: `eval/benchmark.csv` — 30 câu CP3 (thuong 20 · kho 6 · tu_choi 4; Shopee 12 · TikTok 13 · Lazada 10, mỗi sàn ≥8; 5 câu so chéo) · metric: `eval/metric_spec.yaml` (11 metric: 3 thuộc chuẩn đạt + 8 phụ). Nguồn review: 10/30 câu; đáp án số vẫn lấy từ seed synthetic.
- **Chuẩn "đạt"** (chốt **trước 19:30 Thứ Sáu 27/11**, giữ nguyên đến 23:59 Thứ Bảy 28/11): "Đạt khi ≥ 90% dòng phí được gắn đúng luật, VÀ 100% con số trong câu trả lời khớp output công cụ, VÀ 100% câu `tu_choi` bị từ chối."
- Metric phụ (báo cáo, không thuộc chuẩn đạt; khớp `eval/metric_spec.yaml`): quyết định đúng (act / ask / escalate / refuse) ≥ 85% · gắn đúng luật **tách theo từng sàn** (Shopee · TikTok Shop · Lazada) · so chéo sàn chọn đúng sàn lãi nhất ≥ 80% · bắt dòng lệch ≥ 90% · truy xuất đúng đoạn trong top 5 ≥ 80% · hỏi lại khi thiếu dữ liệu 100% · công tắc khớp quy tắc code ≥ 80% · số lượt công cụ trung bình / đơn, tỉ lệ tự sửa thành công, tỉ lệ rơi về fallback.
- Bộ câu thử CP3: 30 câu, ≥8 mỗi sàn, ≥3 so chéo, ≥5 `kho`, ≥3 `tu_choi`, ≥1/3 bối cảnh theo review/YouTube. Builder sinh đáp án seed 42 bằng code từ `data/fee_rules.csv` vào thư mục tạm; không sửa bộ synthetic dùng chung.
- Kết quả CP3: lượt hợp lệ chưa có; lần `python run.py eval` trước chạy 30 câu với model fake nên không chấm và không ứng với benchmark đã làm mới. Production retrieval smoke với BGE-M3 + BM25 RRF đạt 10/10 top-5 (Shopee 4/4, TikTok 3/3, Lazada 3/3); lọc ngày hiệu lực qua kiểm tra chunk có ngày nguồn rõ. `effective_date` để trống khi nguồn không nêu. Thái đã cập nhật liên kết `fee_rules.csv` → chunk; unit test hiện 21/21. Xem `eval/README.md` và `eval/report.md`.

## §8. Chi phí khi dùng thật *(guide 4.2)*
- Persona + giá: `cost/personas.yaml` · lượt mô phỏng: `cost/simulate-__.csv` (__ phiên)
- Chi phí / task thành công: __ (model __) · __ (model __)
- Chi phí / tháng ở quy mô thật: thấp __ · cơ sở __ · cao __ → chi tiết `cost/cost-estimate.md`
- So với impact / người / tháng (§2): đáng làm không, vì sao:

## §9. Rủi ro & an toàn
- Dữ liệu: đã ẩn danh gì, không thu gì, không đưa gì vào model gói miễn phí:
- AI **không được** làm gì kể cả khi người dùng yêu cầu:
- Ai có thể bị hại nếu AI sai, và nhóm chặn thế nào:

## §10. Phân công & changelog
- Phân công có tên (theo chặng, chia cặp — guide "Cách chia việc"): __
- Dùng AI vào việc gì (2–3 dòng; chi tiết `docs/ai-usage.md`):
- Nhật ký thay đổi — **mọi thay đổi sau CP2 19:30 Thứ Sáu 27/11 phải có dòng ở đây**:

**CP2 → CP4** (vd thu hẹp lát cắt, hỏi thêm người dùng, lần cải tiến trước lượt 2)

| Thời điểm | Đổi gì | Vì sao (trỏ về câu thử / lỗi / bằng chứng nào) |
|---|---|---|
| 22:10 T6 27/11 | §4 thêm dòng "Demo bổ sung": import file export tháng. Không đổi lát cắt, không đổi §7 | Shop bán cả 3 sàn thường có sẵn file export tháng; dùng để chọn đơn đáng soi khi demo. Có data mẫu `data/demo_import/` |
| 00:28 T7 28/11 | Chốt bộ CP3 30 câu và hoàn thiện §5–§6; chạy benchmark kiểm cấu trúc, truy xuất lexical 10 câu và thử `run.py eval` | Yêu cầu MI-9; retrieval trượt 3 câu; eval dùng model giả nên không tạo lượt hợp lệ (xem `eval/report.md`) |
| 00:43 T7 28/11 | Làm mới đáp án benchmark theo `data/fee_rules.csv`; cập nhật kết quả production retrieval smoke (10/10, BM25 fallback) và giới hạn vector | Bảng phí đã được đưa vào repo; lượt fake cũ không ứng với bộ hiện tại; kiểm tra `eval/build_benchmark.py`, `python run.py check`, `eval/retrieval_smoke.py` |
| 00:50 T7 28/11 | Tích hợp index BGE-M3 mới từ Thái; cập nhật smoke theo chunk ID mới và ghi rõ trạng thái kiểm thử vector | `main` bổ sung 1.089 vector; smoke BM25 vẫn 10/10; môi trường hiện thiếu `sentence-transformers` và metadata ngày hiệu lực còn thiếu ở nhiều chunk |
| 00:54 T7 28/11 | Ghi nhận lỗi liên kết nguồn fee rule sau khi kho đổi chunk ID | Unit test kiểm tra `fee_rules.csv` với `data/policies/chunks.jsonl` thấy 28/57 chunk_id không còn đúng sàn; cần Thái cập nhật dữ liệu nguồn |
| 01:10 T7 28/11 | Cài `sentence-transformers`, chạy retrieval smoke với BGE-M3 + BM25 RRF; để trống ngày hiệu lực nếu policy không ghi ngày | Query encoder chạy được; kết quả top-5 10/10 và lọc ngày PASS; không tự điền metadata ngày thiếu |
| 01:28 T7 28/11 | Tích hợp cập nhật policy + `fee_rules.csv` của Thái; xác nhận test và smoke retrieval; cập nhật trạng thái MI | `python -m unittest discover -s tests` 21/21, `python run.py check` sạch, BGE-M3 smoke 10/10. MI-10 còn chờ cấu hình model thật và link video demo |
| 08:23 T7 28/11 | Chạy và chấm MI-10 lượt model thật đủ 30 câu; ghi điểm và nhóm lỗi vào hồ sơ đánh giá | `run-1@20261128-082327`, `gpt-6.2-sol`; 21/30 theo pass criterion, trace check 0 lỗi/cảnh báo. Ba metric chuẩn §7 cần báo cáo riêng; video tạm bỏ qua theo yêu cầu của Hà |
| 09:43 T7 28/11 | Chạy và chấm MI-11 lượt 2 cùng benchmark/model sau một cải tiến HU-11; cập nhật so sánh x/N trong hồ sơ | `run-2@20261128-094309`, `gpt-6.2-sol`; HU-11 prompt v0.4 giảm từ chối nhầm đơn hợp lệ. Điểm theo pass criterion 21/30 → 30/30, không có câu tệ đi; trace check 0 lỗi/cảnh báo. Metric §7 chưa được tổng hợp riêng |
| 28/11 | §0–§3 điền lần đầu (HA-3): luồng hiện tại, người dùng, impact 3 hướng, giải pháp tương tự. Không đổi lát cắt, không đổi §7 | Số bằng chứng lấy từ `evidence/data-mining.md` (88/900 đã đọc lại); thừa số impact không có nguồn ghi *(tự ước tính)* |
| 28/11 | §1–§2 chốt số (HA-9): ghi tỉ lệ khớp người kiểm 28/30, số theo app, thừa số impact nào có bằng chứng. Không đổi số bằng chứng, không đổi §7 | Hà kiểm tay 30 dòng nhãn AI (`evidence/data-mining.md` mục 6); 2 dòng lệch không đổi số đếm |

**Sau CP4 (đến 23:59 Thứ Bảy 28/11)** (sửa theo góp ý — không sửa chuẩn "đạt", câu thử, số bằng chứng, kết quả các lượt đã chạy)

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
|  |  |  |
