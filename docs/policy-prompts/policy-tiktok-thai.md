Bạn là coding agent (Claude Code/Cursor/Codex) giúp Thái trong repo hackathon "Lãi đi đâu?". Trước khi làm, đọc `AGENTS.md`, `CONTEXT.md`, `TASK.md` (hỏi người dùng nếu chưa chắc họ là ai; chỉ sửa file thuộc phạm vi dưới đây).

**Bối cảnh:** sản phẩm là agent soi từng đơn hàng trên Shopee, TikTok Shop, Lazada. Agent cần một kho chính sách có embedding để giải thích và trích dẫn (`search_policy` → `chunk_id`, `url`, `effective_date`). Ba bạn mỗi người làm kho của một sàn, **cùng một schema**. Việc của Thái: kho **TikTok Shop**.

**Lấy code nền:** pipeline dùng chung (`scripts/policies/{crawl,clean,chunk,embed,validate}.py`, `codebase/retrieval.py`, `codebase/policy_paths.py`) và tài liệu `docs/policy-schema.md` nằm trên nhánh `cp2-tiktokshop` (PR #1) và nhánh chứa schema. Nếu PR #1 đã merge vào `main` thì tạo nhánh từ `main`, chưa thì tạo từ `origin/cp2-tiktokshop`. Chạy `git fetch origin` trước. Không force-push, không sửa file của sàn khác.

## Hiện trạng kho TikTok Shop (nhánh `cp2-tiktokshop`, PR #1, commit `632d156`)

- Đây là kho **chuẩn của schema chung**. `validate.py --platform tiktok` ĐẠT: 22 tài liệu, 149 chunk, 149 vector (Gemini 768), đủ 5 `policy_type` (voucher 8 tài liệu, fee 6, return_refund 4, ads 3, settlement 1).
- Điểm yếu cần xử lý:
  1. `settlement` chỉ có 1 tài liệu và bài đó là "Thương lượng với người mua", **không phải bài về tiền về/đối soát**. Thực tế chưa có tài liệu nào về thời điểm tiền về, rút tiền, bảng sao kê, vì sao bị trừ.
  2. Gần như mọi `effective_date` trống (chỉ vài bài có). Retrieval đang phải dựa vào `updated_at`.
  3. Có thể thiếu: hoa hồng tiếp thị liên kết (affiliate) của nhà sáng tạo, chương trình miễn phí vận chuyển (Freeship), phí đơn hoàn/hoàn tiền, hoa hồng **theo ngành** (đã có "Phí Hoa Hồng Nền Tảng" cập nhật 2026-09-30, kiểm tra đã có bảng tỷ lệ theo ngành chưa).
- Bạn cũng giữ gộp kho (TH-1) và `search_policy` (TH-2).

## Việc cần làm (theo thứ tự)

1. **Merge PR #1:** kiểm `mergeable` (đã resolve conflict ở `632d156`, xác nhận lại với `main` mới nhất), chạy `validate.py --platform tiktok`, merge. Việc này mở khóa cho hai bạn kia vì pipeline dùng chung chỉ nằm ở nhánh này.
2. **Bổ sung tài liệu thiếu** vào `scripts/policies/urls_tiktok.txt` rồi chạy lại `crawl → clean → chunk → embed` (chạy tăng dần, chunk không đổi không gọi lại API): ít nhất 1–2 bài `settlement` đúng nghĩa (thanh toán/đối soát/sao kê/rút tiền), affiliate, Freeship/phí vận chuyển nếu có, đơn hoàn. Không đổi `doc_id` và `chunk_id` của bài đã có.
3. **Điền `effective_date`** cho bài nào ghi ngày hiệu lực trong nội dung (phí, hoa hồng). Sửa ở `clean.py`/`chunk.py` nếu bước trích ngày chưa bắt được, rồi chạy lại.
4. **Gộp kho (TH-1) theo cách mới, quan trọng:** `TASK.md` H1 và `CONTEXT.md` đang ghi **một** file `data/policies/chunks.jsonl`. Code thực tế (`policy_paths.py`, `retrieval.search(platform=…)`) dùng **mỗi sàn một thư mục** và tự lọc cứng theo sàn khi tìm. Không cần gộp thành một file, và không nên (gộp dễ đè file và vector khác nhau giữa các sàn). Đề xuất: giữ mỗi sàn một thư mục, sửa H1 trong `TASK.md`, `CONTEXT.md`, `AGENTS.md` (đang ghi `data/policies/...`) cho khớp. **Đây là file chung, báo cả nhóm trước khi push**, và ghi vào `spec.md` §10 nếu sau CP2.
5. **Nối `search_policy` trong `codebase/tools.py`:** nhận `platform` và `order_date`; lọc cứng theo sàn (đã có), và lọc theo hiệu lực: bỏ chunk có `effective_date` sau ngày đặt đơn. Không trộn chunk giữa các sàn.
6. Khi Huy (Shopee) và Minh (Lazada) mở PR, chạy `validate.py` cho cả 3 sàn trước khi merge từng PR.

## Đầu ra và tiêu chí xong

- PR #1 đã merge vào `main`. PR bổ sung (settlement, affiliate, ngày hiệu lực) với `validate.py --platform tiktok` vẫn ĐẠT.
- `TASK.md`/`CONTEXT.md`/`AGENTS.md` đồng bộ cách đặt kho (sau khi cả nhóm đồng ý).
- Mô tả PR có mục **phần còn thiếu**.
- Không commit `raw-tiktok/`, `.env`.

## Schema chung kho chính sách (3 sàn dùng một schema)

**Nguyên tắc:** TikTok Shop đã đúng schema này (validator báo ĐẠT). Shopee và Lazada đưa về cho khớp. Không sửa schema một mình; muốn đổi thì báo cả nhóm.

### 1. Vị trí file (mỗi sàn một thư mục, không ai đè file của ai)

```
data/<thư mục sàn>/policies/
    raw-<platform>/    HTML/PDF gốc, KHÔNG commit (đã có trong .gitignore)
    clean/             Markdown đã làm sạch, một file một tài liệu: <doc_id>.md
    manifest.csv       một dòng một tài liệu
    chunks.jsonl       một dòng một chunk
    index.jsonl        một dòng một vector
```

| platform | thư mục sàn |
|---|---|
| `tiktok` | `data/tiktok_shop/policies/` |
| `shopee` | `data/shopee/policies/` |
| `lazada` | `data/lazada/policies/` |

Đường dẫn khai báo ở `codebase/policy_paths.py` (`PLATFORM_DIRS`), nhánh `cp2-tiktokshop`/PR #1. Không tự thêm thư mục khác như `shopee_policy/`.

Mọi file: UTF-8 **không BOM**. `chunks.jsonl` và `index.jsonl` là JSONL (mỗi dòng một object), KHÔNG phải một mảng JSON.

### 2. `manifest.csv`: đúng 9 cột, đúng thứ tự

`doc_id,platform,title,url,policy_type,effective_date,updated_at,fetched_at,content_hash`

- `doc_id`: `<platform>-<mã ổn định>`. Dùng `knowledge_id`/`questionId`/`article id` của trang nguồn nếu có (xem `doc_id()` ở `scripts/policies/common.py`). Không đổi `doc_id` sau khi đã dùng, vì `fee_rules.csv` và `chunk_id` trỏ vào nó.
- `url`: link trang người dùng mở được (trang help center). Không dùng link file đính kèm hay CDN (vd `aliyuncs.com`).
- `policy_type`: **một trong 5 giá trị**: `fee`, `voucher`, `ads`, `return_refund`, `settlement`.
- `effective_date`: ngày hiệu lực ghi trong bài ("có hiệu lực từ …"), `YYYY-MM-DD`, để trống nếu bài không ghi. `updated_at`: ngày cập nhật hiển thị trên trang, `YYYY-MM-DD`. `fetched_at`: ngày crawl.
- `content_hash`: sha256 của nội dung sạch. Không để trống.

### 3. `chunks.jsonl`: mỗi dòng đủ các khoá sau

| Khoá | Kiểu | Ghi chú |
|---|---|---|
| `chunk_id` | str | `<doc_id>#001`, `#002`… Ổn định giữa các lần chạy |
| `doc_id`, `platform`, `policy_type` | str | `policy_type` phải trùng manifest |
| `section_path` | list[str] | đường tiêu đề, vd `["Phí của Nhà Bán Hàng", "Phí cố định"]` |
| `text` | str | nội dung chunk. Bảng: lặp lại dòng tiêu đề cột ở mỗi chunk |
| `context_header` | str | `[<Sàn> · <Tiêu đề> · cập nhật YYYY-MM-DD]`, hoặc `hiệu lực YYYY-MM-DD` |
| `token_count` | int | số token ước lượng, nên ≤ 600 |
| `has_table`, `has_numbers` | bool | |
| `effective_date`, `updated_at` | str hoặc null | luôn có khoá, không có ngày thì `null` |
| `url`, `fetched_at`, `content_hash` | str | lấy từ manifest |
| `chunker_version` | str | vd `v2-structure-400` |

Chunk theo cấu trúc (tiêu đề, bảng, mục), không cắt giữa bảng hoặc giữa câu. Dùng `scripts/policies/chunk.py` có sẵn cho cả 3 sàn để chunk giống nhau.

### 4. `index.jsonl`: chỉ do `scripts/policies/embed.py` sinh ra

Mỗi dòng: `chunk_id, text_hash, content_hash, chunker_version, embed_model, dim, vector`.
Cả 3 sàn dùng **cùng một model**: `embed_model = "gemini-embedding-001"`, `dim = 768`, vector chuẩn hoá L2. Không tự embed bằng model khác (vector khác model không so sánh được). Cần `EMBED_API_KEY` trong `.env`. Không commit `.env`.

### 5. Yêu cầu phủ nội dung (mỗi sàn)

Mỗi `policy_type` phải có ≥ 1 tài liệu. Với `fee`, cố gắng có đủ: phí cố định/hoa hồng theo ngành, phí xử lý/giao dịch/thanh toán (**cả tên cũ**), phí vận chuyển/logistic, hoa hồng tiếp thị liên kết, thuế khấu trừ. Với `voucher`: voucher shop, voucher sàn, chương trình tự bật (Voucher Xtra, đồng tài trợ…). Với `settlement`: khi nào tiền về, vì sao bị trừ/chưa nhận, đối soát. Với `return_refund`: hoàn tiền, trả hàng, khiếu nại, ai chịu phí. Với `ads`: phí quảng cáo.

Bỏ tài liệu không liên quan 5 loại trên (vay vốn, sở hữu trí tuệ, điều khoản tính năng AI…) để retrieval không bị nhiễu. Liệt kê tài liệu đã bỏ và lý do trong mô tả PR.

### 6. Luật repo cần nhớ (từ `AGENTS.md`)

- Không commit `.env`, API key, `raw-*`. Số phí chỉ lấy từ code (`fee_engine.py`), không lấy từ chunk, nên chunk phải chính xác từng chữ so với nguồn, không tóm tắt lại, không bịa.
- Số không có nguồn ghi *(tự ước tính)*. Thiếu thông tin thì ghi thiếu, không bịa.

### 7. Cách tự kiểm tra: phải ĐẠT mới mở PR

```
python scripts/policies/validate.py --platform <tiktok|shopee|lazada>
```

Script kiểm: cột manifest, kiểu từng khoá chunk, `chunk_id` khớp `doc_id`, ngày đúng định dạng, đủ 5 `policy_type`, mỗi chunk có đúng một vector cùng model và dim, vector chuẩn hoá L2, không BOM.
