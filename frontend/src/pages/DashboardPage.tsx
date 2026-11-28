// Trang "Tổng quan tháng" (HA-14, demo bổ sung, ngoài lát cắt). Đọc JSON của data/import_export.py
// (qua POST /import của Thái — TH-11; chưa tải file thì hiện bộ demo frontend/samples/import-thang-11.json).
// Mẫu học từ TrueProfit / BeProfit / BigSeller: lãi từng sàn ghim trên cùng, doanh thu chia cho phí / giá vốn / lãi,
// phí theo khoản, SKU lãi nhất và thấp nhất, quảng cáo so với hoà vốn, đơn cần soi.
// Mọi số hiện ra lấy nguyên từ JSON. Phép chia trong file này chỉ để tính độ dài thanh.
import {useState, type ReactNode} from 'react';
import {motion} from 'motion/react';
import {ChevronDown, FileSpreadsheet, MessageSquareText, Loader2, Sparkles, TrendingDown, TrendingUp, Upload} from 'lucide-react';
import {cn} from '@/lib/utils';
import type {Platform} from '@/types';
import {PLATFORM, pct, vnd} from '@/format';
import {Money, Pill, PlatformPill} from '@/components/bits';
import {Button} from '@/components/ui/button';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import demo from '../../samples/import-thang-11.json';

const USE_API = import.meta.env.VITE_IMPORT_API === '1'; // POST /import của Thái (TH-11)
const PLATFORM_BAR: Record<Platform, string> = {shopee: 'bg-shopee', tiktok: 'bg-tiktok', lazada: 'bg-lazada'};

interface PlatformSummary {
  don: number;
  hoan_tat: number;
  huy: number;
  hoan_hang: number;
  doanh_thu: number;
  tong_phi: number;
  phi_tren_doanh_thu: number;
  tien_ve: number;
  gia_von: number;
  lai_truoc_qc: number;
  don_thieu_gia_von: number;
  phi_theo_khoan?: Record<string, number>;
}

type SkuRow = {
  platform: Platform;
  sku: string;
  don: number;
  ti_le_hoan: number;
  lai_moi_don: number | null;
  cong_tac_lon_nhat: string | null;
  cong_tac_vnd: number;
  ti_le_an_lai: number | null;
  thieu_gia_von: boolean;
};

interface Analysis {
  theo_san: Record<Platform, PlatformSummary>;
  theo_sku_san: SkuRow[];
  dong_lech_luat: {order_id: string; platform: Platform; sku: string; khoan: string; thuc_tru: number; dung_luat: number; chenh: number}[];
  phi_khac_khong_khop: {order_id: string; platform: Platform; sku: string; so_tien: number}[];
  quang_cao: {platform: Platform; chien_dich: string; sku: string; chi_phi: number; gmv: number; roas: number; roas_hoa_von: number; ket_luan: string; lai_sau_qc: number}[];
  bang_phi: string;
}

const rise = (i: number) => ({initial: {opacity: 0, y: 14}, animate: {opacity: 1, y: 0}, transition: {delay: i * 0.06, duration: 0.4}});
const grow = (i: number) => ({initial: {scaleX: 0}, animate: {scaleX: 1}, transition: {delay: 0.25 + i * 0.05, type: 'spring' as const, stiffness: 110, damping: 20}});
const share = (part: number, whole: number) => `${Math.max(0, Math.min(1, whole ? part / whole : 0)) * 100}%`;

function Card({children, className, i = 0, tour}: {children: ReactNode; className?: string; i?: number; tour?: string}) {
  return (
    <motion.section data-tour={tour} {...rise(i)} className={cn('min-w-0 rounded-2xl border border-border bg-card p-5', className)}>
      {children}
    </motion.section>
  );
}

function Title({children, hint, end}: {children: ReactNode; hint?: string; end?: ReactNode}) {
  return (
    <div className="mb-4 flex flex-wrap items-end gap-x-4 gap-y-1">
      <div className="min-w-0 flex-1">
        <h2 className="text-lg font-semibold">{children}</h2>
        {hint && <p className="mt-0.5 text-sm text-muted-foreground">{hint}</p>}
      </div>
      {end}
    </div>
  );
}

