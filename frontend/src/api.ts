// Gọi agent. Có VITE_API_URL (hoặc VITE_USE_API=1 khi dùng proxy dev) → POST /soi-don của Thái (TH-7).
// Không có → chế độ mẫu: trả file JSON trong frontend/samples/ khớp mã đơn trong chữ dán.
import type {SoiResult} from './types';
import index from '../samples/index.json';

export interface SampleEntry {
  file: string;
  label: string;
  order_ids: string[];
  decision: string;
  paste: string | null;
}

export const SAMPLES = index as SampleEntry[];

const files = import.meta.glob<SoiResult>('../samples/*.json', {eager: true, import: 'default'});

export function loadSample(file: string): SoiResult {
  return files[`../samples/${file}`];
}

const API_URL: string | undefined = import.meta.env.VITE_API_URL;
export const USE_API = Boolean(API_URL) || import.meta.env.VITE_USE_API === '1';

export interface SoiRequest {
  text: string;
  cogs: number | null;
  session_state_id: string | null;
}

export class SampleMissError extends Error {}

export async function soiDon(req: SoiRequest): Promise<SoiResult> {
  if (USE_API) {
    const res = await fetch(`${API_URL ?? ''}/soi-don`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`API trả lỗi ${res.status}: ${await res.text()}`);
    return (await res.json()) as SoiResult;
  }
  const hit = SAMPLES.find(s =>
    s.order_ids.length ? s.order_ids.every(id => req.text.includes(id)) : s.paste === req.text.trim(),
  );
  if (!hit) throw new SampleMissError('Chế độ mẫu chỉ nhận các đơn mẫu.');
  await new Promise(r => setTimeout(r, 400));
  return loadSample(hit.file);
}
