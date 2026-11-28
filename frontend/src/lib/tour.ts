// Hướng dẫn từng bước (driver.js). Bước nào không có phần tử trên màn (vd chưa có kết quả) thì bỏ qua.
import {driver, type DriveStep} from 'driver.js';

export type TourView = 'soi-don' | 'tong-quan';
const SEEN_KEY = 'lai-tour-seen';

const STEPS: Record<TourView, DriveStep[]> = {
  'soi-don': [
    {popover: {title: 'Lãi đi đâu?', description: 'Agent soi từng đơn Shopee, TikTok Shop, Lazada: sàn trừ những khoản gì, khoản nào bạn tắt được, lãi thật còn bao nhiêu.'}},
    {element: '[data-tour="composer"]', popover: {title: 'Dán đơn vào đây', description: 'Chép phần chi tiết thanh toán trên trang đơn hàng của sàn rồi dán vào. Mỗi lần 1–5 đơn, có thể khác sàn.'}},
    {element: '[data-tour="samples"]', popover: {title: 'Chưa có đơn? Thử đơn mẫu', description: 'Bấm một đơn mẫu để xem agent làm việc.'}},
    {element: '[data-tour="steps"]', popover: {title: 'Agent làm gì', description: 'Agent lập kế hoạch, tra luật phí theo ngày đặt đơn và gọi công cụ tính. Mọi con số do code tính, không do AI đoán.'}},
    {element: '[data-tour="hero"]', popover: {title: 'Lãi thật mỗi đơn', description: 'Tiền sàn trả về trừ giá vốn. Nhãn bên phải cho biết: đã xong, cần bạn trả lời, hay nên hỏi sàn.'}},
    {element: '[data-tour="waterfall"]', popover: {title: 'Tiền đi đâu', description: 'Mỗi thanh là một khoản sàn trừ. Xám là phí bắt buộc, cam là công tắc bạn tắt được, đỏ là khoản sai luật. Rê chuột vào ⓘ để xem luật và nguồn.'}},
    {element: '[data-tour="switches"]', popover: {title: 'Thử đổi công tắc', description: 'Kéo tỉ lệ rồi bấm Thử: code tính lại lãi mỗi đơn và số đơn được phép giảm mà vẫn có lợi.'}},
    {element: '[data-tour="draft"]', popover: {title: 'Câu hỏi gửi sàn', description: 'Khoản sai luật thì agent soạn sẵn câu hỏi. Agent không tự gửi: bạn chép, đọc lại rồi tự gửi.'}},
    {element: '[data-tour="actions"]', popover: {title: 'Bạn quyết định', description: 'Bấm Sẽ làm hoặc Bỏ qua cho từng đề xuất. Agent không tự bấm gì trên sàn.'}},
    {element: '[data-tour="split"]', popover: {title: 'Đổi độ rộng', description: 'Kéo thanh này để nới khung chat hoặc khung kết quả.'}},
    {element: '[data-tour="history"]', popover: {title: 'Các đơn đã soi', description: 'Chuyển qua lại giữa các kết quả trong phiên này.'}},
    {element: '[data-tour="nav-tong-quan"]', popover: {title: 'Tổng quan tháng', description: 'Tải file export của cả tháng để xem lãi từng sàn, khoản phí nào lớn nhất và đơn nào cần soi.'}},
  ],
  'tong-quan': [
    {element: '[data-tour="data-source"]', popover: {title: 'Dữ liệu tháng', description: 'Tải file export đơn hàng của từng sàn và file giá vốn. Chưa có file thì xem bộ demo tháng 11.'}},
    {element: '[data-tour="tiles"]', popover: {title: 'Lãi từng sàn', description: 'Lãi trước quảng cáo và tỉ lệ phí sàn trên doanh thu của mỗi sàn.'}},
    {element: '[data-tour="split-chart"]', popover: {title: 'Doanh thu chia đi đâu', description: 'Mỗi đồng doanh thu: bao nhiêu cho sàn, bao nhiêu là giá vốn, bao nhiêu còn lại là lãi.'}},
    {element: '[data-tour="fees"]', popover: {title: 'Khoản phí nào lớn nhất', description: 'Tổng từng khoản phí trong tháng, theo sàn. Phí khác không khớp luật được tô đỏ.'}},
    {element: '[data-tour="sku"]', popover: {title: 'SKU lãi nhất và thấp nhất', description: 'Doanh thu cao chưa chắc lãi: đây là lãi mỗi đơn sau phí và giá vốn.'}},
    {element: '[data-tour="ads"]', popover: {title: 'Quảng cáo có lời không', description: 'ROAS dưới vạch hoà vốn thì phần doanh số quảng cáo mang về đang lỗ.'}},
    {element: '[data-tour="review"]', popover: {title: 'Đơn cần soi', description: 'Đơn bị trừ sai luật hoặc có phí lạ. Dán đơn đó vào màn Soi đơn để agent soạn câu hỏi gửi sàn.'}},
  ],
};

export function startTour(view: TourView) {
  const steps = STEPS[view].filter(s => !s.element || document.querySelector(s.element as string));
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
    onDestroyed: () => localStorage.setItem(SEEN_KEY, '1'),
  });
  d.drive();
}

export const hasSeenTour = () => localStorage.getItem(SEEN_KEY) === '1';