/** Ô tooltip khi rê chuột lên một thanh. */
function Tip({children, tip}: {children: ReactNode; tip: ReactNode}) {
  return (
    <div className="group/tip relative">
      {children}
      <div className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 rounded-lg bg-ink px-3 py-1.5 text-sm whitespace-nowrap text-primary-foreground opacity-0 shadow-lg transition-opacity group-hover/tip:opacity-100">
        {tip}
      </div>
    </div>
  );
}

function Legend({items}: {items: [string, string][]}) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted-foreground">
      {items.map(([cls, label]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <span className={cn('h-3 w-4 rounded-[4px]', cls)} />
          {label}
        </span>
      ))}
    </div>
  );
}

function PlatformTile({p, s, i}: {p: Platform; s: PlatformSummary; i: number}) {
  return (
    <Card i={i} className="relative overflow-hidden">
      <span className={cn('absolute inset-x-0 top-0 h-1', PLATFORM_BAR[p])} />
      <div className="flex items-center justify-between">
        <PlatformPill platform={p} />
        <span className="text-sm text-muted-foreground">{s.don} đơn</span>
      </div>
      <div className="mt-4 text-sm text-muted-foreground">Lãi trước quảng cáo</div>
      <Money value={s.lai_truoc_qc} from={0} className="text-3xl font-extrabold tracking-tight" />
      <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
        <div>
          <div className="text-muted-foreground">Doanh thu</div>
          <div className="font-semibold tabular">{vnd(s.doanh_thu)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Phí sàn</div>
          <div className="font-semibold text-alert tabular">{pct(s.phi_tren_doanh_thu)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Hoàn / huỷ</div>
          <div className="font-semibold tabular">
            {s.hoan_hang} / {s.huy}
          </div>
        </div>
      </div>
      {s.don_thieu_gia_von > 0 && <Pill className="mt-3 bg-switch-soft text-[oklch(0.5_0.12_60)]">{s.don_thieu_gia_von} đơn thiếu giá vốn</Pill>}
    </Card>
  );
}

/** Doanh thu mỗi sàn chia thành phí sàn · giá vốn · lãi trước quảng cáo (thanh 100%). */
function RevenueSplit({data}: {data: Analysis}) {
  const rows = (Object.keys(data.theo_san) as Platform[]).map(p => [p, data.theo_san[p]] as const);
  const seg = (s: PlatformSummary) =>
    [
      ['Phí sàn', s.tong_phi, 'bg-alert/75'],
      ['Giá vốn', s.gia_von, 'bg-fee/45'],
      ['Lãi trước QC', s.lai_truoc_qc, 'bg-profit'],
    ] as const;
  return (
    <Card i={3} tour="split-chart">
      <Title hint="Mỗi đồng doanh thu đi về đâu, theo từng sàn." end={<Legend items={[['bg-alert/75', 'Phí sàn'], ['bg-fee/45', 'Giá vốn'], ['bg-profit', 'Lãi trước QC']]} />}>
        Doanh thu chia đi đâu
      </Title>
      <div className="flex flex-col gap-4">
        {rows.map(([p, s], r) => (
          <div key={p} className="grid grid-cols-[7.5rem_1fr] items-center gap-4">
            <div>
              <PlatformPill platform={p} />
              <div className="mt-1 text-sm text-muted-foreground tabular">{vnd(s.doanh_thu)}</div>
            </div>
            <div className="flex h-11 gap-0.5">
              {seg(s).map(([label, v, cls], k) => (
                <motion.div key={label} {...grow(r * 3 + k)} style={{width: share(v, s.doanh_thu), originX: 0}} className="h-full min-w-1">
                  <Tip tip={`${label}: ${vnd(v)}`}>
                    <div className={cn('flex h-11 items-center overflow-hidden rounded-[6px] px-2.5 text-sm font-semibold whitespace-nowrap', cls, label === 'Giá vốn' ? 'text-foreground/80' : 'text-white')}>
                      <span className="truncate tabular">{vnd(v)}</span>
                    </div>
                  </Tip>
                </motion.div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

const FEE_LABEL = (k: string) => (k === 'phi_khac' ? 'Phí khác (không khớp luật)' : k);

/** Phí theo khoản: mỗi sàn một cột, khoản lớn nhất trên cùng. */
function FeeBreakdown({data}: {data: Analysis}) {
  const cols = (Object.keys(data.theo_san) as Platform[]).filter(p => data.theo_san[p].phi_theo_khoan);
  if (!cols.length) return null;
  return (
    <Card i={4} tour="fees">
      <Title hint="Tổng tiền từng khoản phí trong tháng.">Khoản phí nào lớn nhất</Title>
      <div className="grid gap-6 md:grid-cols-3">
        {cols.map((p, c) => {
          const items = Object.entries(data.theo_san[p].phi_theo_khoan ?? {}).sort((a, b) => b[1] - a[1]);
          const top = items[0]?.[1] ?? 1;
          return (
            <div key={p} className="min-w-0">
              <div className="mb-3 flex items-center justify-between">
                <PlatformPill platform={p} />
                <span className="text-sm text-muted-foreground tabular">{vnd(data.theo_san[p].tong_phi)}</span>
              </div>
              <ul className="flex flex-col gap-2.5">
                {items.map(([k, v], i) => (
                  <li key={k}>
                    <div className="flex items-baseline justify-between gap-2 text-sm">
                      <span className={cn('truncate', k === 'phi_khac' && 'font-semibold text-alert')} title={FEE_LABEL(k)}>
                        {FEE_LABEL(k)}
                      </span>
                      <span className="shrink-0 font-medium tabular">{vnd(v)}</span>
                    </div>
                    <div className="mt-1 h-2.5 rounded-full bg-muted">
                      <motion.div {...grow(c * 4 + i)} style={{width: share(v, top), originX: 0}} className={cn('h-full min-w-1 rounded-full', k === 'phi_khac' ? 'bg-alert' : PLATFORM_BAR[p])} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

/** SKU lãi mỗi đơn cao nhất và thấp nhất (bỏ SKU thiếu giá vốn). */
function SkuRanking({rows}: {rows: SkuRow[]}) {
  const ok = rows.filter(r => !r.thieu_gia_von && r.lai_moi_don !== null).sort((a, b) => (b.lai_moi_don ?? 0) - (a.lai_moi_don ?? 0));
  const top = ok.slice(0, 5);
  const bottom = ok.slice(-5).reverse();
  const max = Math.max(1, ...ok.map(r => Math.abs(r.lai_moi_don ?? 0)));
  const List = ({items, good, base}: {items: SkuRow[]; good: boolean; base: number}) => (
    <ul className="flex flex-col gap-3">
      {items.map((r, i) => (
        <li key={`${r.platform}-${r.sku}`} className="grid grid-cols-[minmax(0,9.5rem)_1fr_6.5rem] items-center gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className={cn('size-2.5 shrink-0 rounded-full', PLATFORM_BAR[r.platform])} title={PLATFORM[r.platform].label} />
            <span className="truncate font-mono text-sm">{r.sku}</span>
          </div>
          <Tip tip={`${PLATFORM[r.platform].label} · ${r.don} đơn · hoàn ${pct(r.ti_le_hoan)}`}>
            <div className="h-6 rounded-md bg-muted/60">
              <motion.div {...grow(base + i)} style={{width: share(Math.abs(r.lai_moi_don ?? 0), max), originX: 0}} className={cn('h-full min-w-1 rounded-md', (r.lai_moi_don ?? 0) < 0 ? 'bg-alert' : good ? 'bg-profit' : 'bg-profit/40')} />
            </div>
          </Tip>
          <span className="text-right text-sm font-semibold tabular">{vnd(r.lai_moi_don)}</span>
        </li>
      ))}
    </ul>
  );
  return (
    <Card i={5} tour="sku">
      <Title hint="Lãi mỗi đơn sau phí và giá vốn, trước quảng cáo. Chấm màu là sàn." end={<Legend items={[['bg-shopee', 'Shopee'], ['bg-tiktok', 'TikTok Shop'], ['bg-lazada', 'Lazada']]} />}>
        SKU lãi nhất và thấp nhất
      </Title>
      <div className="grid gap-6">
        <div>
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-profit">
            <TrendingUp className="size-4" /> Lãi nhất
          </div>
          <List items={top} good base={0} />
        </div>
        <div>
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            <TrendingDown className="size-4" /> Lãi thấp nhất
          </div>
          <List items={bottom} good={false} base={5} />
        </div>
      </div>
    </Card>
  );
}

/** Quảng cáo: thanh ROAS, vạch dọc = ROAS hoà vốn. */
function AdsBullet({rows}: {rows: Analysis['quang_cao']}) {
  const max = Math.max(1, ...rows.flatMap(r => [r.roas, r.roas_hoa_von])) * 1.15;
  return (
    <Card i={6} tour="ads">
      <Title hint="Thanh là ROAS, vạch đen là mức hoà vốn. Dưới vạch là quảng cáo đang lỗ." end={<Legend items={[['bg-profit', 'Có lời'], ['bg-alert', 'Đang lỗ']]} />}>
        Quảng cáo có lời không
      </Title>
      <ul className="flex flex-col gap-5">
        {rows.map((r, i) => {
          const isLoss = r.ket_luan === 'lỗ';
          return (
            <li key={r.chien_dich}>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-medium">{r.chien_dich}</span>
                <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <span className={cn('size-2 rounded-full', PLATFORM_BAR[r.platform])} />
                  {PLATFORM[r.platform].label} · chi {vnd(r.chi_phi)}
                </span>
                <span className="ml-auto text-sm font-semibold tabular">
                  ROAS {r.roas} <span className="font-normal text-muted-foreground">· hoà vốn {r.roas_hoa_von}</span>
                </span>
                <Pill className={isLoss ? 'bg-alert-soft text-alert' : 'bg-profit-soft text-profit'}>{isLoss ? 'Đang lỗ' : 'Có lời'}</Pill>
              </div>
              <div className="relative mt-2 h-7 rounded-md bg-muted/60">
                <motion.div {...grow(i)} style={{width: share(r.roas, max), originX: 0}} className={cn('h-full rounded-md', isLoss ? 'bg-alert' : 'bg-profit')} />
                <div className="absolute -inset-y-1.5 w-1 -translate-x-1/2 rounded bg-ink" style={{left: share(r.roas_hoa_von, max)}} title={`Hoà vốn ${r.roas_hoa_von}`} />
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

// Khung tin nhắn cho một đơn cần soi: điền sẵn những gì file export có (sàn, mã đơn, SKU, khoản bị nghi),
// chừa chỗ <…> cho phần chủ shop chép từ trang chi tiết thanh toán. Số tiền lấy nguyên từ JSON.
const PASTE_HEAD: Record<Platform, [string, string, string]> = {
  shopee: ['[Shopee] Chi tiết thanh toán đơn', 'Giá sản phẩm', 'Doanh thu đơn hàng (tiền về)'],
  tiktok: ['[TikTok Shop] Quyết toán đơn', 'Tổng phụ sản phẩm', 'Số tiền quyết toán'],
  lazada: ['[Lazada] Chi tiết giao dịch đơn', 'Giá bán', 'Số tiền thanh toán'],
};
function orderTemplate(platform: Platform, orderId: string, sku: string, fee: string, amount: number): string {
  const [head, price, payout] = PASTE_HEAD[platform];
  return [
    `Soi giúp mình đơn này, khoản ${fee} có đúng không?`,
    `${head} ${orderId}`,
    'Ngày đặt: <ngày/tháng/năm> · Shop thường · Ngành: <ngành hàng>',
    `Sản phẩm: <tên sản phẩm> (SKU ${sku}) x1`,
    `${price}: <giá>đ`,
    `${fee}: -${vnd(amount)}`,
    '<Các khoản phí khác>: -<số tiền>đ',
    `${payout}: <số tiền>đ`,
    'Giá vốn: <số tiền>đ',
  ].join('\n');
}

function ReviewItem({platform, title, tag, tagClass, desc, end, i, onSoi}: {platform: Platform; title: string; tag: string; tagClass: string; desc: string; end?: string; i: number; onSoi?: () => void}) {
  return (
    <motion.li initial={{opacity: 0, x: -8}} animate={{opacity: 1, x: 0}} transition={{delay: 0.35 + i * 0.05}} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-border bg-background/60 px-4 py-3">
      <PlatformPill platform={platform} />
      <span className="font-mono text-sm font-medium">{title}</span>
      <Pill className={tagClass}>{tag}</Pill>
      {end && <span className="ml-auto text-base font-bold text-alert tabular">{end}</span>}
      <div className="flex basis-full items-center gap-3">
        <p className="flex-1 text-sm text-muted-foreground">{desc}</p>
        {onSoi && (
          <Button size="sm" variant="outline" className="shrink-0 text-sm" onClick={onSoi}>
            <MessageSquareText /> Soi đơn này
          </Button>
        )}
      </div>
    </motion.li>
  );
}

function NeedsReview({a, onSoi}: {a: Analysis; onSoi: (text: string) => void}) {
  const missingCogs = a.theo_sku_san.filter(r => r.thieu_gia_von);
  let i = 0;
  return (
    <Card i={7} tour="review" className="border-alert/30">
      <Title hint="Bấm Soi đơn này, điền nốt chi tiết thanh toán, agent kiểm luật và soạn câu hỏi gửi sàn.">Đơn cần soi</Title>
      <ul className="grid gap-2 lg:grid-cols-2">
        {a.dong_lech_luat.map(x => (
          <ReviewItem key={x.order_id + x.khoan} i={i++} platform={x.platform} title={x.order_id} tag="Lệch luật" tagClass="bg-alert-soft text-alert" desc={`${x.khoan} (${x.sku}): bị trừ ${vnd(x.thuc_tru)}, đúng luật ${vnd(x.dung_luat)}`} end={`thu dư ${vnd(x.chenh)}`} onSoi={() => onSoi(orderTemplate(x.platform, x.order_id, x.sku, x.khoan, x.thuc_tru))} />
        ))}
        {a.phi_khac_khong_khop.map(x => (
          <ReviewItem key={x.order_id} i={i++} platform={x.platform} title={x.order_id} tag="Không khớp luật" tagClass="bg-alert-soft text-alert" desc={`"Phí khác" ${vnd(x.so_tien)} trên ${x.sku}: không có trong biểu phí`} onSoi={() => onSoi(orderTemplate(x.platform, x.order_id, x.sku, 'Phí khác', x.so_tien))} />
        ))}
        {missingCogs.map(x => (
          <ReviewItem key={x.platform + x.sku} i={i++} platform={x.platform} title={x.sku} tag="Thiếu giá vốn" tagClass="bg-switch-soft text-[oklch(0.5_0.12_60)]" desc={`${x.don} đơn chưa tính được lãi. Bổ sung giá vốn trong file giá vốn.`} />
        ))}
      </ul>
    </Card>
  );
}

function SkuTable({rows}: {rows: SkuRow[]}) {
  const [isOpen, setOpen] = useState(false);
  return (
    <Card i={8}>
      <button onClick={() => setOpen(o => !o)} className="flex w-full items-center gap-2 text-left" aria-expanded={isOpen}>
        <h2 className="flex-1 text-lg font-semibold">Bảng chi tiết theo SKU</h2>
        <span className="text-sm text-muted-foreground">{isOpen ? 'Thu gọn' : 'Mở bảng'}</span>
        <ChevronDown className={cn('size-5 text-muted-foreground transition-transform', isOpen && 'rotate-180')} />
      </button>
      {isOpen && (
        <div className="mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SKU</TableHead>
                <TableHead>Sàn</TableHead>
                <TableHead className="text-right">Đơn</TableHead>
                <TableHead className="text-right">Tỉ lệ hoàn</TableHead>
                <TableHead className="text-right">Lãi / đơn</TableHead>
                <TableHead>Công tắc lớn nhất</TableHead>
                <TableHead className="text-right">Ăn lãi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map(r => (
                <TableRow key={`${r.platform}-${r.sku}`}>
                  <TableCell className="font-mono text-sm">{r.sku}</TableCell>
                  <TableCell>
                    <PlatformPill platform={r.platform} />
                  </TableCell>
                  <TableCell className="text-right tabular">{r.don}</TableCell>
                  <TableCell className="text-right tabular">{pct(r.ti_le_hoan)}</TableCell>
                  <TableCell className="text-right font-medium tabular">
                    {r.thieu_gia_von ? <Pill className="bg-switch-soft text-[oklch(0.5_0.12_60)]">Thiếu giá vốn</Pill> : vnd(r.lai_moi_don)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{r.cong_tac_lon_nhat ?? '—'}</TableCell>
                  <TableCell className="text-right">
                    {r.ti_le_an_lai === null ? '—' : <Pill className={r.ti_le_an_lai >= 0.5 ? 'bg-alert-soft text-alert' : 'bg-muted text-muted-foreground'}>{pct(r.ti_le_an_lai)}</Pill>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  );
}

function FilePick({label, multiple, onPick, files}: {label: string; multiple?: boolean; onPick: (f: File[]) => void; files: File[]}) {
  return (
    <label className="flex min-w-56 flex-1 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-input bg-background/60 px-4 py-2.5 text-sm hover:border-ink/40">
      <FileSpreadsheet className="size-5 text-profit" />
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{label}</span>
        <span className="block truncate text-sm text-muted-foreground">{files.length ? files.map(f => f.name).join(', ') : 'Chọn tệp .xlsx'}</span>
      </span>
      <input type="file" accept=".xlsx" multiple={multiple} className="sr-only" onChange={e => onPick(Array.from(e.target.files ?? []))} />
    </label>
  );
}

export default function DashboardPage({onSoi}: {onSoi: (text: string) => void}) {
  const [files, setFiles] = useState<File[]>([]);
  const [cogsFile, setCogsFile] = useState<File | null>(null);
  const [data, setData] = useState<Analysis>(demo as Analysis);
  const [source, setSource] = useState<string>('Bộ demo tháng 11 (Shop Demo giả lập)');
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setBusy] = useState(false);

  const upload = async () => {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      files.forEach(f => form.append('exports', f));
      if (cogsFile) form.append('cogs', cogsFile);
      const res = await fetch(`${import.meta.env.VITE_IMPORT_URL ?? ''}/import`, {method: 'POST', body: form});
      const body = (await res.json().catch(() => ({}))) as {phan_tich?: Analysis; error?: string};
      if (!res.ok || !body.phan_tich) throw new Error(body.error ?? `API trả lỗi ${res.status}`);
      setData(body.phan_tich);
      setSource(files.map(f => f.name).join(', '));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="h-full overflow-y-auto">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 p-6">
        <Card tour="data-source" className="flex flex-wrap items-center gap-4">
          <div className="min-w-60 flex-1">
            <h1 className="text-2xl font-extrabold tracking-tight">Tổng quan tháng</h1>
            <p className="mt-0.5 flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="size-4 text-profit" /> {source}
            </p>
          </div>
          <FilePick label="File export đơn hàng" multiple files={files} onPick={f => setFiles(f.slice(0, 3))} />
          <FilePick label="File giá vốn" files={cogsFile ? [cogsFile] : []} onPick={f => setCogsFile(f[0] ?? null)} />
          <Button size="lg" className="text-base" disabled={!USE_API || files.length === 0 || isBusy} onClick={() => void upload()} title={USE_API ? undefined : 'Cần chạy API /import (codebase/app.py --serve)'}>
            {isBusy ? <Loader2 className="animate-spin" /> : <Upload />} Phân tích
          </Button>
          {!USE_API && <p className="basis-full text-sm text-muted-foreground">Đang xem bộ demo. Tải file thật cần bật máy chủ phân tích (xem README).</p>}
          {error && <p className="basis-full rounded-lg bg-alert-soft px-3 py-2 text-sm text-alert">Chưa phân tích được: {error}</p>}
        </Card>

        <div className="grid gap-4 md:grid-cols-3" data-tour="tiles">
          {(Object.keys(data.theo_san) as Platform[]).map((p, i) => (
            <PlatformTile key={p} p={p} s={data.theo_san[p]} i={i} />
          ))}
        </div>
        <RevenueSplit data={data} />
        <FeeBreakdown data={data} />
        <div className="grid gap-4 xl:grid-cols-2">
          <SkuRanking rows={data.theo_sku_san} />
          <AdsBullet rows={data.quang_cao} />
        </div>
        <NeedsReview a={data} onSoi={onSoi} />
        <SkuTable rows={data.theo_sku_san} />
        <p className="px-1 text-sm text-muted-foreground">Lãi chưa trừ ship shop bù và đóng gói. Số do code Python tính từ file export, giao diện chỉ hiển thị.</p>
      </div>
    </main>
  );
}
