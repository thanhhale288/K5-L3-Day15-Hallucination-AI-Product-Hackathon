// Hợp đồng H4 — bản TypeScript của codebase/schema.py (Huy giữ). Frontend chỉ đọc, không tự tính số.

export type Platform = 'shopee' | 'tiktok' | 'lazada';
export type Decision = 'act' | 'ask' | 'escalate' | 'refuse';
export type LineType = 'bat_buoc' | 'cong_tac' | 'khong_khop';

export interface Line {
  name: string;
  amount: number;
  type: LineType;
  rule_id: string | null;
  expected: number | null;
  delta: number | null;
  chunk_id: string | null;
  source_url: string | null;
}

export interface Switch {
  name: string;
  amount: number;
  share_of_profit: number | null;
}

export interface Action {
  text: string;
  gain_per_order: number | null;
}

export interface AgentResult {
  decision: Decision;
  platform: Platform | null;
  order_id: string | null;
  order_date: string | null;
  lines: Line[];
  payout: number | null;
  cogs: number | null;
  profit: number | null;
  switches: Switch[];
  actions: Action[];
  question: string | null;
  draft_to_platform: string | null;
  refusal_reason: string | null;
  trace_id: string | null;
}

export type ComparisonRow = {
  platform: Platform;
  profit: number | null;
  top_switch: string | null;
  order_id?: string;
  payout?: number;
  profit_per_unit?: number;
};

export interface SessionResult {
  decision: Decision;
  orders: AgentResult[];
  platform_comparison: {
    product: string;
    rows: ComparisonRow[];
    best_platform: Platform;
  } | null;
  session_state_id: string | null;
  trace_id: string | null;
}

export type SoiResult = AgentResult | SessionResult;

export function isSession(r: SoiResult): r is SessionResult {
  return 'orders' in r;
}
