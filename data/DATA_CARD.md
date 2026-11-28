# Data card — dữ liệu bản chạy thử dùng

> Chấm ở rubric R4. Mỗi dataset một mục. Cập nhật 28/11/2026 (TH-10, Thái). Số trong file này đếm lại trực tiếp từ file trong repo.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp, chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Tóm tắt

| # | Dataset | File chính | Nhãn | Agent / app đọc? | Dùng cho |
|---|---|---|---|---|---|
| 1 | Review app người bán | `evidence/reviews/` | thật | Không | Bằng chứng pain, bối cảnh câu thử |
| 2 | Bảng phí 3 sàn | `data/fee_rules.csv` (91 luật) | tự dựng, có đối chiếu | Có (qua công cụ) | **Tính** phí |
| 3 | Kho chính sách 3 sàn | `data/policies/chunks.jsonl` + `index.jsonl` (1.089 chunk) | thật | Có (qua `search_policy`) | **Giải thích, trích dẫn** |
| 4 | Đơn giả cấp đơn 3 sàn | `data/synthetic/` (300 đơn, 288 đoạn dán) | `synthetic` | Có, **trừ đáp án** | Đầu vào agent, nguồn câu thử |
| 5 | Bộ câu thử | `eval/benchmark.csv` (30 câu) | `synthetic` + bối cảnh review | Chỉ `eval/` | Chấm lượt 1, lượt 2 |
| 6 | File export mẫu (demo import) | `data/demo_import/` (537 đơn) | `synthetic` | Có, **trừ đáp án** | Màn import tháng (ngoài lát cắt) |
| 7 | Ngữ cảnh shop theo tháng | `data/synthetic/stores.csv`, `store_months.csv` | `synthetic` | Không chấm | Hướng cũ, chỉ làm ngữ cảnh |

Tất cả trừ Dataset 1 và 3 là nhóm tự dựng. **Data `synthetic` không phải bằng chứng pain.**

## Dataset 1 · Review app người bán (bằng chứng pain)

| | |
|---|---|
| Dùng để làm gì | đào bằng chứng pain (`evidence/summary.md`), 10/30 câu thử viết theo bối cảnh review |
| Từ đâu | Google Play, 300 review mới nhất × 3 app: `com.shopee.shopeeseller` (11/01 → 26/11/2026), `com.tiktokshop.seller` (10/07 → 26/11/2026), `com.sc.lazada` (07/06/2024 → 22/11/2026). Lang `vi`, country `vn`, sort NEWEST, mọi mức sao |
| Xử lý những bước gì | bỏ tên / ảnh người viết, băm `reviewId`, che SĐT / email (`evidence/crawl_reviews.py`, Lazada `evidence/crawl_lazada.py`) → lọc từ khoá chọn 116 review có nhãn tiền → AI gán nhãn mẫu A (116) + mẫu B (100 ngẫu nhiên trong 784 còn lại, seed 42) → `evidence/reviews/labels-ai.csv` → đếm bằng `evidence/count_reviews.py` |
| Số dòng / số đoạn | N = 900 (300 mỗi app, `evidence/reviews/manifest.csv`). Pain về tiền đã xác nhận 88/900 (9,8%) |
| Phiên bản / ngày lấy | 27/11/2026 · `google-play-scraper==1.2.7` |
| Nhãn | thật. Nhãn chủ đề do AI gán, **Hà đọc lại 30 dòng, khớp 28/30** (2 dòng lệch không đổi số pain) |
| Giới hạn | nghiêng về người đang bực; không phân biệt shop nhỏ / lớn; nhiều review là lỗi app (ngoài phạm vi); mẫu Lazada trải từ 06/2024 nên cũ hơn 2 app kia; lọc từ khoá bỏ sót ước tính 3/100. Toàn văn thô không commit (`raw-*`) |

## Dataset 2 · Bảng phí 3 sàn (`data/fee_rules.csv`, hợp đồng H2)

