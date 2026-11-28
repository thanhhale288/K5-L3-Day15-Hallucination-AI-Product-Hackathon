import {useState} from 'react';
import {motion} from 'motion/react';
import {Coins} from 'lucide-react';
import {cn} from '@/lib/utils';
import ChatPage from './pages/ChatPage';
import ImportPage from './pages/ImportPage';

type View = 'soi-don' | 'import';
const VIEWS: {value: View; label: string}[] = [
  {value: 'soi-don', label: 'Soi đơn'},
  {value: 'import', label: 'Import tháng'},
];

export default function App() {
  const [view, setView] = useState<View>(new URLSearchParams(window.location.search).get('view') === 'import' ? 'import' : 'soi-don');
  return (
    <div className="flex h-dvh flex-col">
      <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-background/80 px-5 backdrop-blur">
        <span className="grid size-8 place-items-center rounded-xl bg-ink text-primary-foreground">
          <Coins className="size-[18px]" />
        </span>
        <div className="text-lg font-extrabold tracking-tight whitespace-nowrap">Lãi đi đâu?</div>
        <nav className="ml-auto flex rounded-xl bg-muted p-1" aria-label="Chọn màn">
          {VIEWS.map(v => (
            <button
              key={v.value}
              onClick={() => setView(v.value)}
              aria-current={view === v.value ? 'page' : undefined}
              className={cn('relative rounded-lg px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors sm:px-4 sm:text-base', view === v.value ? 'text-foreground' : 'text-muted-foreground hover:text-foreground')}>
              {view === v.value && <motion.span layoutId="view-tab" className="absolute inset-0 rounded-lg bg-card shadow-sm" transition={{type: 'spring', stiffness: 400, damping: 32}} />}
              <span className="relative">{v.label}</span>
            </button>
          ))}
        </nav>
      </header>
      <div className="min-h-0 flex-1">{view === 'soi-don' ? <ChatPage /> : <ImportPage />}</div>
    </div>
  );
}
