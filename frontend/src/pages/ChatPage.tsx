// Màn chính: chat với agent "Lãi đi đâu?" qua AG-UI.
// Cột chat bên trái (dán đơn, xem agent lập kế hoạch và gọi công cụ), vùng kết quả bên phải (thác tiền, công tắc, đề xuất).
import {useEffect, useRef, useState} from 'react';
import {AnimatePresence, motion} from 'motion/react';
import {ArrowUp, ChevronsDown, ChevronsUp, Coins, Check, ChevronDown, CircleAlert, ClipboardPaste, Loader2, ReceiptText, Wrench} from 'lucide-react';
import {cn} from '@/lib/utils';
import {useLaiAgent, type ToolCallView, type Turn} from '@/agent/useLaiAgent';
import {USE_BRIDGE, type Choice} from '@/agent/laiAgent';
import {SAMPLES} from '@/api';
import {isPolicy, isSession, type SoiResult} from '@/types';
import {DECISION, PLATFORM, vnd} from '@/format';
import {InvoiceView, type InvoiceControls} from '@/components/InvoiceView';
import {SessionView} from '@/components/SessionView';
import {PolicyView} from '@/components/PolicyView';
import {Pill, RichText} from '@/components/bits';
import {Button} from '@/components/ui/button';
import {AnnotatedExample, PromptHelpDialog, SAMPLE_EXAMPLE, starters, type Starter} from '@/components/PromptGuide';
import {useMediaQuery} from '@/lib/useMediaQuery';
import {toast} from 'sonner';
import {hasSeenTour, startTour} from '@/lib/tour';
import {ResizableHandle, ResizablePanel, ResizablePanelGroup} from '@/components/ui/resizable';
import {useDefaultLayout} from 'react-resizable-panels';

const MAX_PASTE_LINES = 8;

function Logo({className}: {className?: string}) {
  return (
    <span className={cn('grid size-8 shrink-0 place-items-center rounded-lg bg-ink text-primary-foreground', className)}>
      <Coins className="size-4" />
    </span>
  );
}

function UserBubble({text}: {text: string}) {
  const lines = text.split('\n');
  const isLong = lines.length > MAX_PASTE_LINES;
  const [isOpen, setOpen] = useState(false);
  const shown = isLong && !isOpen ? lines.slice(0, MAX_PASTE_LINES) : lines;
  return (
    <motion.div layout initial={{opacity: 0, y: 8, scale: 0.98}} animate={{opacity: 1, y: 0, scale: 1}} className="ml-8 self-end overflow-hidden rounded-2xl rounded-br-md bg-ink px-4 py-3 text-primary-foreground">
      <div className={cn('whitespace-pre-wrap break-words', lines.length > 1 ? 'font-mono text-sm leading-relaxed opacity-90' : 'text-base')}>
        {shown.map((l, i) => (
          <div key={i}>{l || ' '}</div>
        ))}
      </div>
      {isLong && (
        <button onClick={() => setOpen(o => !o)} className="mt-2 inline-flex items-center gap-1 rounded-md bg-white/10 px-2 py-1 text-sm font-medium hover:bg-white/20">
          {isOpen ? <ChevronsUp className="size-4" /> : <ChevronsDown className="size-4" />}
          {isOpen ? 'Thu gọn' : `Xem thêm ${lines.length - MAX_PASTE_LINES} dòng`}
        </button>
      )}
    </motion.div>
  );
}

function ToolCalls({calls, isDone}: {calls: ToolCallView[]; isDone: boolean}) {
  const [isOpen, setOpen] = useState(false);
  const running = calls.filter(c => c.status === 'running').length;
  return (
    <div className="rounded-xl border border-border bg-card/70">
      <button onClick={() => setOpen(o => !o)} className="flex w-full items-center gap-2 px-3 py-2.5 text-sm" aria-expanded={isOpen}>
        <Wrench className="size-3.5 text-muted-foreground" />
        <span className={cn('font-medium', !isDone && 'shimmer')}>{isDone ? `Đã gọi ${calls.length} công cụ` : `Đang gọi công cụ · ${calls.length}`}</span>
        {!isDone && running > 0 && <Loader2 className="size-3 animate-spin text-muted-foreground" />}
        <ChevronDown className={cn('ml-auto size-3.5 text-muted-foreground transition-transform', isOpen && 'rotate-180')} />
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.ol initial={{height: 0}} animate={{height: 'auto'}} exit={{height: 0}} className="overflow-hidden">
            <div className="max-h-64 overflow-y-auto border-t border-border px-3 py-2">
              {calls.map(c => (
                <li key={c.id} className="flex items-center gap-2 py-1 text-sm">
                  {c.status === 'running' ? (
                    <Loader2 className="size-3 shrink-0 animate-spin text-muted-foreground" />
                  ) : c.status === 'error' ? (
                    <CircleAlert className="size-3 shrink-0 text-alert" />
                  ) : (
                    <Check className="size-3 shrink-0 text-profit" />
                  )}
                  <span className="shrink-0 font-medium">{c.label}</span>
                  {c.target && <span className="truncate font-mono text-xs text-muted-foreground">{c.target}</span>}
                </li>
              ))}
            </div>
          </motion.ol>
        )}
      </AnimatePresence>
    </div>
  );
}

