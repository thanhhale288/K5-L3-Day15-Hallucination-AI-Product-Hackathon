# AI SPEC — Lãi đi đâu? Agent soi đơn đa sàn (Shopee · TikTok Shop · Lazada) · Nhóm Hàllucinations · Lớp L3B · Phòng [XXX] · Zone [X]

> Mốc nộp: §7 chốt chuẩn "đạt" tại **CP2 19:30 Thứ Sáu 27/11** · §0–§7 nộp **CP3 10:00 Thứ Bảy 28/11** · đủ §0–§10 **CP4 14:30 Thứ Bảy 28/11** · §10 changelog ghi tiếp đến **23:59 Thứ Bảy 28/11**.
> Đầu mỗi mục ghi bước guide (`02-guide.md` trong repo đề) chỉ cách điền. Mỗi mục ngắn, có số và nguồn; chi tiết để ở file được trỏ tới. Xoá dòng hướng dẫn trong ngoặc vuông khi điền xong.

Track: [ ] A · [ ] B · [ ] C · [x] D · [ ] E — bài toán (nhóm tự mở rộng, hướng lợi nhuận phía người bán): chủ shop nhỏ bán cùng sản phẩm trên Shopee, TikTok Shop và Lazada bị trừ nhiều khoản trên từng đơn, mỗi sàn một biểu phí và mốc đổi phí riêng, nên không biết khoản nào bắt buộc, khoản nào là chương trình tự bật đang ăn lãi. Lát cắt: xem §4.
Data nền: `data/07_Ecommerce_Seller_Store.xlsx` (nguồn ngoài nhóm tự tìm, là data luyện tập giả lập; đã phân tích, không dùng làm đầu vào). Data chạy thử tự sinh có seed ở `data/synthetic/`, không tính là bằng chứng pain.

## §0. Hiện tại việc này diễn ra thế nào *(guide 1.1)*
- Luồng hiện tại của việc này, trong khoá hoặc trên app thật (3–5 bước; ảnh chụp từ tài khoản của mình, đã che thông tin):
- Công cụ / AI đang được dùng cho việc này (nếu có) + nguồn. Không kiểm được thì ghi "chưa kiểm":

## §1. Người dùng & bằng chứng *(guide 1.1, 1.2)*
- Người dùng chính (một vai cụ thể):
- Việc họ cố làm xong (`động từ + đối tượng + bối cảnh`, không có chữ AI):
- Hôm nay họ giải bằng gì, hỏng ở đâu, vì sao chưa bỏ:
- Pain (KHÔNG chữ AI): ai — đang làm gì — vướng đâu — hậu quả gì:
- Bằng chứng — số chính + kết luận (chi tiết: `evidence/summary.md`): __

## §2. Impact & quyết định chọn *(guide 1.3)*

| Hướng | Bao nhiêu người gặp | Bao nhiêu lần / tháng | Mỗi lần tốn gì | Impact / tháng | Làm kịp không | Chọn? |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |

- **Impact / tháng** của hướng chọn = __ người × __ lần × __ phút = __ — nguồn từng thừa số: __ (không có nguồn thì ghi rõ *(tự ước tính)*)
- Hướng ĐÃ LOẠI + vì sao (giữ lại, đừng xoá):
- Số lần / tháng của từng kiểu người dùng (dùng cho persona ở §8):

## §3. Giải pháp tương tự *(guide 2.1)*
- [sản phẩm / tính năng gần giống]: một điều đáng học · một điều đáng né · mình khác gì

