// Một AgentResult → hoá đơn đã soi + chỗ để chủ shop thao tác trên đề xuất.
// Chỉ đọc số trong JSON của agent (và kết quả what-if do bridge gọi tools.py). Không tự tính số.
import {useState} from 'react';
import {AnimatePresence, motion} from 'motion/react';
import {Check, Copy, MessageCircleQuestion, Send, ShieldAlert, Sparkles, ToggleRight, Undo2, X} from 'lucide-react';
import {toast} from 'sonner';
import {cn} from '@/lib/utils';
import type {AgentResult, Switch} from '@/types';
import type {Choice, SwitchInfo, WhatIf} from '@/agent/laiAgent';
import {DECISION, ngay, pct, vnd} from '@/format';
import {Money, Pill, PlatformPill} from './bits';
import {Waterfall} from './Waterfall';
import {Button} from './ui/button';
import {Input} from './ui/input';
import {Slider} from './ui/slider';

export interface InvoiceControls {
  switchInfo?: SwitchInfo[];
  whatIf?: WhatIf[];
  canWhatIf?: boolean;
  onWhatIf?: (orderId: string, switchName: string, newRate: number) => void;
  decisions?: Record<string, Choice>;
  onDecide?: (orderId: string, actionText: string, choice: Choice) => void;
  draftSent?: Record<string, boolean>;
  onDraftSent?: (orderId: string, isSent: boolean) => void;
  onAnswerAsk?: (cogs: number) => void;
  isBusy?: boolean;
}

const rise = {initial: {opacity: 0, y: 12}, animate: {opacity: 1, y: 0}};

function Section({title, icon, children, delay = 0, className}: {title: string; icon?: React.ReactNode; children: React.ReactNode; delay?: number; className?: string}) {
  return (
    <motion.section {...rise} transition={{delay, duration: 0.35}} className={cn('rounded-2xl border border-border bg-card p-5 shadow-[0_1px_0_rgb(0_0_0/0.03)]', className)}>
      <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold">
        {icon}
        {title}
      </h3>
      {children}
    </motion.section>
  );
}