| | |
|---|---|
| Dùng để làm gì | nguồn **duy nhất** để TÍNH phí: `data/fee_engine.py` → công cụ `lookup_fee_rule`, `expected_amount`, `unit_profit`, `switch_what_if`, `compare_platforms`; và mọi script sinh data / đáp án. `fee_engine.load_rules()` đọc file này, thiếu thì rơi về `data/synthetic/fee_rules_v0.csv` |
| Từ đâu | khung v0 nhóm tự dựng (`python data/fee_engine.py --write-v0`): mốc ngày đổi phí 2026 lấy từ báo chí / blog (`CONTEXT.md` › Thực trạng 2026), tỉ lệ theo ngành tự ước tính. Bản 1.1 dựng bằng `python data/build_fee_rules.py`: giữ nguyên số của v0, thêm `ten_cu`, `chunk_id` và nâng `da_doi_chieu` khi trang chính sách khớp |
| Xử lý những bước gì | 3 sàn × 6 ngành (`dien_tu, me_be, my_pham, nha_cua, thoi_trang, thuc_pham`, hoặc `*`) × loại shop × khoảng hiệu lực (11 mốc, 01/07/2025 → 03/08/2026). Gắn `chunk_id` chỉ khi đoạn chính sách **không mâu thuẫn** với số của luật. Kiểm: `python data/fee_engine.py --check` → đơn mẫu H4 ra 123.520 / 28.520; `tests/test_tools.py` kiểm mọi `chunk_id` có thật và đúng sàn |
| Số dòng / số đoạn | 91 luật: Shopee 36 · TikTok Shop 32 · Lazada 23. 82 `bat_buoc`, 9 `cong_tac`. 56 luật có `chunk_id` (Shopee 29, TikTok 27, Lazada 0); 90 có `nguon_url` |
| Phiên bản / ngày lấy | bản 1.1 · 28/11/2026 (commit `cb7e8fc`), đối chiếu với kho chính sách ở Dataset 3 |
| Nhãn | cột `da_doi_chieu`: **`chinh_thuc` 4** (khớp cả số và ngày trên trang chính sách: Shopee phí xử lý giao dịch 6% shop thường từ 01/05 và Mall từ 08/05, phí hạ tầng; TikTok phí xử lý đơn hàng) · **`bao_chi` 7** (theo báo chí, chưa khớp trang chính sách) · **`gia_dinh` 80** *(tự ước tính)* |
| Ai kiểm | Hà soát nghiệp vụ (HA-7): tên phí, loại bắt buộc / công tắc, ngày hiệu lực. Chỗ trang chính thức khác v0 ghi ở `data/fee_rules_review.md`, **chưa sửa số** |
| Giới hạn | 88% luật là giả định nên kết luận "sàn nào đắt hơn" chỉ đúng trong data giả. Lazada chưa luật nào gắn `chunk_id` dù kho đã có 423 chunk Lazada. Biểu phí cố định theo ngành của Shopee khác v0 (xem `fee_rules_review.md`). Chưa có phí ship shop chịu, phí quảng cáo theo đơn, đóng gói. Sửa số thì phải sinh lại đơn giả + đáp án + benchmark cùng lúc, không sửa riêng một bên |

## Dataset 3 · Kho chính sách 3 sàn (`data/policies/`, hợp đồng H1)

