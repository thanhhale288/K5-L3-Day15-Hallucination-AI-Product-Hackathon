"""Công cụ của bài toán — NHÓM VIẾT. Điền ở guide bước 2.2 (thiết kế) và 3.2 (code).

Mỗi công cụ là một hàm Python có @tool. Docstring ghi đúng 4 ý như sơ đồ ở spec.md §4:
    tên · input · output · có tác động ra ngoài không (gửi tin, sửa dữ liệu, chấm điểm…)
Khung tự ghi mỗi lần gọi công cụ vào trace (tên, input, output rút gọn, thời gian, lỗi).

Số công cụ, kiểu công cụ do thiết kế của nhóm quyết định — có bài chỉ cần một công cụ tra cứu.
Công cụ có tác động ra ngoài: KHÔNG tự làm. Trả về bản nháp chờ người duyệt (guide bước 2.2, "chỗ người duyệt").
Dữ liệu công cụ đọc (bài mẫu, thông báo mẫu, lịch…): để trong data/ và mô tả ở data/DATA_CARD.md.
"""
from tracing import tool, TOOLS  # noqa: F401  (TOOLS: danh sách công cụ đã đăng ký, dùng khi viết vòng lặp agent)


@tool
def search_example(query: str) -> list:
    """(ví dụ — thay bằng công cụ của nhóm) Tra dữ liệu mẫu theo câu hỏi.
    Input: câu hỏi (str). Output: danh sách đoạn {"code", "text"}. Không tác động ra ngoài."""
    return [{"code": "VD-1", "text": "(ví dụ) đoạn dữ liệu giả — thay bằng dữ liệu thật của bài toán"}]


@tool
def search_policy(query: str, platform: str = "tiktok", policy_type: str = "", k: int = 4) -> list:
    """search_policy · tra chính sách chính thức của sàn (RAG trên data/<thư mục sàn>/policies/, xem codebase/policy_paths.py).
    Input: câu hỏi (str), sàn ("tiktok"), loại chính sách ("fee" | "voucher" | "ads" | "return_refund" |
    "settlement" | "" = mọi loại), k = số đoạn tối đa.
    Output: [{"chunk_id", "text", "url", "effective_date", "fetched_at", "score"}]; [] khi không có đoạn nào
    đủ gần → luồng phải trả lời "không tìm thấy trong chính sách đã lưu", không tự đoán số.
    Không tác động ra ngoài (chỉ đọc file + gọi API embedding cho câu hỏi)."""
    from retrieval import search
    return search(query, platform=platform, policy_type=policy_type, k=k)