## §4. Thiết kế *(guide 2.2, 3.2)*
- **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả): Một chủ shop nhỏ bán cùng sản phẩm trên Shopee, TikTok Shop và Lazada · dán chi tiết thanh toán của một hoặc vài đơn vừa về tiền (sàn nào cũng được) kèm giá vốn · agent quyết định mỗi khoản trừ thuộc luật phí nào của sàn đó tại ngày đặt đơn, công tắc nào đang ăn lãi, sàn nào lãi thật nhiều nhất, và có cần hỏi lại hay soạn nháp câu hỏi gửi sàn không · chủ shop biết lãi thật mỗi đơn, mỗi sàn và nên tắt, giữ hay chỉnh công tắc nào ở sàn nào.
- Không làm (≥3 điều): không tự tắt chương trình hay tự gửi gì cho sàn (chỉ soạn nháp) · không kết nối API / tài khoản sàn thật · không làm báo cáo lãi cả tháng (BigSeller, Sapo đã có) · không gợi ý né phí, né thuế, buff đơn, review ảo · không chat tự do ngoài phạm vi đơn đã dán.
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
  | `search_policy` | câu hỏi, sàn, ngày | top-k chunk (`chunk_id`, url, hiệu lực, text), lọc cứng theo sàn | Không |
  | `expected_amount` | `rule_id`, số tiền căn cứ | số đúng luật, độ lệch | Không |
  | `unit_profit` | giá, các dòng, giá vốn | tiền về, lãi thật, phần ăn lãi của từng công tắc | Không |
  | `switch_what_if` | dòng, công tắc, giá trị mới | lãi sau khi đổi; số đơn được phép giảm mà vẫn có lợi | Không |
  | `breakeven_roas` | biên lãi trước quảng cáo | 1 ÷ biên lãi | Không |
  | `compare_platforms` | các đơn cùng sản phẩm ở ≥ 2 sàn, giá vốn | lãi thật mỗi sàn, công tắc lớn nhất mỗi sàn, sàn lãi nhất | Không |
  | `ask_user` | câu hỏi | dừng lượt, lưu trạng thái phiên | Không |
  | `draft_platform_question` | đơn, dòng, số đúng luật, số bị trừ | nháp câu hỏi để chủ shop tự gửi | Chỉ soạn nháp, không gửi |

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
|  |  |  |  |
| *(tấn công)* |  |  |  |
| *(tấn công)* |  |  |  |

(1) nguồn sự thật · (2) mơ hồ / thiếu thông tin · (3) ngoài phạm vi / thẩm quyền · (4) đặc thù lĩnh vực (sai thì người dùng mất gì đắt nhất)

## §6. Bốn đường đi của trải nghiệm
- Mọi thứ suôn sẻ: · Không chắc (lớp 2): · Không có căn cứ (lớp 1): · Người dùng sửa:
- Bị đòi ngoài phạm vi (lớp 3): · Trường hợp đặc thù lĩnh vực (lớp 4):

## §7. Đánh giá & chuẩn "đạt" *(guide 2.4, 4.1)*
- Data card: `data/DATA_CARD.md` · bộ câu thử: `eval/benchmark.csv` — 26 câu (thuong 16 · kho 6 · tu_choi 4) · metric: `eval/metric_spec.yaml` (11 metric: 3 thuộc chuẩn đạt + 8 phụ)
- **Chuẩn "đạt"** (chốt **trước 19:30 Thứ Sáu 27/11**, giữ nguyên đến 23:59 Thứ Bảy 28/11): "Đạt khi ≥ 90% dòng phí được gắn đúng luật, VÀ 100% con số trong câu trả lời khớp output công cụ, VÀ 100% câu `tu_choi` bị từ chối."
- Metric phụ (báo cáo, không thuộc chuẩn đạt; khớp `eval/metric_spec.yaml`): quyết định đúng (act / ask / escalate / refuse) ≥ 85% · gắn đúng luật **tách theo từng sàn** (Shopee · TikTok Shop · Lazada) · so chéo sàn chọn đúng sàn lãi nhất ≥ 80% · bắt dòng lệch ≥ 90% · truy xuất đúng đoạn trong top 5 ≥ 80% · hỏi lại khi thiếu dữ liệu 100% · công tắc khớp quy tắc code ≥ 80% · số lượt công cụ trung bình / đơn, tỉ lệ tự sửa thành công, tỉ lệ rơi về fallback.
- Bộ câu thử dự kiến 30 câu: ≥ 8 mỗi sàn, ≥ 3 so chéo sàn, ≥ 5 `kho`, ≥ 3 `tu_choi`, ≥ 1/3 câu theo lời review / YouTube.
- Kết quả: lượt 1 __/__ (__%) · lượt 2 __/__ (__%) — run ID: __ / __ → chi tiết `eval/report.md`, hồ sơ `eval/README.md`

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
|  |  |  |

**Sau CP4 (đến 23:59 Thứ Bảy 28/11)** (sửa theo góp ý — không sửa chuẩn "đạt", câu thử, số bằng chứng, kết quả các lượt đã chạy)

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
|  |  |  |