function SwitchCard({sw, orderId, info, tried, profit, controls}: {sw: Switch; orderId: string; info?: SwitchInfo; tried?: WhatIf; profit: number | null; controls: InvoiceControls}) {
  // Bridge trả tỉ lệ theo dấu của dòng phí (vd −10). Chủ shop nhập tỉ lệ dương.
  const current = info?.current_rate === null || info?.current_rate === undefined ? null : Math.abs(info.current_rate);
  const [rate, setRate] = useState<number>(current ?? 0);
  const canTry = Boolean(controls.canWhatIf && controls.onWhatIf) && !controls.isBusy;
  const share = Math.min(1, sw.share_of_profit ?? 0);
  const max = Math.max(20, Math.ceil((current ?? 10) * 2));
  return (
    <div className="rounded-xl border border-border bg-background/60 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-base font-semibold">{sw.name}</div>
        <div className="text-right text-base tabular">
          <span className="font-semibold">{vnd(sw.amount)}</span>
          <span className="text-muted-foreground"> · ăn {pct(sw.share_of_profit)} lãi</span>
        </div>
      </div>
      <div className="mt-2.5 h-2 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full bg-switch"
          initial={{width: 0}}
          animate={{width: `${share * 100}%`}}
          transition={{type: 'spring', stiffness: 90, damping: 18, delay: 0.2}}
        />
      </div>

      {controls.canWhatIf && info?.can_change_rate && (
        <div className="mt-4 grid grid-cols-[1fr_auto] items-center gap-4">
          <div>
            <div className="mb-2 flex justify-between text-sm text-muted-foreground">
              <span className="tabular">
                <b className="text-foreground">{rate}%</b> {current !== null && rate !== current && <>· đang {current}%</>}
              </span>
            </div>
            <Slider value={rate} onValueChange={v => setRate(Array.isArray(v) ? v[0] : v)} min={0} max={max} step={0.5} disabled={!controls.canWhatIf} aria-label={`Tỉ lệ mới cho ${sw.name}`} />
          </div>
          <Button size="lg" variant="outline" className="text-base" disabled={!canTry || rate === current} onClick={() => controls.onWhatIf?.(orderId, sw.name, rate)}>
            Thử {rate}%
          </Button>
        </div>
      )}
      {controls.canWhatIf && (
        <div className="mt-3 flex items-center gap-2">
          <Button size="lg" variant="ghost" className="text-base" disabled={!canTry} onClick={() => controls.onWhatIf?.(orderId, sw.name, 0)}>
            <ToggleRight /> Thử tắt
          </Button>
        </div>
      )}

      <AnimatePresence>
        {tried && (
          <motion.div
            key={`${tried.new_rate}`}
            initial={{opacity: 0, height: 0}}
            animate={{opacity: 1, height: 'auto'}}
            exit={{opacity: 0, height: 0}}
            className="overflow-hidden">
            <div className="mt-3 rounded-lg bg-profit-soft p-3 text-sm">
              <div className="text-sm text-profit/80">{tried.new_rate ? `Nếu đổi sang ${tried.new_rate}%` : 'Nếu tắt'}</div>
              <div className="mt-0.5 flex items-baseline gap-2">
                <Money value={tried.profit_after} from={profit ?? 0} className="text-2xl font-bold text-profit" />
                <Pill className="bg-profit text-white">+{vnd(tried.gain_per_order)}</Pill>
              </div>
              {tried.max_order_drop_pct !== null && (
                <div className="mt-1 text-sm text-foreground/70">Vẫn lời hơn nếu số đơn giảm dưới {Math.round(tried.max_order_drop_pct)}%.</div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ActionRow({text, gain, choice, onDecide}: {text: string; gain: number | null; choice?: Choice; onDecide?: (c: Choice) => void}) {
  return (
    <motion.li layout className={cn('flex flex-wrap items-center gap-3 rounded-xl border p-3.5 transition-colors', choice === 'se_lam' ? 'border-profit/40 bg-profit-soft/60' : choice === 'bo_qua' ? 'border-border bg-muted/40 opacity-60' : 'border-border bg-background/60')}>
      <div className="min-w-0 flex-1">
        <div className={cn('text-base', choice === 'bo_qua' && 'line-through')}>{text}</div>
        {gain !== null && <Pill className="mt-1.5 bg-profit-soft text-profit">+{vnd(gain)} / đơn</Pill>}
      </div>
      {onDecide && (
        <AnimatePresence mode="wait" initial={false}>
          {choice ? (
            <motion.div key="chosen" initial={{opacity: 0, scale: 0.9}} animate={{opacity: 1, scale: 1}} exit={{opacity: 0}} className="flex items-center gap-2 text-sm">
              <span className={cn('inline-flex items-center gap-1 text-sm font-semibold', choice === 'se_lam' ? 'text-profit' : 'text-muted-foreground')}>
                {choice === 'se_lam' ? <Check className="size-3.5" /> : <X className="size-3.5" />}
                {choice === 'se_lam' ? 'Sẽ làm trên sàn' : 'Đã bỏ qua'}
              </span>
              <Button size="icon-xs" variant="ghost" aria-label="Đổi lựa chọn" onClick={() => onDecide(choice === 'se_lam' ? 'bo_qua' : 'se_lam')}>
                <Undo2 />
              </Button>
            </motion.div>
          ) : (
            <motion.div key="ask" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0, scale: 0.9}} className="flex gap-1.5">
              <Button size="lg" className="text-base" onClick={() => onDecide('se_lam')}>
                Sẽ làm
              </Button>
              <Button size="lg" variant="ghost" className="text-base" onClick={() => onDecide('bo_qua')}>
                Bỏ qua
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </motion.li>
  );
}

export function InvoiceView({result, controls = {}}: {result: AgentResult; controls?: InvoiceControls}) {
  const [cogs, setCogs] = useState('');
  const d = DECISION[result.decision];
  const oid = result.order_id ?? '';
  const isSent = Boolean(controls.draftSent?.[oid]);
  const base = controls.switchInfo?.find(x => x.order_id === oid && x.base !== null)?.base ?? null;

  if (result.decision === 'refuse') {
    return (
      <motion.div {...rise} className="rounded-2xl border border-border bg-card p-6">
        <div className="flex items-center gap-2 font-semibold">
          <ShieldAlert className="size-5 text-muted-foreground" /> Mình không hỗ trợ yêu cầu này
        </div>
        <p className="mt-2 text-base text-foreground/80">{result.refusal_reason}</p>
      </motion.div>
    );
  }

  const copyDraft = async () => {
    if (!result.draft_to_platform) return;
    await navigator.clipboard.writeText(result.draft_to_platform);
    toast.success('Đã chép nháp. Bạn tự dán vào kênh hỗ trợ người bán của sàn.');
  };

  return (
    <div className="flex flex-col gap-4">
      <motion.header {...rise} transition={{duration: 0.35}} className="rounded-2xl bg-ink p-5 text-primary-foreground">
        <div className="flex flex-wrap items-center gap-2">
          {result.platform && (
            <span className="rounded-full bg-white/95 p-px">
              <PlatformPill platform={result.platform} />
            </span>
          )}
          <span className="font-mono text-base opacity-90">{result.order_id ?? '—'}</span>
          <span className="text-sm opacity-75">· đặt {ngay(result.order_date)}</span>
          <Pill className={cn('ml-auto', d.chip)}>{d.label}</Pill>
        </div>
        <div className="mt-5 flex flex-wrap items-end gap-x-10 gap-y-3">
          <div>
            <div className="text-base opacity-75" title="Tiền về trừ giá vốn. Chưa trừ ship shop bù, đóng gói, quảng cáo.">Lãi thật mỗi đơn</div>
            {result.profit === null ? (
              <div className="text-3xl leading-tight font-bold opacity-70">Chưa tính được</div>
            ) : (
            <Money value={result.profit} from={result.payout ?? 0} className={cn('text-5xl leading-none font-extrabold tracking-tight', (result.profit ?? 0) < 0 ? 'text-[oklch(0.75_0.16_27)]' : 'text-[oklch(0.82_0.14_158)]')} />
            )}
          </div>
          <div className="pb-1">
            <div className="text-base opacity-75">Tiền về</div>
            <div className="text-2xl font-semibold tabular">{vnd(result.payout)}</div>
          </div>
          <div className="pb-1">
            <div className="text-base opacity-75">Giá vốn</div>
            <div className="text-2xl font-semibold tabular">{vnd(result.cogs)}</div>
          </div>
        </div>
      </motion.header>

      {result.decision === 'ask' && result.question && (
        <Section title="Agent cần bạn trả lời" icon={<MessageCircleQuestion className="size-4 text-switch" />} delay={0.05} className="border-switch/50 bg-switch-soft/50">
          <p className="text-base">{result.question}</p>
          <form
            className="mt-4 flex flex-wrap gap-2"
            onSubmit={e => {
              e.preventDefault();
              const n = Number(cogs.replace(/\D/g, ''));
              if (n > 0) controls.onAnswerAsk?.(n);
            }}>
            <Input value={cogs} onChange={e => setCogs(e.target.value)} inputMode="numeric" placeholder="Giá vốn mỗi sản phẩm, vd 120000" className="h-11 max-w-72 bg-card text-base" aria-label="Giá vốn mỗi sản phẩm" />
            <Button type="submit" size="lg" disabled={!cogs || !controls.onAnswerAsk || controls.isBusy}>
              <Send /> Gửi và soi tiếp
            </Button>
          </form>
        </Section>
      )}

      {result.decision === 'escalate' && result.draft_to_platform && (
        <motion.section {...rise} transition={{delay: 0.05}} className={cn('rounded-2xl bg-card p-5', isSent ? 'border border-profit/40' : 'beam')}>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="flex items-center gap-2 text-lg font-semibold">
              {isSent ? <Check className="size-4 text-profit" /> : <ShieldAlert className="size-4 text-alert" />}
              {isSent ? 'Đã gửi câu hỏi cho sàn' : 'Câu hỏi gửi sàn'}
            </h3>
            <div className="ml-auto flex gap-1.5">
              <Button size="lg" variant="outline" className="text-base" onClick={() => void copyDraft()}>
                <Copy /> Chép nháp
              </Button>
              {controls.onDraftSent && (
                <Button size="lg" variant={isSent ? 'ghost' : 'default'} className="text-base" onClick={() => controls.onDraftSent?.(oid, !isSent)}>
                  {isSent ? 'Bỏ đánh dấu' : 'Đã tự gửi'}
                </Button>
              )}
            </div>
          </div>
          <blockquote className="mt-3 rounded-lg border-l-2 border-alert/60 bg-muted/50 px-4 py-3 text-base leading-relaxed">{result.draft_to_platform}</blockquote>
        </motion.section>
      )}

      {result.lines.length > 0 && (
        <Section title="Tiền đi đâu" delay={0.1}>
          <Waterfall result={result} base={base} />
        </Section>
      )}

      {result.switches.length > 0 && (
        <Section title="Công tắc đang ăn lãi" icon={<ToggleRight className="size-4 text-switch" />} delay={0.15}>
          <div className="flex flex-col gap-3">
            {result.switches.map(s => (
              <SwitchCard
                key={s.name}
                sw={s}
                orderId={oid}
                profit={result.profit}
                info={controls.switchInfo?.find(x => x.order_id === oid && x.switch === s.name)}
                tried={controls.whatIf?.find(x => x.order_id === oid && x.switch === s.name)}
                controls={controls}
              />
            ))}
          </div>
        </Section>
      )}

      {result.actions.length > 0 && (
        <Section title="Agent đề xuất" icon={<Sparkles className="size-4 text-profit" />} delay={0.2}>
          <ul className="flex flex-col gap-2">
            {result.actions.map(a => (
              <ActionRow
                key={a.text}
                text={a.text}
                gain={a.gain_per_order}
                choice={controls.decisions?.[`${oid}::${a.text}`]}
                onDecide={controls.onDecide ? c => controls.onDecide?.(oid, a.text, c) : undefined}
              />
            ))}
          </ul>
        </Section>
      )}

    </div>
  );
}
