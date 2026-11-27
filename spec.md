# AI SPEC — Chẩn đoán vì sao shop bán nhiều mà lãi thấp · Nhóm Hàllucinations · Phòng [XXX] · Zone [X]

> Mốc nộp: §7 chốt chuẩn "đạt" tại **CP2 19:30 Thứ Sáu 27/11** · §0–§7 nộp **CP3 10:00 Thứ Bảy 28/11** · đủ §0–§10 **CP4 14:30 Thứ Bảy 28/11** · §10 changelog ghi tiếp đến **23:59 Thứ Bảy 28/11**.
> Đầu mỗi mục ghi bước guide (`02-guide.md` trong repo đề) chỉ cách điền. Mỗi mục ngắn, có số và nguồn; chi tiết để ở file được trỏ tới. Xoá dòng hướng dẫn trong ngoặc vuông khi điền xong.

Track: [ ] A · [ ] B · [ ] C · [x] D · [ ] E — bài toán (nhóm tự mở rộng, hướng lợi nhuận phía người bán): chủ shop nhỏ bán trên Shopee/TikTok Shop thấy doanh thu tăng nhưng tiền về ít, vì phí sàn, voucher, quảng cáo, hàng hoàn nằm rải ở nhiều báo cáo nên không biết khoản nào đang ăn mất lãi. Lát cắt: một chủ shop nhỏ · cuối tháng dán số liệu doanh thu/chi phí (+ giá vốn) · chọn nguyên nhân chính làm lãi thấp và 2 hành động, mọi con số lấy từ công cụ tính · chủ shop biết nên cắt khoản nào, cắt bao nhiêu.
Data BTC cấp đã dùng (nếu có — không commit nguyên file): `data/07_Ecommerce_Seller_Store.xlsx` (data giả lập, chỉ để chạy thử, không tính là bằng chứng pain).

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
- **Lát cắt MỘT CÂU:** Chủ shop thường trên Shopee dán chi tiết thanh toán của một đơn vừa về cùng giá vốn; agent gắn từng khoản trừ với quy tắc phí hoặc công tắc, tính lãi đơn, rồi kết luận hoặc hỏi/chuyển trường hợp chưa rõ để chủ shop quyết định.
- **Không làm:** không phân tích toàn shop/tháng; không tự đổi cài đặt, hoàn tiền hay gửi khiếu nại; không hướng dẫn né phí, gian lận hoặc dùng dữ liệu shop khác.
- **Sơ đồ:**

    ```mermaid
    flowchart TD
      A[Chủ shop dán chi tiết đơn + giá vốn] --> B{Yêu cầu an toàn và đủ dữ liệu?}
      B -->|Ngoài phạm vi / độc hại| R[Refuse: từ chối và nêu hướng an toàn]
      B -->|Thiếu ngày, giá vốn hoặc tổng không khớp| Q[Ask: hỏi đúng dữ liệu còn thiếu]
      B -->|Đủ| C[Agent tách các dòng phí]
      C --> D[lookup_fee_rule + search_policy theo Shopee, ngày đặt]
      D --> E[Code: check_lines_sum + expected_amount + unit_profit]
      E --> F{Kiểm tra số, quy tắc và chunk nguồn đạt?}
      F -->|Không rõ / lệch / không có căn cứ| X[Escalate: chỉ soạn nháp câu hỏi, chủ shop tự duyệt/gửi]
      F -->|Đạt| G[Act: giải thích lãi đơn và 1–2 công tắc có thể cân nhắc]
      G --> H[Chủ shop xem nguồn và tự quyết]
    ```

