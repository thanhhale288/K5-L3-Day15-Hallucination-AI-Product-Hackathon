// Đơn mẫu (frontend/samples/, sinh bằng make_samples.py): dùng cho gợi ý trong chat và cho SampleAgent.
import type {SoiResult} from './types';
import type {SwitchInfo} from './agent/laiAgent';
import index from '../samples/index.json';

export interface SampleEntry {
  file: string;
  label: string;
  order_ids: string[];
  decision: string;
  paste: string | null;
  /** Tóm tắt bằng chữ, sinh bằng frontend/agui/summary.py (giống câu bridge trả). */
  summary: string;
  switch_info: SwitchInfo[];
}

export const SAMPLES = index as unknown as SampleEntry[];

const files = import.meta.glob<SoiResult>('../samples/*.json', {eager: true, import: 'default'});

export function loadSample(file: string): SoiResult {
  return files[`../samples/${file}`];
}
