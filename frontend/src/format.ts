// Chỉ định dạng số để hiển thị. Không cộng, trừ, chia: mọi con số đến từ JSON của agent.
import type {Decision, LineType, Platform} from './types';

const VND = new Intl.NumberFormat('vi-VN');

/** 123520 → "123.520đ"; -10395 → "−10.395đ". */
export function vnd(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  const s = `${VND.format(Math.abs(n))}đ`;
  return n < 0 ? `−${s}` : s;
}

/** 0.663 → "66%"; 5.13 → "513%". */
export function pct(x: number | null | undefined): string {
  if (x === null || x === undefined) return '—';
  return `${Math.round(x * 100)}%`;
}

/** "2026-11-12" → "12/11/2026". */
export function ngay(d: string | null): string {
  if (!d) return '—';
  const [y, m, day] = d.split('-');
  return `${day}/${m}/${y}`;
}

export const PLATFORM: Record<Platform, {label: string; color: 'orange' | 'gray' | 'blue'}> = {
  shopee: {label: 'Shopee', color: 'orange'},
  tiktok: {label: 'TikTok Shop', color: 'gray'},
  lazada: {label: 'Lazada', color: 'blue'},
};

export const LINE_TYPE: Record<LineType, {label: string; color: 'gray' | 'orange' | 'red'; tip: string}> = {
  bat_buoc: {label: 'Bắt buộc', color: 'gray', tip: 'Sàn luôn thu, shop không tắt được.'},
  cong_tac: {
    label: 'Công tắc',
    color: 'orange',
    tip: 'Chương trình shop tự bật (Voucher Xtra, tiếp thị liên kết…). Tắt hoặc chỉnh được.',
  },
  khong_khop: {
    label: 'Không khớp luật',
    color: 'red',
    tip: 'Không tìm thấy khoản này trong biểu phí của sàn tại ngày đặt đơn.',
  },
};

export const DECISION: Record<
  Decision,
  {label: string; variant: 'success' | 'warning' | 'error' | 'neutral'; hint: string}
> = {
  act: {label: 'Đã soi xong', variant: 'success', hint: 'Mọi dòng khớp luật. Xem lãi thật và việc nên làm.'},
  ask: {label: 'Cần bạn trả lời', variant: 'warning', hint: 'Thiếu dữ liệu để tính tiếp.'},
  escalate: {label: 'Nên hỏi sàn', variant: 'error', hint: 'Có dòng lệch luật hoặc không khớp luật nào.'},
  refuse: {label: 'Không hỗ trợ', variant: 'neutral', hint: 'Yêu cầu nằm ngoài phạm vi.'},
};
