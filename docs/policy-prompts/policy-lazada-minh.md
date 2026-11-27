Bạn là coding agent (Claude Code/Cursor/Codex) giúp Minh trong repo hackathon "Lãi đi đâu?". Trước khi làm, đọc `AGENTS.md`, `CONTEXT.md`, `TASK.md` (hỏi người dùng nếu chưa chắc họ là ai; chỉ sửa file thuộc phạm vi dưới đây).

**Bối cảnh:** sản phẩm là agent soi từng đơn hàng trên Shopee, TikTok Shop, Lazada. Agent cần một kho chính sách có embedding để giải thích và trích dẫn (`search_policy` → `chunk_id`, `url`, `effective_date`). Ba bạn mỗi người làm kho của một sàn, **cùng một schema**. Việc của Minh: kho **Lazada**.

**Lấy code nền:** pipeline dùng chung (`scripts/policies/{crawl,clean,chunk,embed,validate}.py`, `codebase/retrieval.py`, `codebase/policy_paths.py`) và tài liệu `docs/policy-schema.md` nằm trên nhánh `cp2-tiktokshop` (PR #1) và nhánh chứa schema. Nếu PR #1 đã merge vào `main` thì tạo nhánh từ `main`, chưa thì tạo từ `origin/cp2-tiktokshop`. Chạy `git fetch origin` trước. Không force-push, không sửa file của sàn khác.

## Hiện trạng kho Lazada (đã đọc nhánh `minh/lazada-policy-chunks`, commit `a4c2acf`)

- `manifest.csv` có 4 dòng: phí cố định LazMall, hoàn tiền (chỉ hoàn tiền), lý do chưa nhận thanh toán, điều khoản dịch vụ nhà bán hàng (hiệu lực 29/09/2026). File **có BOM** ở đầu và **thiếu cột `updated_at`**, `content_hash` trống ở cả 4 dòng.
- Chunk nằm ở `chunk_lazada.json` (một mảng JSON, 130 chunk), còn `chunks.jsonl` **rỗng 0 byte**. Không có `index.jsonl` (chưa embed). Code nạp kho chỉ đọc `chunks.jsonl` + `index.jsonl`, nên hiện tại search Lazada trả rỗng.
- 130 chunk thì 126 là bảng phí cố định LazMall, 2 chunk bảng phí ngành sách (doc `lazada-phi-co-dinh-lazmall-sach-2026-10` **không có trong manifest**), 1 chunk hoàn tiền, 1 chunk thanh toán. **"Điều khoản dịch vụ nhà bán hàng" có trong manifest nhưng 0 chunk.**
- Thiếu hẳn: voucher, ads (quảng cáo/Sponsored Solutions), phí thanh toán/xử lý giao dịch, phí vận chuyển, hoa hồng tiếp thị liên kết, Freeship/chương trình tự bật, đơn hoàn/phí hoàn.
- `url` của bảng phí đang là link file đính kèm trên `aliyuncs.com`. Phải là link trang help center để chủ shop mở được.
- Lazada Seller Center là SPA và có PDF, nên `crawl.py` mặc định có thể không dùng được. Giữ `evidence/crawl_lazada.py` cho bước lấy nội dung nếu cần, nhưng đầu ra phải là `clean/<doc_id>.md` rồi dùng `chunk.py` chung.

## Việc cần làm (theo thứ tự)

1. **Lập danh sách tài liệu cần có** (`scripts/policies/urls_lazada.txt`, định dạng `<policy_type> <url>` như `urls_tiktok.txt`) phủ đủ 5 loại: ít nhất phí cố định/hoa hồng (LazMall **và shop thường**, nếu khác nhau), phí xử lý thanh toán, phí vận chuyển/ship, voucher shop + voucher sàn/đồng tài trợ + Freeship, quảng cáo, hoàn tiền/trả hàng/đơn hoàn, thanh toán và đối soát. Chỉ dùng trang công khai. Tài liệu nào không tìm được thì ghi vào mục "còn thiếu" của PR, không bịa.
2. **Sửa manifest:** UTF-8 không BOM, đúng 9 cột, thêm `updated_at`, điền `content_hash`. Thêm dòng cho bảng phí ngành sách, hoặc gộp nó vào doc phí cố định, nhưng `doc_id` trong chunk và manifest phải khớp. Điền `effective_date` từ nội dung bài (bảng phí có "từ 04/06/2026" và "từ 04/10/2026": đây là **hai mốc hiệu lực khác nhau của cùng một bảng**, giữ cả hai trong text để tra theo ngày đặt đơn).
3. **Chunk lại bằng `scripts/policies/chunk.py`** (chunker chung, ra `chunks.jsonl`), không dùng `chunk_lazada.json` nữa. Bảng phí lặp lại dòng tiêu đề cột ở mỗi chunk (bản hiện tại làm đúng điều này, giữ lại). Chunk điều khoản dịch vụ nhà bán hàng 29/09/2026. Xóa `chunk_lazada.json` khỏi PR.
4. **Embed:** `python scripts/policies/embed.py --platform lazada` (cần `EMBED_API_KEY` trong `.env`).
5. **Kiểm:** `python scripts/policies/validate.py --platform lazada` phải ĐẠT. Rồi thử 10 câu hỏi thật bằng `codebase/retrieval.search(query, platform="lazada")` (ví dụ "phí cố định ngành điện tử LazMall", "khi nào tiền về tài khoản", "lý do chưa nhận được thanh toán", "hoàn tiền không trả hàng thì ai chịu phí") và ghi chunk trả về đúng/sai vào mô tả PR.
6. Việc phụ: bạn đang giữ `eval/` và `search_policy`. Sau khi cả 3 kho xong, chạy MI-4 (thử 10 câu hỏi phí, mỗi sàn ≥ 3) trên kho thật.

## Đầu ra và tiêu chí xong

- PR vào `main` với: `data/lazada/policies/{manifest.csv, chunks.jsonl, index.jsonl, clean/}`, `scripts/policies/urls_lazada.txt`.
- `validate.py --platform lazada` ĐẠT, mỗi `policy_type` ≥ 1 tài liệu, tài liệu nào có trong manifest đều có chunk.
- Mô tả PR có mục **phần còn thiếu**.
- Không commit `raw-lazada/`, `.env`.

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
