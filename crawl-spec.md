# Crawl spec — review app người bán + chính sách 3 sàn

> Chuẩn **viết trước khi crawl**. Ai crawl cũng theo file này để số đếm chạy lại ra giống nhau.
> Phục vụ: (A) đào bằng chứng pain → `evidence/data-mining.md` (canvas dòng 4) · (B) kho chính sách cho RAG của bản chạy thử → `codebase/tools.py`.
> Luật repo áp dụng (CONTEXT.md): không chép tên người viết review, trích nguyên văn tối đa 2 câu/review, ghi link + ngày xem, số không có nguồn ghi *(tự ước tính)*.

---

## A. Review Google Play — `google-play-scraper` (Python)

### A1. Nguồn

| Sàn | Tên app | `app_id` (package) | Trạng thái |
|---|---|---|---|
| Shopee | Shopee Seller Center | `com.shopee.shopeeseller` | cần mở `play.google.com/store/apps/details?id=…&hl=vi&gl=VN` kiểm |
| TikTok Shop | TikTok Shop Seller Center | `com.tiktokshop.seller` | cần kiểm như trên |
| Lazada | Lazada Seller Center | `com.sc.lazada` | cần kiểm như trên (mới thấy 1 nguồn) |

Thư viện: `google-play-scraper==1.2.7` (ghi vào `requirements.txt`). Không cần API key.

### A2. Tham số crawl (chốt)

```python
from google_play_scraper import reviews, Sort, app

result, token = reviews(
    app_id,
    lang="vi",          # mặc định thư viện là 'en' → PHẢI đặt 'vi'
    country="vn",       # mặc định 'us' → PHẢI đặt 'vn'
    sort=Sort.NEWEST,   # mẫu = "N review mới nhất", không dùng MOST_RELEVANT (Google xếp, không lặp lại được)
    count=300,          # canvas: 300 review mới nhất × 3 app
    filter_score_with=None,  # lấy mọi số sao, lọc sau → mẫu số không bị lệch
)
```

- Google Play trả tối đa 200 review/trang; thư viện tự phân trang. Không dùng `reviews_all` (hàng nghìn request).
- Mỗi app crawl **một lần trong cùng một ngày**, ghi `crawled_at`. Muốn thêm thì nối bằng `continuation_token`, không crawl lại từ đầu (tránh trùng / lệch mẫu).
- Gọi thêm `app(app_id, lang="vi", country="vn")` lấy `score`, `ratings`, `reviews`, `installs`, `version`, `updated` → dùng làm bối cảnh (tổng số review = quy mô), không phải mẫu đếm.

### A3. Trường thô thư viện trả về → giữ / bỏ

| Trường thư viện | Giữ? | Ghi chú |
|---|---|---|
| `reviewId` | giữ dạng **hash** | `sha256(reviewId)[:12]` → `review_key`. Dùng để khử trùng + trích dẫn "mã đã ẩn danh" |
| `userName`, `userImage` | **bỏ ngay khi crawl** | luật: không chép tên người viết |
| `content` | giữ | văn bản gốc, không sửa |
| `score` | giữ | 1–5 |
| `thumbsUpCount` | giữ | mức "nhiều người đồng ý" |
| `reviewCreatedVersion`, `appVersion` | giữ | có thể `None` |
| `at` | giữ | đổi sang ISO 8601, múi `+07:00` |
| `replyContent`, `repliedAt` | giữ | sàn có trả lời không, sau bao lâu |

### A4. Schema chuẩn (1 dòng = 1 review) — `data/reviews/reviews_clean.csv`

| Cột | Kiểu | Ví dụ | Nguồn |
|---|---|---|---|
| `review_key` | str | `a3f9c01b22de` | hash `reviewId` |
| `platform` | enum | `shopee` · `tiktok` · `lazada` | |
| `app_id` | str | `com.shopee.shopeeseller` | |
| `score` | int 1–5 | `1` | |
| `content` | str | … | |
| `content_len` | int | `142` | tính |
| `thumbs_up` | int | `12` | |
| `app_version` | str/null | `3.62.64` | |
| `review_at` | ISO datetime | `2026-11-20T09:14:00+07:00` | |
| `has_reply` | bool | `true` | |
| `reply_lag_h` | float/null | `26.5` | `repliedAt − at` |
| `lang`, `country`, `sort` | str | `vi`, `vn`, `newest` | tham số crawl |
| `crawled_at` | ISO datetime | | |
| `lib_version` | str | `1.2.7` | |

Nhãn (điền sau, tay hoặc AI + người kiểm) — file riêng `data/reviews/reviews_labels.csv`, nối bằng `review_key`:

