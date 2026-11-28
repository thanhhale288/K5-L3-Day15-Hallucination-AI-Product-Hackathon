// Agent phía giao diện, nói giao thức AG-UI (https://docs.ag-ui.com).
//  - Có bridge (VITE_USE_API=1 hoặc VITE_API_URL): HttpAgent gọi POST /agent của frontend/agui/server.py,
//    bridge bọc agent thật của Huy (codebase/agent.py).
//  - Không có: SampleAgent phát đúng các sự kiện đó từ file JSON mẫu (frontend/samples/), để demo không cần backend.
import {AbstractAgent, HttpAgent} from '@ag-ui/client';
import {EventType, type BaseEvent, type RunAgentInput} from '@ag-ui/core';
import {Observable} from 'rxjs';
import type {AgentResult, SoiResult} from '../types';
import {isPolicy, isSession} from '../types';
import {SAMPLES, loadSample, type SampleEntry} from '../api';

export interface SwitchInfo {
  order_id: string | null;
  switch: string;
  amount: number;
  current_rate: number | null;
  base: number | null;
  cap_vnd: number | null;
  can_change_rate: boolean;
}

export interface WhatIf {
  order_id: string;
  switch: string;
  new_rate: number;
  old_amount: number;
  new_amount: number;
  gain_per_order: number;
  profit_after: number | null;
  max_order_drop_pct: number | null;
}

export type Choice = 'se_lam' | 'bo_qua';

/** Trạng thái dùng chung giữa agent và giao diện (AG-UI state). */
export interface LaiState {
  result?: SoiResult | null;
  session_state_id?: string | null;
  trace_id?: string | null;
  /** MODEL_PROVIDER của agent (bridge điền). "fake" = AI giả, chỉ đúng với đơn DEMO-0412. */
  model?: string;
  switch_info?: SwitchInfo[];
  what_if?: WhatIf[];
  /** Chủ shop chọn gì với từng đề xuất: khoá = `${order_id}::${text}`. Chỉ giao diện ghi. */
  decisions?: Record<string, Choice>;
  /** Nháp gửi sàn đã được chủ shop tự gửi chưa: khoá = order_id. */
  draft_sent?: Record<string, boolean>;
  /** Số lượt agent đang nhớ trong cuộc trò chuyện này (bridge giữ theo threadId). */
  memory_turns?: number;
}

export type Command =
  | {type: 'soi'}
  | {type: 'what_if'; order_id: string; switch: string; new_rate: number};

const API_URL: string | undefined = import.meta.env.VITE_API_URL;
export const USE_BRIDGE = Boolean(API_URL) || import.meta.env.VITE_USE_API === '1';

const TOOL_LABEL: Record<string, string> = {
  check_lines_sum: 'Kiểm tổng các dòng',
  lookup_fee_rule: 'Tra luật phí',
  search_policy: 'Tìm đoạn chính sách',
  expected_amount: 'Tính số đúng luật',
  unit_profit: 'Tính lãi thật',
  switch_what_if: 'Thử đổi công tắc',
  breakeven_roas: 'ROAS hoà vốn',
  compare_platforms: 'So sàn',
  ask_user: 'Hỏi lại chủ shop',
  draft_platform_question: 'Soạn nháp gửi sàn',
};
export const toolLabel = (name: string) => TOOL_LABEL[name] ?? name;

/** Chữ ngắn mô tả đối số của một lần gọi công cụ (hiện cạnh tên công cụ). */
export function toolTarget(name: string, args: string): string | undefined {
  try {
    const a = JSON.parse(args) as Record<string, unknown>;
    if (name === 'lookup_fee_rule') return `${a.fee_name} · ${a.platform}`;
    if (name === 'expected_amount') return String(a.rule_id ?? '');
    if (name === 'switch_what_if') return String(a.switch ?? '');
    if (name === 'search_policy') return String(a.query ?? '');
    if (name === 'draft_platform_question') return `${a.order_id} · ${a.line}`;
    if (name === 'compare_platforms') return `${(a.orders as unknown[] | undefined)?.length ?? 0} đơn`;
    return undefined;
  } catch {
    return undefined;
  }
}

