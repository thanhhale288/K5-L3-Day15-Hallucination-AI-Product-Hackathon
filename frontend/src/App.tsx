import {useEffect, useState} from 'react';
import {motion} from 'motion/react';
import {CircleHelp, Coins, LayoutDashboard, MessageSquareText, SquarePen} from 'lucide-react';
import {cn} from '@/lib/utils';
import {hasSeenTour, startTour, type TourView} from '@/lib/tour';
import {USE_BRIDGE} from '@/agent/laiAgent';
import {Button} from '@/components/ui/button';
import ChatPage from './pages/ChatPage';
import DashboardPage from './pages/DashboardPage';

const VIEWS: {value: TourView; label: string; short: string; icon: typeof Coins}[] = [
  {value: 'soi-don', label: 'Soi đơn', short: 'Soi đơn', icon: MessageSquareText},
  {value: 'tong-quan', label: 'Tổng quan tháng', short: 'Tổng quan', icon: LayoutDashboard},
];

function initialView(): TourView {
  return new URLSearchParams(window.location.search).get('view') === 'import' ? 'tong-quan' : 'soi-don';
}

export default function App() {
  const [view, setView] = useState<TourView>(initialView);
  const [chatKey, setChatKey] = useState(0);

  // Lần đầu vào trang: tự chạy hướng dẫn (trừ khi mở link demo có sẵn đơn).
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (hasSeenTour() || p.has('mau') || p.has('notour')) return;
    const t = setTimeout(() => startTour(view), 900);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-card/80 px-4 backdrop-blur sm:gap-4 sm:px-5">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-ink text-primary-foreground shadow-sm">
            <Coins className="size-5" />
          </span>
          <div className="hidden leading-tight sm:block">
            <div className="text-lg font-extrabold tracking-tight whitespace-nowrap">Lãi đi đâu?</div>
            <div className="hidden text-xs text-muted-foreground lg:block">Agent soi phí từng đơn · Shopee · TikTok Shop · Lazada</div>
          </div>
        </div>

        <nav className="flex rounded-xl bg-muted p-1 sm:ml-4" aria-label="Chọn màn">
          {VIEWS.map(v => (
            <button
              key={v.value}
              data-tour={`nav-${v.value}`}
              onClick={() => setView(v.value)}
              aria-current={view === v.value ? 'page' : undefined}
              className={cn(
                'relative flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors sm:px-4 sm:text-base',
                view === v.value ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
              )}>
              {view === v.value && <motion.span layoutId="view-tab" className="absolute inset-0 rounded-lg bg-card shadow-sm" transition={{type: 'spring', stiffness: 400, damping: 32}} />}
              <v.icon className="relative hidden size-4 sm:block" />
              <span className="relative sm:hidden">{v.short}</span>
              <span className="relative hidden sm:inline">{v.label}</span>
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden items-center gap-2 rounded-full border border-border bg-background px-3 py-1 text-sm text-muted-foreground md:flex" title={USE_BRIDGE ? 'Đang nối agent thật qua AG-UI' : 'Phát lại kết quả mẫu, không gọi agent'}>
            <span className="relative flex size-2">
              {USE_BRIDGE && <span className="absolute inline-flex size-full animate-ping rounded-full bg-profit opacity-60" />}
              <span className={cn('relative inline-flex size-2 rounded-full', USE_BRIDGE ? 'bg-profit' : 'bg-fee')} />
            </span>
            {USE_BRIDGE ? 'Agent đang chạy' : 'Chế độ mẫu'}
          </span>
          {view === 'soi-don' && (
            <Button variant="outline" size="lg" className="text-base" onClick={() => setChatKey(k => k + 1)}>
              <SquarePen /> <span className="hidden sm:inline">Đơn mới</span>
            </Button>
          )}
          <Button variant="ghost" size="lg" className="text-base" onClick={() => startTour(view)} aria-label="Hướng dẫn">
            <CircleHelp /> <span className="hidden sm:inline">Hướng dẫn</span>
          </Button>
        </div>
      </header>
      <div className="min-h-0 flex-1">{view === 'soi-don' ? <ChatPage key={chatKey} /> : <DashboardPage />}</div>
    </div>
  );
}
