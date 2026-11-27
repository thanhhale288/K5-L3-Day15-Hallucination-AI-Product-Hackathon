Bạn là coding agent (Claude Code/Cursor/Codex) giúp Huy trong repo hackathon "Lãi đi đâu?". Trước khi làm, đọc `AGENTS.md`, `CONTEXT.md`, `TASK.md` (hỏi người dùng nếu chưa chắc họ là ai; chỉ sửa file thuộc phạm vi dưới đây).

**Bối cảnh:** sản phẩm là agent soi từng đơn hàng trên Shopee, TikTok Shop, Lazada. Agent cần một kho chính sách có embedding để giải thích và trích dẫn (`search_policy` → `chunk_id`, `url`, `effective_date`). Ba bạn mỗi người làm kho của một sàn, **cùng một schema**. Việc của Huy: kho **Shopee**.

**Lấy code nền:** pipeline dùng chung (`scripts/policies/{crawl,clean,chunk,embed,validate}.py`, `codebase/retrieval.py`, `codebase/policy_paths.py`) và tài liệu `docs/policy-schema.md` nằm trên nhánh `cp2-tiktokshop` (PR #1) và nhánh chứa schema. Nếu PR #1 đã merge vào `main` thì tạo nhánh từ `main`, chưa thì tạo từ `origin/cp2-tiktokshop`. Chạy `git fetch origin` trước. Không force-push, không sửa file của sàn khác.

## Hiện trạng kho Shopee (đã đọc nhánh `feat/shoppe`, commit `81d38a5`)

- Có 31 tài liệu, 438 chunk ở `data/shopee_policy/seller/` (`documents.jsonl`, `chunks.jsonl`, `embeddings_meta.json`) và code ở `rag/`. Code này **khác schema chung** nên cần chuyển, không dùng lại nguyên.
- Vector **không được commit** (chỉ có `embeddings_meta.json`). Metadata chỉ có `category` ("Thông Tin Chung / Chính sách Shopee"), **không có `policy_type`**, không có `platform`, `effective_date`, `updated_at`, `context_header`, `section_path` dạng list.
- Embed bằng OpenAI `text-embedding-3-small` 1536 chiều. Cả nhóm dùng Gemini 768 chiều, nên **phải embed lại**, không dùng lại được vector cũ.
- Bộ lọc "seller-only" đã bỏ 200 trong 231 bài (`filter_report.md`). Danh sách 31 bài giữ lại hầu như là điều khoản chung và chương trình khác. **Tôi không thấy bài nào có tiêu đề kiểu "Phí cố định", "Phí xử lý giao dịch", "Voucher Xtra", "Phí hoa hồng tiếp thị liên kết"**. Nhiều khả năng bài về phí bị lọc nhầm.
- Dữ liệu nhà bán hàng: Shopee đổi phí liên tục năm 2026 (24/04 "phí thanh toán" đổi tên thành "phí xử lý giao dịch"; 01/05 lên 6%; 08/05 giảm 1% phí cố định; 23/05 Voucher Xtra 5,5% trần 50.000đ/sản phẩm; chi tiết ở `CONTEXT.md`, mục *Thực trạng 2026*, đó là bài tổng hợp cần đối chiếu với trang gốc, không coi là nguồn).

## Việc cần làm (theo thứ tự)

1. **Rà `rag/filter_report.md`, `filter_decisions.jsonl`** và danh sách 235 bài gốc. Tìm bài thuộc 5 loại (`fee, voucher, ads, return_refund, settlement`) đã bị loại. Cần tìm tối thiểu: phí cố định theo ngành, phí xử lý giao dịch (và tên cũ "phí thanh toán"), Voucher Xtra, hoa hồng tiếp thị liên kết, phí vận chuyển/chính sách vận chuyển, hoàn tiền/trả hàng/đơn hoàn, thanh toán và đối soát cho người bán, phí quảng cáo. Nếu bài đó nằm ngoài 235 bài đã crawl, crawl thêm từ Seller Education Hub/help.shopee.vn (chỉ trang công khai). Liệt kê rõ bài nào thêm lại, bài nào không tìm được.
2. **Đổi tiêu chí lọc:** thay "seller-only" bằng "thuộc 1 trong 5 `policy_type` và liên quan đến tiền của người bán". Gán `policy_type` cho từng tài liệu (viết bảng gán trong `scripts/policies/urls_shopee.txt` theo định dạng `<policy_type> <url>` như `urls_tiktok.txt`). Bỏ tài liệu không thuộc 5 loại (vay Seasy/Quick Funds, sở hữu trí tuệ, tính năng AI, Shopee Live, Instant Mart, v.v.), trừ khi chúng nói rõ phí hay tiền của người bán.
3. **Chuyển về pipeline chung:** dùng `scripts/policies/crawl.py`, `clean.py`, `chunk.py` với `--platform shopee`. Nếu trang Shopee là SPA không crawl được bằng `crawl.py`, giữ bước lấy HTML riêng của bạn nhưng đầu ra phải là `data/shopee/policies/clean/<doc_id>.md` rồi chạy `chunk.py`. Nếu cần sửa script dùng chung thì báo Thái (người giữ `scripts/policies/`) trước. `doc_id` = `shopee-<article id>`.
4. **Ngày:** điền `updated_at` và `effective_date` từ trang gốc (nhiều bài Shopee ghi "có hiệu lực từ…"). Quan trọng với phí: agent tra luật theo ngày đặt đơn. Tên cũ và tên mới của phí phải cùng có mặt trong text chunk để tìm được cả hai tên.
5. **Embed lại:** `python scripts/policies/embed.py --platform shopee` (cần `EMBED_API_KEY` trong `.env`). Xóa các file cũ ở `data/shopee_policy/` và `rag/` khỏi PR hoặc ghi rõ lý do giữ.
6. **Kiểm:** `python scripts/policies/validate.py --platform shopee` phải ĐẠT. Rồi thử 10 câu hỏi thật về phí Shopee bằng `codebase/retrieval.search(query, platform="shopee")` (ví dụ "phí xử lý giao dịch Shopee là bao nhiêu từ tháng 5/2026", "Voucher Xtra trần bao nhiêu", "đơn hoàn có bị trừ phí không") và ghi chunk trả về đúng/sai vào mô tả PR.

## Đầu ra và tiêu chí xong

- PR vào `main` với: `data/shopee/policies/{manifest.csv, chunks.jsonl, index.jsonl, clean/}`, `scripts/policies/urls_shopee.txt`.
- `validate.py --platform shopee` ĐẠT, mỗi `policy_type` ≥ 1 tài liệu.
- Mô tả PR có 3 mục: (a) tài liệu thêm lại so với bản lọc cũ, (b) tài liệu bỏ và lý do, (c) **phần còn thiếu** (loại phí nào không tìm thấy nguồn công khai).
- Không commit `raw-shopee/`, `.env`.

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