function AssistantTurn({turn, onOpenResult}: {turn: Extract<Turn, {role: 'assistant'}>; onOpenResult?: () => void}) {
  return (
    <motion.div initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} className="flex gap-2.5">
      <Logo className="mt-0.5" />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        {turn.steps.length > 0 && (
          <ul className="flex flex-col gap-1" data-tour="steps">
            {turn.steps.map((s, i) => {
              const isLive = !turn.isDone && i === turn.steps.length - 1;
              return (
                <motion.li key={i} initial={{opacity: 0, x: -4}} animate={{opacity: 1, x: 0}} className="flex gap-2 text-sm text-muted-foreground">
                  <span className={cn('mt-1.5 size-1.5 shrink-0 rounded-full', isLive ? 'animate-pulse bg-switch' : 'bg-profit')} />
                  <span className={cn(isLive && 'shimmer')}>{s}</span>
                </motion.li>
              );
            })}
          </ul>
        )}
        {turn.calls.length > 0 && <ToolCalls calls={turn.calls} isDone={turn.isDone} />}
        {!turn.isDone && !turn.text && turn.calls.length === 0 && turn.steps.length === 0 && <span className="shimmer text-sm">Agent đang đọc chữ dán…</span>}
        {turn.text && (
          <div className="flex flex-col gap-2 text-base leading-relaxed text-foreground/85">
            <RichText text={turn.text} />
          </div>
        )}
        {turn.error && (
          <div className="rounded-xl border border-alert/30 bg-alert-soft px-3 py-2 text-sm text-alert">
            <b>Agent gặp lỗi.</b> {turn.error}
          </div>
        )}
        {turn.isDone && onOpenResult && (
          <Button size="lg" variant="outline" className="self-start text-base" onClick={onOpenResult}>
            <ReceiptText /> Xem kết quả
          </Button>
        )}
      </div>
    </motion.div>
  );
}

function Welcome({onPick}: {onPick: (paste: string) => void}) {
  return (
    <div className="flex flex-col gap-5 py-6">
      <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}}>
        <h2 className="text-3xl leading-tight font-extrabold tracking-tight text-balance">
          Dán chi tiết thanh toán. <span className="text-profit">Agent chỉ ra lãi đi đâu.</span>
        </h2>
        <p className="mt-2 text-base text-muted-foreground">Shopee · TikTok Shop · Lazada, 1–5 đơn mỗi lần. Hoặc hỏi về phí, chính sách của 3 sàn.</p>
      </motion.div>
      <div className="flex flex-col gap-2" data-tour="samples">
        <div className="text-sm font-semibold text-muted-foreground">Thử đơn mẫu</div>
        {SAMPLES.filter(s => s.paste).map((s, i) => (
          <motion.button
            key={s.file}
            initial={{opacity: 0, y: 8}}
            animate={{opacity: 1, y: 0}}
            transition={{delay: 0.1 + i * 0.06}}
            whileHover={{x: 3}}
            onClick={() => onPick(s.paste!)}
            className="group flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3.5 text-left text-base shadow-[0_1px_0_rgb(0_0_0/0.03)] hover:border-ink/30">
            <span className="flex-1">{s.label}</span>
            <Pill className={DECISION[s.decision as keyof typeof DECISION]?.chip ?? 'bg-muted'}>{DECISION[s.decision as keyof typeof DECISION]?.label}</Pill>
          </motion.button>
        ))}
      </div>
    </div>
  );
}