| Cột | Giá trị |
|---|---|
| `is_seller_pain` | `1` / `0` (review không liên quan, spam, chỉ "app tốt" → 0) |
| `topic` (nhiều nhãn, `;`) | `phi_san` · `tien_ve_doi_soat` · `voucher_khuyen_mai` · `quang_cao` · `hoan_tra` · `van_chuyen` · `khoa_tai_khoan_vi_pham` · `loi_app` · `khac` |
| `mentions_profit` | `1` nếu nói rõ lỗ / lãi thấp / tiền về ít |
| `labeler` | `human:P_thai` · `ai:<model>+human_check` |
| `label_note` | lý do khi khó phân |

> Định nghĩa từng nhãn + 2 ví dụ / nhãn viết vào `evidence/data-mining.md` §1 **trước khi gán nhãn**. Nếu dùng AI gán nhãn: người kiểm tay ≥30 dòng, ghi tỉ lệ khớp.

### A5. Làm sạch (theo thứ tự, script `evidence/clean_reviews.py`)

1. Bỏ `userName`, `userImage`; hash `reviewId`.
2. Khử trùng theo `review_key`; rồi theo (`app_id`, `content` đã chuẩn hoá) để bắt spam copy-paste.
3. Chuẩn hoá Unicode **NFC** (tiếng Việt hay lẫn dựng sẵn / tổ hợp), gộp khoảng trắng. **Không** bỏ dấu, không sửa chính tả trong `content`.
4. Che PII lọt trong nội dung: SĐT (`0\d{9,10}` → `[SĐT]`), email, mã đơn dài → `[MÃ]`, link shop → `[LINK]`.
5. Đánh dấu (không xoá) review rỗng / `content_len < 10` → loại khỏi mẫu số, báo số đã loại.

### A6. Quy tắc đếm (cho `evidence/data-mining.md`)

- **Mẫu số:** số review sau bước 5, theo từng app và gộp. Báo `x/N (y%)`, kèm khoảng thời gian `min(review_at)`–`max(review_at)`.
- Báo riêng 2 mẫu số: tất cả review và review 1–2 sao.
- Trích nguyên văn: ≤2 câu, kèm `platform · review_key · ngày review · link trang app · ngày xem`.
- Giới hạn phải ghi: review trên Play nghiêng về người bực (selection bias), không phân biệt shop nhỏ / lớn, review có thể nói về app chứ không về phí.

### A7. Lưu gì vào repo

| File | Commit? |
|---|---|
| `data/reviews/raw-*.jsonl` (đầu ra thô) | **không** — thêm `data/reviews/raw-*` vào `.gitignore` |
| `reviews_clean.csv`, `reviews_labels.csv` (đã ẩn danh) | có |
| script crawl + clean + count | có |
| Mục dataset trong `data/DATA_CARD.md` | có (nguồn, ngày lấy, số dòng, lọc, giới hạn) |

---

## B. Chính sách 3 sàn — chuẩn chunking cho RAG

### B1. Nguồn và metadata cấp tài liệu

Chỉ lấy trang công khai, không đăng nhập (Trung tâm hỗ trợ / Học viện người bán / trang biểu phí của Shopee, TikTok Shop, Lazada bản VN). Chỉ lấy nhóm chính sách phục vụ lát cắt: **phí sàn (cố định, thanh toán, dịch vụ), voucher/khuyến mãi do người bán chịu, phí quảng cáo, hoàn/trả hàng và ai chịu phí, đối soát / thời gian tiền về**.

Mỗi tài liệu một dòng trong `data/policies/manifest.csv`:

| Cột | Ví dụ |
|---|---|
| `doc_id` | `shopee-phi-co-dinh` |
| `platform` | `shopee` |
| `title` | tiêu đề trang nguyên văn |
| `url` | link gốc |
| `policy_type` | `fee` · `voucher` · `ads` · `return_refund` · `settlement` |
| `effective_date` | ngày hiệu lực ghi trên trang, không có → `null` (đừng đoán) |
| `fetched_at` | ngày xem |
| `content_hash` | sha256 text đã làm sạch — đổi hash = chính sách đã đổi |

### B2. Làm sạch trước khi cắt

- HTML → Markdown, **giữ heading (H1–H4), list, bảng**. Bỏ menu, footer, banner, "bài viết liên quan", cookie.
- NFC Unicode. Giữ nguyên số, %, đơn vị (`đ`, `VNĐ`, `%/đơn`), ngày.
- Bảng biểu phí: chuyển mỗi hàng thành 1 dòng có đủ tên cột (`Ngành hàng: Thời trang | Phí cố định: 4% | Áp dụng từ: …`) để chunk nào cũng tự hiểu được.

### B3. Quy tắc cắt (chốt)

