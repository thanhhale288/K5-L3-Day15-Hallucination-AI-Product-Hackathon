// "Tiền đi đâu": thác tiền từ số khách trả → từng khoản sàn trừ → tiền về → giá vốn → lãi thật.
// Số hiện trên màn đều lấy nguyên từ JSON của agent. Cộng dồn ở đây chỉ để đặt vị trí thanh (hình học),
// không hiện thành số. Ô đầu chỉ ghi số khi bridge có `base` (giá × SL − voucher shop) và khớp đúng điểm đầu.
import {motion} from 'motion/react';
import {Info} from 'lucide-react';
import {cn} from '@/lib/utils';
import type {AgentResult, Line} from '@/types';
import {LINE_TYPE, vnd} from '@/format';
import {Money, Pill} from './bits';
import {Tooltip, TooltipContent, TooltipTrigger} from './ui/tooltip';

type Row =
  | {kind: 'start'; label: string; amount: number | null; from: number; to: number}
  | {kind: 'line'; label: string; amount: number; from: number; to: number; line: Line; ghost: [number, number] | null}
  | {kind: 'payout' | 'cogs' | 'profit'; label: string; amount: number; from: number; to: number};

function buildRows(r: AgentResult, base: number | null): Row[] {
  if (r.payout === null) return [];
  const top = r.payout - r.lines.reduce((s, l) => s + l.amount, 0);
  const rows: Row[] = [{kind: 'start', label: 'Khách trả', amount: base === top ? base : null, from: 0, to: top}];
  let run = top;
  for (const l of r.lines) {
    const next = run + l.amount;
    const ghost: [number, number] | null =
      l.expected !== null && l.delta ? [Math.min(run, run + l.expected), Math.max(run, run + l.expected)] : null;
    rows.push({kind: 'line', label: l.name, amount: l.amount, from: Math.min(run, next), to: Math.max(run, next), line: l, ghost});
    run = next;
  }
  rows.push({kind: 'payout', label: 'Tiền về', amount: r.payout, from: 0, to: r.payout});
  if (r.cogs !== null && r.profit !== null) {
    rows.push({kind: 'cogs', label: 'Giá vốn', amount: -r.cogs, from: Math.min(r.profit, r.payout), to: Math.max(r.profit, r.payout)});
    rows.push({kind: 'profit', label: 'Lãi thật', amount: r.profit, from: Math.min(0, r.profit), to: Math.max(0, r.profit)});
  }
  return rows;
}

const BAR: Record<Row['kind'], string> = {
  start: 'bg-ink/15',
  line: '',
  payout: 'bg-ink',
  cogs: 'bg-fee/40',
  profit: 'bg-profit',
};

function LineTip({line}: {line: Line}) {
  const t = LINE_TYPE[line.type];
  return (
    <Tooltip>
      <TooltipTrigger className="text-muted-foreground/70 hover:text-foreground" aria-label={`Luật của ${line.name}`}>
        <Info className="size-4" />
      </TooltipTrigger>
      <TooltipContent className="max-w-72 text-left leading-relaxed">
        <p className="font-semibold">{t.label}</p>
        <p className="opacity-80">{t.tip}</p>
        {line.rule_id && <p className="mt-1 font-mono text-xs opacity-70">{line.rule_id}</p>}
        {line.source_url && (
          <a href={line.source_url} target="_blank" rel="noreferrer" className="mt-1 block underline underline-offset-2">
            {line.chunk_id ? `Nguồn · ${line.chunk_id}` : 'Nguồn biểu phí'}
          </a>
        )}
      </TooltipContent>
    </Tooltip>
  );
}

