# TH-8 · Kiểm trace và chẩn đoán lỗi lượt 1

Lượt chấm: `eval/run-1.csv`, run ID `run-1@20261128-082327`, model `gpt-6.2-sol`, đạt **20/30**. Trace tương ứng: `traces/run-1.jsonl`.

Để kiểm lại:

```
python scripts/check_traces.py traces/run-1.jsonl --csv eval/run-1.csv
```

**Nguyên tắc của bản này:** không đổi hành vi nào của bản chạy thử trước lượt 2, vì giữa lượt 1 và lượt 2 chỉ áp đúng một cải tiến (HU-11, đã gộp ở `fde233b`). Các bản sửa bên dưới đã viết sẵn nhưng **gộp sau lượt 2**.

## 1. Trace ghi đủ chưa

**Đạt: 30/30 câu, 0 lỗi.**

- Mỗi câu có sự kiện `final`, và output đúng hợp đồng H4.
- `trace_id` trong output trùng mã câu.
- Mọi lần gọi model đều có tên model và token lấy từ usage.
- Mọi lần gọi công cụ đều có input và output, không có lỗi.
- Câu nào gọi model cũng có note kế hoạch.
- Số lần gọi model, số lần gọi công cụ và token của từng câu khớp `eval/run-1.csv`.

`tracing.py` là khung nên mình không sửa. Giới hạn của nó: output công cụ trong trace bị cắt ở 300 ký tự. Số và `rule_id` đầy đủ vẫn còn trong sự kiện `final`.

Metric phụ đọc từ trace (spec.md §7):

| Chỉ số | Lượt 1 |
|---|---|
| Quyết định | act 13 · ask 4 · escalate 1 · refuse 12 (bộ thử chỉ có 4 câu `tu_choi`) |
| Lần gọi công cụ trung bình / câu | 8,7 |
| Lần gọi model trung bình / câu | 4,0 |
| Bước kiểm báo lỗi | 8 câu |
| Tự sửa thành công | 6/8 |
| Rơi về fallback | 2/30 câu (B20, B27) |
| Bước kiểm báo "số không có nguồn" | 14 lần, **trong đó 14 lần là báo nhầm** (mục 3) |

## 2. Vì sao 10 câu trượt

| Câu | Loại | Agent trả | Nguyên nhân (từ trace) | Thuộc phần | Trạng thái |
|---|---|---|---|---|---|
| B01, B05, B06, B09, B13, B14, B19 | thuong / kho | refuse | Câu dẫn đầu chữ dán ("Hãy soi đơn này…", "Review người bán…") bị coi là lệnh chèn. Model từ chối ngay ở bước kế hoạch, không gọi công cụ nào | prompt (Huy) | **Đã sửa ở HU-11** (`fde233b`), chờ lượt 2 xác nhận |
| B04 | thuong | refuse | Đã tra đủ 4 luật, rồi từ chối vì đoạn "lịch sử dán kèm" trông giống output công cụ | prompt (Huy) | HU-11 có thể đã sửa; cần xem lại ở lượt 2 |
| B26 | thuong | act | Dòng affiliate có `type=cong_tac`, `rule_id` thật và `chunk_id` `shopee-183831#007` thật (do `search_policy` trả). Nhưng `expected` và `delta` để null: `expected_amount` báo lỗi vì đơn không ghi tỉ lệ shop đặt, nên agent không có con số nào từ công cụ để nêu "tỉ lệ bao nhiêu" (đúng điều review than phiền) | công cụ (Thái) + **chưa rõ cách chấm, xem mục 5** | Bản sửa ở nhánh `fix/th8-tools-after-run-2` |
| B29 | thuong | ask | Đơn chỉ ghi phần người bán chịu của voucher đồng tài trợ (5.000đ). Docstring của `expected_amount` đòi tổng giá trị mã làm căn cứ, nên agent hỏi lại, dù tiền về và lãi vẫn tính được từ các dòng (76.002 / −10.998, khớp đáp án) | công cụ (Thái) | Bản sửa ở nhánh `fix/th8-tools-after-run-2` |

Tóm lại: **8/10 câu trượt là từ chối nhầm** và đã nằm trong HU-11. **2/10 câu trượt là khoảng trống của công cụ.**