1. **Cắt theo cấu trúc trước**: mỗi section dưới heading là một đơn vị. Không cắt ngang câu, ngang list, ngang hàng bảng.
2. **Kích thước mục tiêu 300–500 token, trần 800**. Section dài hơn trần → tách theo đoạn / mục list, sau đó mới tách theo câu. Section ngắn < 100 token → gộp với section anh em cùng heading cha.
3. **Overlap: 0** khi đã cắt theo cấu trúc; chỉ khi buộc phải tách giữa một section dài thì cho chồng **1–2 câu** (~10–15%).
4. **Quy tắc + ngoại lệ đi chung**: đoạn "trừ trường hợp…", "lưu ý…", "không áp dụng với…" phải nằm cùng chunk với quy tắc nó sửa. Đây là chỗ RAG chính sách hay sai nhất.
5. **Một bảng phí = nguyên vẹn** nếu ≤ trần; lớn hơn thì tách theo nhóm hàng, lặp lại tiêu đề cột ở mỗi phần.
6. **Gắn ngữ cảnh vào đầu chunk** (contextual header, chỉ dùng khi embed + đưa cho model):
   `[Shopee · Phí người bán > Phí cố định > Ngành Thời trang · hiệu lực 2026-xx-xx]`

> Con số 300–500 / overlap 0 là điểm khởi đầu từ các nghiên cứu và mặc định nền tảng (xem nguồn), không phải chân lý. Kiểm bằng bộ câu thử: nếu câu hỏi phí trả lời sai do thiếu ngữ cảnh → tăng cỡ; do lấy nhầm chunk → giảm cỡ. Ghi thay đổi vào `spec.md` §10.

### B4. Schema chunk — `data/policies/chunks.jsonl` (1 dòng = 1 chunk)

```json
{
  "chunk_id": "shopee-phi-co-dinh#003",
  "doc_id": "shopee-phi-co-dinh",
  "platform": "shopee",
  "policy_type": "fee",
  "section_path": ["Phí người bán", "Phí cố định", "Ngành Thời trang"],
  "text": "…nội dung đã làm sạch…",
  "context_header": "[Shopee · Phí người bán > Phí cố định > Ngành Thời trang]",
  "token_count": 412,
  "has_table": true,
  "has_numbers": true,
  "effective_date": "2026-xx-xx",
  "url": "https://…#anchor",
  "fetched_at": "2026-11-27",
  "content_hash": "…",
  "chunker_version": "v1-structure-400"
}
```

- `chunk_id` ổn định: `doc_id#số thứ tự` — trace và câu trả lời phải dẫn được `chunk_id` + `url`.
- Đổi tham số cắt → tăng `chunker_version`, chạy lại toàn bộ, ghi vào data card.

### B5. Chặn rủi ro riêng của chính sách

- **Nguồn sự thật cho con số**: model chỉ được dẫn % / phí có trong chunk lấy về; phép tính do công cụ (`tools.py`) làm. Không có chunk nào chứa số → trả "không tìm thấy trong chính sách đã lưu" (lớp chỗ khó *nguồn sự thật*).
- **Chính sách cũ**: luôn đưa `effective_date` + `fetched_at` vào câu trả lời; khác sàn thì không trộn chunk (lọc metadata `platform` trước khi tìm).
- **Bản quyền / repo công khai**: commit `manifest.csv` + chunk đã làm sạch kèm link nguồn là đủ cho demo; không commit HTML gốc (`data/policies/raw-*` vào `.gitignore`).
- Chunk chính sách là **dữ liệu cho công cụ**, không phải bằng chứng pain.

---

## C. Việc cần chốt trước khi crawl

- [ ] Mở 3 link Play Store, xác nhận `app_id` + tên app hiển thị ở VN
- [ ] Viết định nghĩa nhãn `topic` + ví dụ vào `evidence/data-mining.md` §1
- [ ] Thêm `data/reviews/raw-*`, `data/policies/raw-*` vào `.gitignore`
- [ ] Liệt kê URL chính sách cụ thể của từng sàn vào `manifest.csv`
- [ ] Thêm `google-play-scraper==1.2.7` vào `requirements.txt`

## Nguồn tham khảo (xem 2026-11-27)

- google-play-scraper README (trường review, giới hạn 200/trang): https://github.com/JoMingyu/google-play-scraper · https://pypi.org/project/google-play-scraper/
- Package ID: https://appgoblin.info/apps/com.shopee.shopeeseller · https://grand-screen.com/apps/tiktok-shop-seller-center/ · https://www.nowsecure.com/marc-app/tiktok-shop-seller-center-android/ · https://apptopia.com/google-play/app/com.sc.lazada/about
- Chunk size / overlap: https://arxiv.org/pdf/2601.14123 · https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/ · https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025 · https://elib.dlr.de/221921/1/COINS_CAMERA_READY_IEEE_APPROVED.pdf