| | |
|---|---|
| Dùng để làm gì | nguồn để GIẢI THÍCH và TRÍCH DẪN cho `search_policy` (`codebase/tools.py` → `codebase/retrieval.py`). **Không lấy con số tính toán từ chunk** |
| Từ đâu | trang công khai, không đăng nhập: Shopee `banhang.shopee.vn/edu` (291 chunk) + `help.shopee.vn` (83); TikTok Shop Học viện người bán `seller-vn.tiktok.com/university` (292); Lazada Seller Center `sellercenter.lazada.vn/helpcenter` (423). Danh sách URL: `scripts/policies/urls_{shopee,tiktok,lazada}.txt` |
| Xử lý những bước gì | crawl Playwright ~1 trang / 3 s (`crawl.py`, `crawl_hub.py`) → HTML → Markdown, bảng thành mỗi hàng một dòng "Cột: giá trị" (`clean.py`) → cắt theo heading ~400 token, trần 800 (`chunk.py`, `v2-structure-400`) → kiểm schema (`validate.py`) → embed `bge-m3` chạy local, 1.024 chiều (`embed.py`) → gộp 3 kho, bỏ trùng theo nội dung (`merge.py`) → điền `effective_date` **chỉ khi chính đoạn văn nêu ngày** (`fill_effective_date.py`, căn cứ ở `effective_date_evidence.csv`). Truy xuất: BM25 + cosine gộp RRF, lọc cứng `platform`, bỏ đoạn có `effective_date` sau ngày đặt đơn |
| Số dòng / số đoạn | 181 tài liệu → 1.089 chunk, 1.089 vector. Shopee 65 tài liệu / 374 chunk · TikTok 48 / 292 · Lazada 68 / 423. Theo loại: `fee` 546 · `voucher` 151 · `return_refund` 165 · `ads` 114 · `settlement` 113. 240 chunk có bảng. Token median 334–369 |
| Phiên bản / ngày lấy | crawl 27–28/11/2026 · `chunker_version = v2-structure-400` · `embed_model = bge-m3` (commit `741c0ab`, `cb7e8fc`). Kho riêng từng sàn ở `data/{shopee,tiktok_shop,lazada}/policies/`, kho gộp là bản agent đọc |
| Nhãn | thật (văn bản chính sách công khai, không có dữ liệu cá nhân) |
| Ai kiểm | Minh (MI-4, MI-6): 10 câu hỏi phí, top-5 đúng 10/10 (Shopee 4/4, TikTok 3/3, Lazada 3/3); kiểm âm tính lọc ngày PASS |
| Giới hạn | 652/1.089 chunk (60%) để `effective_date` trống vì nguồn không nêu ngày (TikTok 259/292), nên lọc ngày chỉ có tác dụng trên phần còn lại. Một số chunk Lazada vượt trần 800 token (max 1.752). Tệp đính kèm (PDF, XLSX biểu phí) chưa trích, chunk chỉ ghi tên tệp. Chính sách đổi theo thời gian, cần crawl lại trước khi dùng thật. HTML gốc không commit (`data/*/policies/raw-*`). `data/shopee_policy/` là kho Shopee cũ khác schema, **không dùng** |

## Dataset 4 · Đơn giả cấp đơn 3 sàn (`data/synthetic/`)

| | |
|---|---|
| Dùng để làm gì | đầu vào cho bản chạy thử, frontend và nguồn sinh bộ câu thử (đáp án do code sinh) |
| Từ đâu | sinh có seed: `python data/make_orders.py --seed 42`, tính phí bằng `data/fee_engine.py` (Dataset 2) |
| Xử lý những bước gì | 8 shop · 41 sản phẩm · 109 listing → 300 đơn (Shopee 120 · TikTok Shop 100 · Lazada 80), 1.173 dòng phí, đặt 03–11/2026. Cài lỗi ~10%: vượt trần 8 · sai tỉ lệ theo ngày 8 · dòng lạ 7 · thiếu dòng 4 · tổng không khớp 4. 26 đơn thiếu giá vốn, 11 đơn dùng tên phí cũ, 15 nhóm so chéo sàn. Mỗi sàn một kiểu chữ "chi tiết thanh toán"; có đoạn không ghi tên sàn |
| Số dòng / số đoạn | 300 đơn · 288 đoạn dán (`pastes.jsonl`): `don` 261 · `nhieu_don` 15 · `chen_lenh` 6 · `tu_choi` 6. Quyết định mong đợi: act 220 · ask 33 · escalate 23 · refuse 12 |
| Phiên bản / ngày lấy | seed 42 · 27/11/2026 |
| Nhãn | `synthetic`. File agent đọc: `shops, products, listings, orders, order_lines, pastes`. **Đáp án, agent và code chạy thật không đọc:** `order_answers.csv, line_answers.csv, paste_answers.csv` |
| Giới hạn | định dạng chữ dán là nhóm tự dựng, chưa đối chiếu app thật; mỗi đơn 1 sản phẩm; chưa có phí vận chuyển người bán chịu; tỉ lệ lỗi 10% là nhóm chọn *(tự ước tính)*, không phải tỉ lệ lỗi thật của sàn |

## Dataset 5 · Bộ câu thử (`eval/benchmark.csv`, hợp đồng H5, Minh giữ)