export function Waterfall({result, base}: {result: AgentResult; base: number | null}) {
  const rows = buildRows(result, base);
  if (!rows.length) return null;
  const lo = Math.min(...rows.map(r => r.from));
  const hi = Math.max(...rows.map(r => r.to));
  const x = (v: number) => `${((v - lo) / (hi - lo || 1)) * 100}%`;
  const w = (a: number, b: number) => `${(Math.abs(b - a) / (hi - lo || 1)) * 100}%`;

  return (
    <div className="flex flex-col gap-1" role="list" aria-label="Tiền đi đâu">
      {rows.map((row, i) => {
        const isLine = row.kind === 'line';
        const isOff = isLine && Boolean(row.line.delta);
        const isUnknown = isLine && row.line.type === 'khong_khop';
        const isBad = isOff || isUnknown;
        const isTotal = row.kind === 'payout' || row.kind === 'profit';
        const growsFromRight = row.kind === 'line' || row.kind === 'cogs';
        return (
          <motion.div
            role="listitem"
            key={`${row.kind}-${row.label}-${i}`}
            initial={{opacity: 0, y: 6}}
            animate={isBad ? {opacity: 1, y: 0, backgroundColor: ['rgb(0 0 0 / 0)', 'var(--alert-soft)', 'var(--alert-soft)']} : {opacity: 1, y: 0}}
            transition={isBad ? {delay: i * 0.07, duration: 1.2, times: [0, 0.4, 1]} : {delay: i * 0.07, duration: 0.3}}
            className={cn(
              'group grid grid-cols-[minmax(0,8.5rem)_1fr_6rem] items-center gap-2 sm:grid-cols-[minmax(0,16rem)_1fr_8.5rem] sm:gap-3 rounded-lg px-2 py-2 hover:bg-muted/60',
              isTotal && 'mt-1 border-t border-dashed border-border pt-2.5',
            )}>
            <div className="flex min-w-0 flex-col items-start gap-1">
              <div className="flex max-w-full min-w-0 items-center gap-1.5">
                <span title={row.label} className={cn('truncate text-base', isTotal ? 'font-semibold' : 'text-foreground/85')}>{row.label}</span>
                {isLine && <LineTip line={row.line} />}
              </div>
              {isOff && <Pill className="bg-alert-soft text-alert">Lệch luật</Pill>}
              {isUnknown && <Pill className="bg-alert-soft text-alert">Không khớp luật</Pill>}
            </div>
            <div className="relative h-6">
              {row.kind === 'line' && row.ghost && (
                <div
                  className="absolute inset-y-0 rounded-[5px] border border-dashed border-ink/50"
                  style={{left: x(row.ghost[0]), width: w(row.ghost[0], row.ghost[1])}}
                  title={`Đúng luật: ${vnd(row.line.expected)}`}
                />
              )}
              <motion.div
                className={cn(
                  'absolute inset-y-0.5 rounded-[5px]',
                  isLine ? LINE_TYPE[row.line.type].bar : BAR[row.kind],
                  isOff && 'bg-alert',
                  isTotal && 'inset-y-0',
                )}
                style={{left: x(row.from), width: w(row.from, row.to), minWidth: 6, originX: growsFromRight ? 1 : 0}}
                initial={{scaleX: 0}}
                animate={{scaleX: 1}}
                transition={{delay: i * 0.07 + 0.1, type: 'spring', stiffness: 140, damping: 20}}
              />
            </div>
            <div className={cn('text-right text-base tabular', isTotal ? 'font-bold' : 'text-foreground/80', row.kind === 'profit' && 'text-profit')}>
              {row.amount === null ? '' : isTotal ? <Money value={row.amount} from={0} /> : vnd(row.amount)}
              {isOff && row.kind === 'line' && (
                <div className="text-xs font-medium text-alert">đúng luật {vnd(row.line.expected)}</div>
              )}
            </div>
          </motion.div>
        );
      })}
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 px-2 text-sm text-muted-foreground">
        <Legend className="bg-fee" label="Bắt buộc" />
        <Legend className="bg-switch" label="Công tắc" />
        <Legend className="bg-alert" label="Lệch / không khớp luật" />
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-[3px] border border-dashed border-ink/50" /> Số đúng luật
        </span>
      </div>
    </div>
  );
}

function Legend({className, label}: {className: string; label: string}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn('h-2.5 w-4 rounded-[3px]', className)} />
      {label}
    </span>
  );
}
