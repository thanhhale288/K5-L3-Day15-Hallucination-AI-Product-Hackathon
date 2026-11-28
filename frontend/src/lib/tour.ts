// Hướng dẫn từng bước (driver.js). Bước nào không có phần tử trên màn (vd chưa có kết quả) thì bỏ qua.
import {driver, type DriveStep} from 'driver.js';

export type TourView = 'soi-don' | 'tong-quan';
/** 'ket-qua': hướng dẫn ngắn tự chạy lần đầu có kết quả soi đơn. */
export type TourKey = TourView | 'ket-qua';
const seenKey = (view: TourKey) => `lai-tour-seen-${view}`;

const RESULT_STEPS: DriveStep[] = [
    {element: '[data-tour="hero"]', popover: {title: 'Lãi thật mỗi đơn', description: 'Tiền sàn trả về trừ giá vốn. Nhãn bên phải cho biết: đã xong, cần bạn trả lời, hay nên hỏi sàn.'}},
    {element: '[data-tour="waterfall"]', popover: {title: 'Tiền đi đâu', description: 'Mỗi thanh là một khoản sàn trừ. Xám là phí bắt buộc, cam là công tắc bạn tắt được, đỏ là khoản sai luật. Rê chuột vào ⓘ để xem luật và nguồn.'}},
    {element: '[data-tour="switches"]', popover: {title: 'Thử đổi công tắc', description: 'Kéo tỉ lệ rồi bấm Thử: code tính lại lãi mỗi đơn và số đơn được phép giảm mà vẫn có lợi.'}},
    {element: '[data-tour="draft"]', popover: {title: 'Câu hỏi gửi sàn', description: 'Khoản sai luật thì agent soạn sẵn câu hỏi. Agent không tự gửi: bạn chép, đọc lại rồi tự gửi.'}},
    {element: '[data-tour="actions"]', popover: {title: 'Bạn quyết định', description: 'Bấm Sẽ làm hoặc Bỏ qua cho từng đề xuất. Agent không tự bấm gì trên sàn.'}},
    {element: '[data-tour="history"]', popover: {title: 'Các đơn đã soi', description: 'Chuyển qua lại giữa các kết quả trong phiên này.'}},
];