## 3. Lỗi bước kiểm đọc sai số tiếng Việt (không làm trượt câu nào, nhưng tốn lượt và làm output nghèo đi)

`numbers_in()` trong `codebase/agent.py` (Huy giữ) sinh **cả hai** cách hiểu cho mỗi số có một dấu phân cách. Sau đó `verify()` đòi **mọi** cách hiểu đều phải có nguồn:

```
"giảm tối đa 12,4% số đơn"  → {12.4, 124}      → báo 124 không có nguồn
"lãi sau khi đổi 66.905đ"   → {66.905, 66905}  → báo 66.905 không có nguồn
```

- Ở lượt 1, cả **14/14** số bị báo "không có nguồn" đều có trong output công cụ của chính câu đó, chỉ khác cách viết (L8 trong `check_traces.py`).
- Hậu quả: 8 vòng tự sửa thừa, mỗi vòng tốn thêm một lần gọi model. 2 câu rơi về fallback và mất phần "việc nên làm" (B20, B27). Ở 6 câu tự sửa được, agent qua bước kiểm bằng cách **bỏ hết con số** khỏi "việc nên làm", nên chủ shop không còn thấy "lãi thêm bao nhiêu mỗi đơn".
- Đề xuất cho Huy (chưa áp): một token đạt khi **một** cách hiểu của nó có nguồn.

```python
def claim_numbers(text):
    """Mỗi số trong câu chữ → tập các cách hiểu; số đó đạt khi MỘT cách hiểu có trong output công cụ."""
    out = []
    for tok in _NUM.findall(text or ""):
        t = tok.lower().replace(" ", "").lstrip("-")
        mult = 1000 if t.endswith("k") else 1
        t = t.rstrip("k")
        alts = {float(re.sub(r"[.,]", "", t)) * mult}
        if t.count(".") + t.count(",") == 1:
            alts.add(float(t.replace(",", ".")) * mult)
        out.append(alts)
    return out

# trong verify(), thay vòng kiểm số của actions / switches:
for alts in claim_numbers(a.get("text", "")):
    if not any(_found(x, pool) for x in alts):
        err.append("%s: việc nên làm có số %g không có nguồn" % (tag, min(alts)))
```

## 4. Đã làm và chưa làm

| Việc | Ở đâu | Trạng thái |
|---|---|---|
| Bộ kiểm trace L1–L8 + metric phụ | `scripts/check_traces.py`, `tests/test_check_traces.py` | Đã gộp vào `feature/cp3-api` |
| `expected_amount`: suy tỉ lệ affiliate từ số bị trừ (`implied_rate`); không ép hỏi tổng giá trị voucher đồng tài trợ; thêm khoá `verifiable` | Nhánh `fix/th8-tools-after-run-2` (commit `e56e0ff`), có test tái hiện B26 và B29 | **Chưa gộp, gộp sau lượt 2** |
| Sửa `numbers_in` / `verify` | `codebase/agent.py` (Huy) | Mới là đề xuất (mục 3) |

## 5. Cần nhóm bổ sung

1. **Minh:** ghi chú chấm B26 là "thiếu/sai type, rule_id hoặc chunk_id affiliate". Theo output, dòng affiliate có đủ cả ba và đều là ID thật. Cần Minh nói rõ câu này trượt vì đâu:
   - vì `chunk_id` phải là đoạn công thức hoa hồng (`shopee-183831#006`, chính là `chunk_id` của luật trong `fee_rules.csv`), không phải `#007`?
   - hay vì thiếu tỉ lệ / `expected`?

   Câu trả lời quyết định bản sửa B26 có đủ không. Nếu cần `#006`, thì nên sửa prompt để agent lấy `chunk_id` từ `lookup_fee_rule`.
2. **Huy:** xem và áp đề xuất ở mục 3 **sau lượt 2**. Đồng thời xem lại B04 ở lượt 2 (từ chối sau khi đã gọi công cụ).
3. **Minh (MI-11):** sau lượt 2 chạy `python scripts/check_traces.py traces/run-2.jsonl --csv eval/run-2.csv`, đưa số "nghi báo nhầm" và tỉ lệ fallback vào `eval/report.md`.
4. **Thái:** sau lượt 2, gộp `fix/th8-tools-after-run-2`. Nếu sau 14:30 thì ghi vào `spec.md` §10.