- **Hình dạng:** [x] một agent · Agent giới hạn tối đa 8 lượt gọi công cụ, nhiệt độ 0; việc tách dòng và quyết định cần ngôn ngữ linh hoạt. Không chọn nhiều agent vì lát cắt một đơn, cần giảm phối hợp và điểm phát sinh sai; phép tính vẫn giao cho code xác định.
- **AI dựa vào đâu** — công cụ theo hợp đồng H3; phần hiện thực có thể đang được hoàn thiện:

  | Công cụ | Input | Output | Tác động ra ngoài? |
  |---|---|---|---|
  | `check_lines_sum(lines, payout)` | Các dòng đã tách, tiền về | Khớp hoặc độ lệch | Không |
  | `lookup_fee_rule(fee_name, order_date, shop_type, category, platform)` | Tên phí, ngày, loại shop/ngành, sàn | Quy tắc hiệu lực và nguồn hoặc `null` | Không |
  | `search_policy(query, platform, order_date)` | Câu hỏi, sàn, ngày đặt | Top-k đoạn chính sách có metadata | Không |
  | `expected_amount(rule_id, base_amount)` | Mã quy tắc, số tiền căn cứ | Số tiền theo quy tắc và độ lệch | Không |
  | `unit_profit(price, lines, cogs)` | Giá, khoản trừ, giá vốn | Tiền về, lãi thật, phần công tắc | Không |
  | `ask_user(question)` | Câu hỏi làm rõ | Dừng lượt để chờ chủ shop | Không |
  | `draft_platform_question(order_id, line, expected, actual)` | Dòng phí lệch và số đối chiếu | Bản nháp câu hỏi cho sàn | Không; chỉ nháp, người dùng tự gửi |

- **Mức tự động:** [x] AI gợi ý, người quyết — sai số phí có thể khiến shop quyết định giá/vận hành sai; mọi kết luận gắn nguồn, mọi phép tính do code kiểm, chủ shop chịu quyết định cuối.
- **Chỗ chặn rủi ro:** bộ lọc từ chối yêu cầu gian lận/né phí; thiếu dữ liệu thì Ask; không khớp quy tắc hoặc tổng thì Escalate; bước kiểm xác nhận số từ output công cụ và kiểm `chunk_id`/ngày trước kết luận.
- **Chỗ người duyệt:** chủ shop tự duyệt hành động với công tắc và tự gửi bản nháp cho sàn; agent không thay đổi dữ liệu hay liên hệ bên ngoài.
- **Nguyên tắc thiết kế** (≥3, bắt buộc G10):

  | Nguyên tắc | Chỗ cụ thể trên sơ đồ / trong bản chạy thử |
  |---|---|
  | G10 — thu hẹp phạm vi khi không chắc | Không tìm được quy tắc hiệu lực hoặc dữ liệu thiếu → Ask/Escalate, không ước lượng mức phí. |
  | Số phải kiểm chứng được | Tính tiền và lãi bằng công cụ; câu trả lời chỉ dùng số có trong output công cụ. |
  | Người giữ quyền quyết định | Chỉ đưa gợi ý và bản nháp; chủ shop tự thay đổi cài đặt hoặc gửi yêu cầu. |
  |  |  |
  |  |  |

- Phần nào còn giả (công cụ trả dữ liệu giả, model chế độ giả…) — ghi rõ, không giả làm thật:

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
- Data card: `data/DATA_CARD.md` · bộ câu thử: `eval/benchmark.csv` — 10 câu CP2 (thuong 4 · kho 4 · tu_choi 2) · metric: `eval/metric_spec.yaml` (5 metric). Retrieval hiện có: 10/10 chunk đích top-5 trên 130 chunk Lazada với lexical baseline (`eval/retrieval_smoke.py`); lần chạy ghi nhận chỉ có platform `lazada`, chưa có data Shopee/TikTok để chấm, và chưa đo `search_policy` sản phẩm.
- **Chuẩn "đạt"** (chốt **trước 19:30 Thứ Sáu 27/11**, giữ nguyên đến 23:59 Thứ Bảy 28/11): "Đạt khi ≥ 70% câu qua, và 100% số liệu khớp output công cụ, 100% câu từ chối bị từ chối an toàn". Ngưỡng 70% đã có trong bản làm việc; đối chiếu `CONTEXT.md` trước khi nộp vì tài liệu đó ghi ngưỡng chính là ≥90% dòng khớp luật.
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