| | |
|---|---|
| Dùng để làm gì | chấm lượt 1 / lượt 2 theo `eval/metric_spec.yaml` và chuẩn đạt `spec.md` §7 |
| Từ đâu | `python eval/build_benchmark.py`: sinh đơn seed 42 từ `data/fee_rules.csv` vào thư mục tạm, đáp án do code tính, không sửa `data/synthetic/` |
| Số dòng / số đoạn | 30 câu: `thuong` 20 · `kho` 6 · `tu_choi` 4. 20 câu nguồn `sinh_seed`, 10 câu theo bối cảnh review công khai (Dataset 1) |
| Nhãn | đáp án `synthetic` (code sinh); bối cảnh 10 câu lấy từ review thật |
| Giới hạn | đáp án đúng theo bảng phí giả định, không phải theo sàn thật; 30 câu nhỏ nên mỗi câu = 3,3 điểm % |

## Dataset 6 · File export mẫu để demo import (`data/demo_import/`)

| | |
|---|---|
| Dùng để làm gì | demo bổ sung, ngoài lát cắt: "chủ shop tải file export tháng → bảng lãi theo sàn và SKU" (`data/import_export.py`, API `POST /import`) |
| Từ đâu | sinh có seed: `python data/make_demo_import.py` (cần `openpyxl`) |
| Xử lý những bước gì | "Shop Demo" tháng 11/2026: Shopee 262 · TikTok Shop 185 · Lazada 90 đơn; 3 chiến dịch quảng cáo; file giá vốn `gia_von_mau.xlsx`; 6 câu chuyện cài sẵn (xem `data/demo_import/README.md`) |
| Số dòng / số đoạn | 537 đơn |
| Phiên bản / ngày lấy | seed 42 · 27/11/2026 |
| Nhãn | `synthetic`. Đáp án `_dap_an_2026-11.json`, agent không đọc |
| Giới hạn | tên cột **mô phỏng**, chưa đối chiếu file export thật. Kết quả import ghi vào `data/imported/` (đã `.gitignore`, không commit vì khi dùng file thật đó là dữ liệu thật của shop) |

## Dataset 7 · Ngữ cảnh shop theo tháng (`data/synthetic/stores.csv`, `store_months.csv`)

| | |
|---|---|
| Dùng để làm gì | hướng cũ (chẩn đoán cuối tháng, bỏ lúc 18:50 T6). Chỉ giữ làm ngữ cảnh, **không dùng để chấm** |
| Từ đâu | sinh có seed: `python data/generate_synthetic.py --dirty` (seed 42). `07_Ecommerce_Seller_Store.xlsx` là data luyện tập giả lập nhóm tự tìm, chỉ tham khảo, không làm đầu vào |
| Số dòng / số đoạn | 150 shop × 12 tháng = 1.800 dòng (bản `_dirty` có cài lỗi định dạng, nhãn ở `labels.csv`) |
| Nhãn | `synthetic` |
| Giới hạn | bảng phí mốc 2025, không đọc `fee_rules.csv`; cấp tháng, không có đơn |

## Người kiểm tay

| Dataset | Ai | Đã kiểm gì |
|---|---|---|
| 1 | Hà | 30 dòng nhãn AI (chọn theo 4 nhóm, có seed), khớp 28/30 |
| 2 | Hà | soát nghiệp vụ bản 1 (HA-7): tên phí, loại, ngày hiệu lực; chỗ lệch ghi ở `data/fee_rules_review.md` |
| 3 | Minh | 10 câu hỏi phí, top-5 đúng 10/10; kiểm âm tính lọc ngày |
| 4 | Thái | đơn mẫu H4 (`fee_engine.py --check`); chưa đọc tay từng đoạn dán |
| 5 | Minh | `python run.py check` sạch; chấm tay lượt 1 theo `pass_criterion` và trace |

## Sinh lại toàn bộ

```bash
python data/fee_engine.py --write-v0      # bảng phí v0
python data/build_fee_rules.py            # data/fee_rules.csv (bản 1.1)
python data/fee_engine.py --check         # phải ra 123.520 / 28.520
python data/make_orders.py --seed 42      # đơn giả + đáp án
python eval/build_benchmark.py            # bộ câu thử
python scripts/policies/merge.py          # kho chính sách gộp (từ kho từng sàn)
python data/make_demo_import.py           # file export mẫu
```