function lastUserText(input: RunAgentInput): string {
  for (const m of [...input.messages].reverse()) {
    if (m.role === 'user') return typeof m.content === 'string' ? m.content : '';
  }
  return '';
}

function findSample(text: string): SampleEntry | undefined {
  const t = text.trim();
  return SAMPLES.find(s => (s.order_ids.length ? s.order_ids.every(id => t.includes(id)) : s.paste?.trim() === t));
}

const uid = (p: string) => `${p}-${Math.random().toString(36).slice(2, 10)}`;

/** Phát lại một kết quả mẫu thành chuỗi sự kiện AG-UI giống bridge (không gọi agent). */
export class SampleAgent extends AbstractAgent {
  run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable<BaseEvent>(sub => {
      const events: BaseEvent[] = [];
      const push = (e: Record<string, unknown>) => events.push(e as unknown as BaseEvent);
      const text = (content: string) => {
        const messageId = uid('msg');
        push({type: EventType.TEXT_MESSAGE_START, messageId, role: 'assistant'});
        for (let i = 0; i < content.length; i += 24) {
          push({type: EventType.TEXT_MESSAGE_CONTENT, messageId, delta: content.slice(i, i + 24)});
        }
        push({type: EventType.TEXT_MESSAGE_END, messageId});
      };
      const tool = (name: string, args: unknown, result: unknown) => {
        const toolCallId = uid('tool');
        push({type: EventType.TOOL_CALL_START, toolCallId, toolCallName: name});
        push({type: EventType.TOOL_CALL_ARGS, toolCallId, delta: JSON.stringify(args)});
        push({type: EventType.TOOL_CALL_END, toolCallId});
        push({type: EventType.TOOL_CALL_RESULT, messageId: uid('msg'), toolCallId, role: 'tool', content: JSON.stringify(result)});
      };

      push({type: EventType.RUN_STARTED, threadId: input.threadId, runId: input.runId});
      const cmd = (input.forwardedProps as {command?: Command} | undefined)?.command;
      if (cmd?.type === 'what_if') {
        text('Chế độ mẫu không chạy được công cụ tính. Bật bridge (python frontend/agui/server.py) để thử đổi công tắc.');
      } else {
        const sample = findSample(lastUserText(input));
        if (!sample) {
          text('Chế độ mẫu chỉ nhận các đơn mẫu. Chọn một gợi ý bên dưới, hoặc bật bridge để soi đơn bất kỳ.');
        } else {
          const result = loadSample(sample.file);
          const orders: AgentResult[] = isSession(result) ? result.orders : isPolicy(result) ? [] : [result];
          for (const o of orders) {
            for (const ln of o.lines) {
              tool('lookup_fee_rule', {fee_name: ln.name, platform: o.platform, order_date: o.order_date},
                ln.rule_id ? {rule_id: ln.rule_id, loai: ln.type} : null);
            }
            if (o.profit !== null) tool('unit_profit', {order_id: o.order_id}, {payout: o.payout, profit: o.profit});
            if (o.draft_to_platform) tool('draft_platform_question', {order_id: o.order_id, line: o.lines.find(l => l.type === 'khong_khop' || l.delta)?.name}, {sent: false});
            if (o.question) tool('ask_user', {question: o.question}, {stop: true});
          }
          if (isSession(result) && result.platform_comparison) {
            tool('compare_platforms', {orders: result.orders.map(o => o.order_id)}, result.platform_comparison);
          }
          const state: LaiState = {
            ...(input.state as LaiState),
            result,
            session_state_id: isSession(result) ? result.session_state_id : null,
            trace_id: result.trace_id,
            switch_info: sample.switch_info,
            what_if: [],
          };
          push({type: EventType.STATE_SNAPSHOT, snapshot: state});
          text(sample.summary);
        }
      }
      push({type: EventType.RUN_FINISHED, threadId: input.threadId, runId: input.runId});

      let i = 0;
      const timer = setInterval(() => {
        if (i >= events.length) {
          clearInterval(timer);
          sub.complete();
          return;
        }
        sub.next(events[i++]);
      }, 35);
      return () => clearInterval(timer);
    });
  }
}

export function createAgent(): AbstractAgent {
  return USE_BRIDGE ? new HttpAgent({url: `${API_URL ?? ''}/agent`}) : new SampleAgent();
}
