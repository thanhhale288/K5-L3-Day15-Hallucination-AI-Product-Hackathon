# rag/: dữ liệu chính sách Shopee Việt Nam cho RAG

Bốn bước, chỉ dùng thư viện chuẩn của Python (không cần `pip install`):

```
python rag/pipeline.py crawl     # help.shopee.vn → data/shopee_policy/raw/*.json + clean/*.md + documents.jsonl
python rag/pipeline.py chunk     # → data/shopee_policy/chunks.jsonl
python rag/pipeline.py filter    # → data/shopee_policy/seller/ (Seller-only)
python rag/pipeline.py embed     # → data/shopee_policy/seller/embeddings.jsonl + embeddings_meta.json
```

## 1. Crawl

- Nguồn duy nhất: `help.shopee.vn` (Trung tâm hỗ trợ chính thức; robots.txt cho phép toàn bộ).
- Danh sách bài: `sitemap.xml`, cộng thêm các bài `help.shopee.vn/.../article/<id>` được bài chính sách trỏ tới (nhiều văn bản gốc như Quy chế hoạt động, Chính sách vận chuyển không có trong sitemap).
- Nội dung: API công khai mà chính trang web gọi, `/api/inhouse/hc/mobile/v1/article?id=<id>` (title, HTML, danh mục).
- `raw/<id>.json`: phản hồi API nguyên bản (để kiểm tra). `clean/<id>.md`: văn bản đã bỏ thẻ HTML, ảnh, style; giữ heading, bullet, bảng, nguyên văn.
- Chỉ giữ bài liên quan chính sách: so khớp tên danh mục hoặc tiêu đề (không dấu) với `POLICY_PATTERNS` trong `pipeline.py`.
- Chạy lại thì dùng lại `raw/` đã có; `--refresh` để tải lại.

## 2. Chunk

- Tách theo heading (gồm cả đoạn in đậm mà Shopee dùng làm tiêu đề mục), giữ nguyên một đoạn / một mục danh sách / một hàng bảng; chỉ cắt theo câu khi một đoạn dài hơn `--max`.
- Mặc định: `--max 600 --overlap 80 --min 150` token. Overlap chỉ áp dụng trong cùng một mục; chunk tiếp nối nhắc lại heading của mục.
- Đếm token bằng `tiktoken` nếu đã cài, không thì ước lượng `len/2.6` ký tự.
- Mỗi dòng: `chunk_id, content, title, source_url, section` (+ `category`, `n_tokens`).

## 2b. Filter: dataset Seller-only

```
python rag/pipeline.py filter    # → data/shopee_policy/seller/{chunks.jsonl, documents.jsonl, filter_report.md, filter_decisions.jsonl}
```

Không crawl lại, không chunk lại: chỉ chọn chunk từ `chunks.jsonl`, giữ nguyên văn nội dung và metadata. Luật lọc nằm ở đầu `rag/seller_filter.py`:
bỏ trùng (ID cũ chuyển hướng), bỏ bản lưu trữ "(phiên bản trước / phiên bản ngày …)", chấm tín hiệu Người bán / Người mua trên nội dung từng chunk,
bài viết cho Người bán giữ cả bài, bài chung chỉ giữ mục cho Người bán, còn lại loại. Các quyết định tay có lý do nằm trong `OVERRIDES`.
Xem từng quyết định ở `seller/filter_report.md`.

Dataset Seller-only đã chốt nằm ở `data/shopee_policy/seller/`. Dữ liệu trung gian (`raw/`, `clean/`, `documents.jsonl`, `chunks.jsonl`)
đã được xoá sau khi chốt; muốn lọc lại thì chạy lại `crawl` → `chunk` → `filter`. `embed` chỉ cần `seller/chunks.jsonl`.

## 3. Embed

Mặc định embed dataset Seller-only (`--dataset all` để embed toàn bộ policy). Repo chưa có vector database, nên embedding lưu thành file JSONL (mỗi dòng = metadata chunk + `embedding`). Cấu hình trong `.env` (tên biến có tiền tố `RAG_`, tách khỏi `EMBED_*` của `codebase/retrieval.py`), không có key nào trong code:

```
RAG_EMBED_PROVIDER=openrouter                      # gọi https://openrouter.ai/api/v1/embeddings
RAG_EMBED_MODEL=openai/text-embedding-3-small
RAG_EMBED_DIM=1536
RAG_EMBED_API_KEY=<OPENROUTER_API_KEY>
```

Bắt buộc đủ 4 biến, không có giá trị mặc định hay fallback (không mượn `MODEL_PROVIDER` / `API_KEY`); thiếu hoặc sai là dừng và báo lỗi.
Mỗi batch được kiểm: đủ số vector, đúng `RAG_EMBED_DIM`, không có null/NaN; sai thì dừng và không ghi output.
`embeddings_meta.json` ghi provider, model, dimension, số chunk và số token API của lần chạy.

Văn bản đem đi embed là `title + section + content`; `content` lưu nguyên văn. Chạy lại chỉ gọi API cho chunk mới hoặc đã đổi.
