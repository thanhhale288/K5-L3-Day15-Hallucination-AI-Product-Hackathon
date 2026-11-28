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

export const PLATFORM: Record<Platform, {label: string; dot: string; chip: string}> = {
  shopee: {label: 'Shopee', dot: 'bg-shopee', chip: 'bg-shopee/10 text-shopee'},
  tiktok: {label: 'TikTok Shop', dot: 'bg-tiktok', chip: 'bg-tiktok/10 text-tiktok'},
  lazada: {label: 'Lazada', dot: 'bg-lazada', chip: 'bg-lazada/10 text-lazada'},
};

export const LINE_TYPE: Record<LineType, {label: string; bar: string; chip: string; tip: string}> = {
  bat_buoc: {label: 'Bắt buộc', bar: 'bg-fee', chip: 'bg-muted text-muted-foreground', tip: 'Sàn luôn thu, shop không tắt được.'},
  cong_tac: {
    label: 'Công tắc',
    bar: 'bg-switch',
    chip: 'bg-switch-soft text-[oklch(0.5_0.12_60)]',
    tip: 'Chương trình shop tự bật (Voucher Xtra, tiếp thị liên kết…). Tắt hoặc chỉnh được.',
  },
  khong_khop: {
    label: 'Không khớp luật',
    bar: 'bg-alert hatch',
    chip: 'bg-alert-soft text-alert',
    tip: 'Không tìm thấy khoản này trong biểu phí của sàn tại ngày đặt đơn.',
  },
};

export const DECISION: Record<Decision, {label: string; chip: string; hint: string}> = {
  act: {label: 'Đã soi xong', chip: 'bg-profit-soft text-profit', hint: 'Mọi dòng khớp luật. Xem lãi thật và việc nên làm.'},
  ask: {label: 'Cần bạn trả lời', chip: 'bg-switch-soft text-[oklch(0.5_0.12_60)]', hint: 'Thiếu dữ liệu để tính tiếp.'},
  escalate: {label: 'Nên hỏi sàn', chip: 'bg-alert-soft text-alert', hint: 'Có dòng lệch luật hoặc không khớp luật nào.'},
  refuse: {label: 'Không hỗ trợ', chip: 'bg-muted text-muted-foreground', hint: 'Yêu cầu nằm ngoài phạm vi.'},
};