function Composer({onSend, isBusy, model, memoryTurns, value, setValue, inputRef, starters: chips, onHelp}: {
  onSend: (t: string) => void;
  isBusy: boolean;
  model?: string;
  memoryTurns?: number;
  value: string;
  setValue: (v: string) => void;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  starters: Starter[];
  onHelp: React.ReactNode;
}) {
  const ref = inputRef;
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 260)}px`;
  }, [value, ref]);
  const fill = (c: Starter) => {
    setValue(c.text);
    requestAnimationFrame(() => {
      const el = ref.current;
      if (!el) return;
      el.focus();
      const at = c.caret === 'end' ? c.text.length : c.text.indexOf('<') >= 0 ? c.text.indexOf('<') : c.text.length;
      el.setSelectionRange(at, c.caret === 'end' || c.text.indexOf('<') < 0 ? at : c.text.indexOf('>', at) + 1);
    });
  };
  const submit = () => {
    const t = value.trim();
    if (!t || isBusy || t.includes('<')) return;
    onSend(t);
    setValue('');
  };
  return (
    <div className="flex flex-col gap-2" data-tour="composer">
    <div className="flex flex-wrap items-center gap-1.5" data-tour="starters">
      {chips.map(c => (
        <motion.button
          key={c.label}
          initial={{opacity: 0, y: 4}}
          animate={{opacity: 1, y: 0}}
          onClick={() => fill(c)}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-sm text-foreground/80 hover:border-ink/40 hover:text-foreground">
          <c.icon className="size-3.5 text-muted-foreground" />
          {c.label}
        </motion.button>
      ))}
      <span className="ml-auto">{onHelp}</span>
    </div>
    <div className="rounded-2xl border border-border bg-card p-2 shadow-[0_8px_30px_-12px_rgb(0_0_0/0.15)] focus-within:border-ink/40">
      <textarea
        ref={ref}
        rows={1}
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder={'Dán chi tiết thanh toán của đơn, hoặc hỏi về phí, chính sách của 3 sàn.\nVd: Phí Voucher Xtra của Shopee có trần không?'}
        aria-label="Tin nhắn cho agent"
        className="block w-full resize-none bg-transparent px-2 py-2 text-base outline-none placeholder:text-muted-foreground/70"
      />
      <div className="flex items-center gap-2 px-1 pt-1">
        {model === 'fake' ? (
          <Pill className="bg-switch-soft text-[oklch(0.5_0.12_60)]">AI giả · chỉ đúng với DEMO-0412</Pill>
        ) : (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className={cn('size-1.5 rounded-full', USE_BRIDGE ? 'bg-profit' : 'bg-fee')} />
            {USE_BRIDGE ? model ?? 'Agent thật' : 'Chế độ mẫu'}
            {USE_BRIDGE && memoryTurns ? <span title="Agent nhớ các lượt trước trong cuộc trò chuyện này để hiểu câu hỏi nối tiếp. Bấm Đơn mới để bắt đầu lại."> · nhớ {memoryTurns} lượt</span> : null}
          </span>
        )}
        <span className="ml-auto hidden text-xs text-muted-foreground sm:inline">Enter để gửi · Shift+Enter xuống dòng</span>
        <Button size="icon" className="rounded-full" disabled={!value.trim() || isBusy || value.includes('<')} onClick={submit} aria-label="Gửi" title={value.includes('<') ? 'Thay các chỗ <…> bằng số của đơn' : undefined}>
          {isBusy ? <Loader2 className="animate-spin" /> : <ArrowUp />}
        </Button>
      </div>
    </div>
    </div>
  );
}

function EmptyResult({onUse}: {onUse: (text: string) => void}) {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-2xl flex-col justify-center gap-4" data-tour="example">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Mẫu tin nhắn</h2>
          <p className="text-sm text-muted-foreground">Chép chi tiết thanh toán trong Seller Center, dán vào ô chat.</p>
        </div>
        <Button size="lg" className="text-base" onClick={() => onUse(SAMPLE_EXAMPLE)}>
          <ClipboardPaste /> Dùng mẫu này
        </Button>
      </div>
      <AnnotatedExample compact />
    </div>
  );
}

function historyLabel(r: SoiResult): string {
  if (isPolicy(r)) return 'Hỏi chính sách';
  if (isSession(r)) return r.platform_comparison ? `${r.orders.length} đơn · so sàn` : `${r.orders.length} đơn`;
  if (r.decision === 'refuse') return 'Yêu cầu bị từ chối';
  return `${r.platform ? PLATFORM[r.platform].label : ''} · ${r.order_id ?? '—'}`;
}

function HistoryBar({history, current, onPick}: {history: SoiResult[]; current: SoiResult | null; onPick: (trace: string | null) => void}) {
  return (
    <div data-tour="history" className="flex shrink-0 items-center gap-2 overflow-x-auto border-b border-border bg-card/70 px-6 py-2.5 backdrop-blur">
      <span className="shrink-0 text-sm font-semibold text-muted-foreground">Đã soi</span>
      {history.map(h => {
        const isActive = h.trace_id === current?.trace_id;
        return (
          <button
            key={h.trace_id ?? historyLabel(h)}
            onClick={() => onPick(h.trace_id)}
            className={cn('relative flex shrink-0 items-center gap-2 rounded-full border px-3 py-1 text-sm whitespace-nowrap transition-colors', isActive ? 'border-ink bg-ink text-primary-foreground' : 'border-border bg-background hover:border-ink/40')}>
            <span className={cn('size-2 rounded-full', isPolicy(h) ? 'bg-lazada' : {act: 'bg-profit', ask: 'bg-switch', escalate: 'bg-alert', refuse: 'bg-fee'}[h.decision])} />
            {historyLabel(h)}
          </button>
        );
      })}
    </div>
  );
}

export default function ChatPage({incoming}: {incoming?: {text: string; id: number} | null}) {
  const {turns, state, isRunning, send, setLocal, note} = useLaiAgent();
  const isNarrow = useMediaQuery('(max-width: 900px)');
  const [isSheetOpen, setSheetOpen] = useState(false);
  const latest = state.result ?? null;
  const scrollRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const useText = (text: string) => {
    setDraft(text);
    setSheetOpen(false);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  // Từ trang tổng quan ("Soi đơn này"): điền khung tin nhắn, chọn sẵn chỗ <…> đầu tiên.
  useEffect(() => {
    if (!incoming) return;
    setDraft(incoming.text);
    setSheetOpen(false);
    const t = setTimeout(() => {
      const el = inputRef.current;
      if (!el) return;
      el.focus();
      const at = incoming.text.indexOf('<');
      if (at >= 0) el.setSelectionRange(at, incoming.text.indexOf('>', at) + 1);
    }, 50);
    toast('Đã mở khung tin nhắn cho đơn này', {
      description: incoming.text.includes('<')
        ? 'Điền các chỗ <…> từ trang chi tiết thanh toán của đơn rồi gửi.'
        : 'Chi tiết thanh toán đã điền sẵn từ file export. Xem lại rồi bấm gửi.',
    });
    return () => clearTimeout(t);
  }, [incoming]);

  // ?mau=<file>: dán sẵn một đơn mẫu (để demo và chụp màn hình).
  const didPreset = useRef(false);
  useEffect(() => {
    if (didPreset.current) return;
    didPreset.current = true;
    const s = SAMPLES.find(x => x.file === new URLSearchParams(window.location.search).get('mau'));
    if (s?.paste) void send(s.paste);
  }, [send]);

  useEffect(() => {
    if (turns.length) scrollRef.current?.scrollTo({top: scrollRef.current.scrollHeight, behavior: 'smooth'});
  }, [turns]);

  const controls: InvoiceControls = {
    switchInfo: state.switch_info,
    whatIf: state.what_if,
    canWhatIf: USE_BRIDGE,
    isBusy: isRunning,
    onWhatIf: (orderId, sw, rate) =>
      void send('', {type: 'what_if', order_id: orderId, switch: sw, new_rate: rate},
        rate ? `Thử đổi ${sw} sang ${rate}% ở đơn ${orderId}` : `Thử tắt ${sw} ở đơn ${orderId}`),
    decisions: state.decisions,
    onDecide: (orderId: string, text: string, choice: Choice) => {
      setLocal({decisions: {...state.decisions, [`${orderId}::${text}`]: choice}});
      note(choice === 'se_lam' ? `Bạn sẽ làm: ${text} (đơn ${orderId})` : `Bạn bỏ qua: ${text} (đơn ${orderId})`);
    },
    draftSent: state.draft_sent,
    onDraftSent: (orderId, isSent) => {
      setLocal({draft_sent: {...state.draft_sent, [orderId]: isSent}});
      note(isSent ? `Bạn đã tự gửi câu hỏi cho sàn về đơn ${orderId}` : `Bỏ đánh dấu đã gửi (đơn ${orderId})`);
    },
    onAnswerAsk: cogs => void send(`Giá vốn mỗi sản phẩm: ${vnd(cogs)}`),
  };

  // Các kết quả đã có trong phiên (để chuyển qua lại). Kết quả mới cùng trace thay kết quả cũ.
  const [history, setHistory] = useState<SoiResult[]>([]);
  const [pickedTrace, setPickedTrace] = useState<string | null>(null);
  useEffect(() => {
    if (!latest) return;
    setHistory(h => [...h.filter(x => x.trace_id !== latest.trace_id), latest]);
    setPickedTrace(null);
  }, [latest]);
  const result = (pickedTrace && history.find(h => h.trace_id === pickedTrace)) || latest;

  // Lần đầu có kết quả: hướng dẫn ngắn chỉ vào lãi thật, thác tiền, công tắc, nháp, đề xuất.
  const hasResult = Boolean(latest);
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (!hasResult || isNarrow || hasSeenTour('ket-qua') || p.has('mau') || p.has('notour')) return;
    const t = setTimeout(() => startTour('ket-qua'), 2200);
    return () => clearTimeout(t);
  }, [hasResult, isNarrow]);
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({id: 'lai-split', storage: localStorage});

  const resultBody = result ? (
    <AnimatePresence mode="wait">
      <motion.div key={result.trace_id ?? 'r'} initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}>
        {isPolicy(result) ? (
          <PolicyView result={result} />
        ) : isSession(result) ? (
          <SessionView result={result} controls={controls} />
        ) : (
          <InvoiceView result={result} controls={controls} />
        )}
      </motion.div>
    </AnimatePresence>
  ) : (
    <EmptyResult onUse={useText} />
  );

  const lastAssistant = [...turns].reverse().find(t => t.role === 'assistant');

  const chat = (
    <div className="flex h-full min-h-0 flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-5">
        {turns.length === 0 ? (
          <Welcome onPick={paste => void send(paste)} />
        ) : (
          <div className="flex flex-col gap-5 py-6">
            {turns.map(t =>
              t.role === 'user' ? (
                <UserBubble key={t.id} text={t.text} />
              ) : t.role === 'system' ? (
                <motion.div key={t.id} initial={{opacity: 0, scale: 0.95}} animate={{opacity: 1, scale: 1}} className="self-center rounded-full bg-muted px-3 py-1 text-center text-sm text-muted-foreground">
                  {t.text}
                </motion.div>
              ) : (
                <AssistantTurn key={t.id} turn={t} onOpenResult={isNarrow && result && t === lastAssistant ? () => setSheetOpen(true) : undefined} />
              ),
            )}
          </div>
        )}
      </div>
      <div className="px-4 pt-2 pb-4">
        <Composer
          onSend={t => void send(t)}
          isBusy={isRunning}
          model={state.model}
          memoryTurns={state.memory_turns}
          value={draft}
          setValue={setDraft}
          inputRef={inputRef}
          starters={starters(!latest ? 'start' : !isSession(latest) && !isPolicy(latest) && latest.decision === 'ask' ? 'ask' : 'after')}
          onHelp={<PromptHelpDialog onUse={useText} />}
        />
      </div>
    </div>
  );

  if (isNarrow) {
    return (
      <div className="relative h-full">
        {chat}
        <AnimatePresence>
          {isSheetOpen && result && (
            <motion.div
              initial={{y: '100%'}}
              animate={{y: 0}}
              exit={{y: '100%'}}
              transition={{type: 'spring', stiffness: 300, damping: 34}}
              className="absolute inset-0 z-20 flex flex-col bg-background">
              <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
                <span className="text-lg font-semibold">Kết quả soi đơn</span>
                <Button size="lg" variant="ghost" className="text-base" onClick={() => setSheetOpen(false)}>
                  Đóng
                </Button>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto p-4">{resultBody}</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <ResizablePanelGroup orientation="horizontal" defaultLayout={defaultLayout} onLayoutChanged={onLayoutChanged} className="h-full min-h-0">
      <h1 className="sr-only">Chat soi đơn</h1>
      <ResizablePanel id="chat" defaultSize="34%" minSize="320px" maxSize="60%" className="min-h-0 bg-background">
        {chat}
      </ResizablePanel>
      <ResizableHandle withHandle data-tour="split" className="w-1.5 bg-border transition-colors hover:bg-profit/50 data-[separator=active]:bg-profit" />
      <ResizablePanel id="result" minSize="40%" className="min-h-0">
        <main className="flex h-full min-h-0 flex-col bg-[radial-gradient(ellipse_at_top,oklch(0.96_0.02_158/0.5),transparent_60%)]">
          {history.length > 0 && <HistoryBar history={history} current={result} onPick={setPickedTrace} />}
          <div className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto max-w-4xl p-8">{resultBody}</div>
          </div>
        </main>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
