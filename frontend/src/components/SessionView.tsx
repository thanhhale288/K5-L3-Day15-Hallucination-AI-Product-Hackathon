// SessionResult (dán nhiều đơn) → so sánh sàn (thanh lãi mỗi sản phẩm) + hoá đơn từng đơn.
import {useState} from 'react';
import {motion} from 'motion/react';
import {Trophy} from 'lucide-react';
import {cn} from '@/lib/utils';
import type {SessionResult} from '@/types';
import {PLATFORM} from '@/format';
import {Money, PlatformPill} from './bits';
import {InvoiceView, type InvoiceControls} from './InvoiceView';

function Comparison({pc}: {pc: NonNullable<SessionResult['platform_comparison']>}) {
  const value = (r: (typeof pc.rows)[number]) => r.profit_per_unit ?? r.profit ?? 0;
  const top = Math.max(1, ...pc.rows.map(value));
  return (
    <motion.section initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} className="rounded-2xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">Lãi mỗi sản phẩm · {pc.product}</h3>
        <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-profit">
          <Trophy className="size-4" /> Lãi nhất: {PLATFORM[pc.best_platform].label}
        </span>
      </div>
      <div className="mt-4 flex flex-col gap-3">
        {pc.rows.map((r, i) => {
          const isBest = r.platform === pc.best_platform;
          return (
            <div key={r.platform} className="grid grid-cols-[6.5rem_1fr_7rem] items-center gap-3">
              <PlatformPill platform={r.platform} />
              <div className="h-7 rounded-md bg-muted/70">
                <motion.div
                  className={cn('h-full rounded-md', isBest ? 'bg-profit' : 'bg-fee/50')}
                  initial={{width: 0}}
                  animate={{width: `${(Math.max(0, value(r)) / top) * 100}%`}}
                  transition={{delay: 0.15 + i * 0.12, type: 'spring', stiffness: 80, damping: 16}}
                />
              </div>
              <div className={cn('text-right text-base font-bold', isBest && 'text-profit')}>
                <Money value={r.profit_per_unit ?? r.profit} from={0} />
              </div>
              <div />
              <div className="-mt-2 text-sm text-muted-foreground">{r.top_switch ? `Ăn lãi nhiều nhất: ${r.top_switch}` : 'Không có công tắc'}</div>
            </div>
          );
        })}
      </div>
    </motion.section>
  );
}

export function SessionView({result, controls}: {result: SessionResult; controls?: InvoiceControls}) {
  const [tab, setTab] = useState(result.orders[0]?.order_id ?? '');
  const current = result.orders.find(o => o.order_id === tab) ?? result.orders[0];
  return (
    <div className="flex flex-col gap-4">
      {result.platform_comparison && <Comparison pc={result.platform_comparison} />}
      <div className="flex flex-wrap gap-1 rounded-xl bg-muted p-1" role="tablist" aria-label="Từng đơn">
        {result.orders.map(o => {
          const isActive = o.order_id === current?.order_id;
          return (
            <button
              key={o.order_id}
              role="tab"
              aria-selected={isActive}
              onClick={() => setTab(o.order_id ?? '')}
              className={cn('relative flex-1 rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors', isActive ? 'text-foreground' : 'text-muted-foreground hover:text-foreground')}>
              {isActive && <motion.span layoutId="order-tab" className="absolute inset-0 rounded-lg bg-card shadow-sm" transition={{type: 'spring', stiffness: 400, damping: 32}} />}
              <span className="relative">
                {o.platform ? PLATFORM[o.platform].label : ''} · {o.order_id}
              </span>
            </button>
          );
        })}
      </div>
      {current && <InvoiceView key={current.order_id} result={current} controls={controls} />}
    </div>
  );
}
