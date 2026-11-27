# Schema chung kho chính sách (3 sàn dùng một schema)

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