const STEPS: Record<TourKey, DriveStep[]> = {
  'ket-qua': RESULT_STEPS,
  'soi-don': [
    {popover: {title: 'Lãi đi đâu?', description: 'Agent soi từng đơn Shopee, TikTok Shop, Lazada: sàn trừ những khoản gì, khoản nào bạn tắt được, lãi thật còn bao nhiêu.'}},
    {element: '[data-tour="example"]', popover: {title: 'Nhắn gì cho agent?', description: 'Chép chi tiết thanh toán của đơn trong Seller Center và dán vào. Đây là một tin nhắn mẫu, mỗi phần có chú thích. Giá vốn bạn tự thêm, thiếu thì agent sẽ hỏi.'}},
    {element: '[data-tour="composer"]', popover: {title: 'Dán vào ô này', description: 'Bấm một gợi ý để điền sẵn tin nhắn mẫu hoặc khung trống, sửa số rồi Enter. Mỗi lần 1–5 đơn, khác sàn cũng được. Cũng hỏi được về phí, chính sách của 3 sàn: agent trả lời từ kho chính sách, có trích nguồn, và nhớ các lượt trước để hiểu câu hỏi nối tiếp.'}},
    {element: '[data-tour="samples"]', popover: {title: 'Chưa có đơn? Thử đơn mẫu', description: 'Bấm một đơn mẫu để xem agent làm việc.'}},
    {element: '[data-tour="steps"]', popover: {title: 'Agent làm gì', description: 'Agent lập kế hoạch, tra luật phí theo ngày đặt đơn và gọi công cụ tính. Mọi con số do code tính, không do AI đoán.'}},
    ...RESULT_STEPS.filter(x => x.element !== '[data-tour="history"]'),
    {element: '[data-tour="split"]', popover: {title: 'Đổi độ rộng', description: 'Kéo thanh này để nới khung chat hoặc khung kết quả.'}},
    {element: '[data-tour="history"]', popover: {title: 'Các đơn đã soi', description: 'Chuyển qua lại giữa các kết quả trong phiên này.'}},
    {element: '[data-tour="nav-tong-quan"]', popover: {title: 'Tổng quan tháng', description: 'Tải file export của cả tháng để xem lãi từng sàn, khoản phí nào lớn nhất và đơn nào cần soi.'}},
  ],
  'tong-quan': [
    {element: '[data-tour="data-source"]', popover: {title: 'Tải dữ liệu tháng', description: 'Chọn file export đơn hàng (.xlsx) của từng sàn và file giá vốn, rồi bấm Phân tích.'}},
    {element: '[data-tour="sample-files"]', popover: {title: 'Chưa có file? Dùng bộ mẫu', description: 'Tải về để xem định dạng, hoặc bấm Phân tích bộ file mẫu để thử ngay.'}},
    {element: '[data-tour="tiles"]', popover: {title: 'Lãi từng sàn', description: 'Lãi trước quảng cáo và tỉ lệ phí sàn trên doanh thu của mỗi sàn.'}},
    {element: '[data-tour="split-chart"]', popover: {title: 'Doanh thu chia đi đâu', description: 'Mỗi đồng doanh thu: bao nhiêu cho sàn, bao nhiêu là giá vốn, bao nhiêu còn lại là lãi.'}},
    {element: '[data-tour="fees"]', popover: {title: 'Khoản phí nào lớn nhất', description: 'Tổng từng khoản phí trong tháng, theo sàn. Phí khác không khớp luật được tô đỏ.'}},
    {element: '[data-tour="sku"]', popover: {title: 'SKU lãi nhất và thấp nhất', description: 'Doanh thu cao chưa chắc lãi: đây là lãi mỗi đơn sau phí và giá vốn.'}},
    {element: '[data-tour="ads"]', popover: {title: 'Quảng cáo có lời không', description: 'ROAS dưới vạch hoà vốn thì phần doanh số quảng cáo mang về đang lỗ.'}},
    {element: '[data-tour="review"]', popover: {title: 'Đơn cần soi', description: 'Đơn bị trừ sai luật hoặc có phí lạ. Dán đơn đó vào màn Soi đơn để agent soạn câu hỏi gửi sàn.'}},
    {element: '[data-tour="nav-soi-don"]', popover: {title: 'Soi từng đơn với agent', description: 'Sang đây để dán chi tiết thanh toán của một đơn. Agent chỉ ra từng khoản bị trừ, công tắc ăn lãi và soạn câu hỏi gửi sàn.'}},
  ],
};

export function startTour(view: TourKey) {
  // Chỉ lấy phần tử đang hiện: màn không dùng vẫn nằm trong DOM (ẩn) để giữ trạng thái.
  const isShown = (sel: string) => [...document.querySelectorAll(sel)].some(el => el.getClientRects().length > 0);
  const steps = STEPS[view].filter(s => !s.element || isShown(s.element as string)).map(s =>
    s.element ? {...s, element: () => [...document.querySelectorAll(s.element as string)].find(el => el.getClientRects().length > 0) as Element} : s,
  );
  const d = driver({
    steps,
    showProgress: true,
    progressText: '{{current}} / {{total}}',
    nextBtnText: 'Tiếp',
    prevBtnText: 'Lùi',
    doneBtnText: 'Xong',
    popoverClass: 'lai-tour',
    stagePadding: 6,
    stageRadius: 14,
    overlayOpacity: 0.55,
    onDestroyed: () => localStorage.setItem(seenKey(view), '1'),
  });
  d.drive();
}

/** Mỗi màn có hướng dẫn riêng; lần đầu mở màn nào thì chạy hướng dẫn của màn đó. */
export const hasSeenTour = (view: TourKey) => localStorage.getItem(seenKey(view)) === '1';
