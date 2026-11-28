// Màn import tháng (HA-14, demo bổ sung, ngoài lát cắt). Đọc JSON của data/import_export.py
// (qua POST /import của Thái — TH-11; chưa có API thì đọc frontend/samples/import-thang-11.json).
// Mục đích: chọn ra ĐƠN CẦN SOI, không phải báo cáo lãi tổng. Mọi số do code Python tính.
import {useState} from 'react';
import {motion} from 'motion/react';
import {FileSpreadsheet, Loader2, Sparkles, Upload} from 'lucide-react';
import {cn} from '@/lib/utils';
import type {Platform} from '@/types';
import {pct, vnd} from '@/format';
import {Money, Pill, PlatformPill} from '@/components/bits';
import {Button} from '@/components/ui/button';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import demo from '../../samples/import-thang-11.json';

const USE_API = import.meta.env.VITE_IMPORT_API === '1'; // POST /import của Thái (TH-11)

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

const rise = (i: number) => ({initial: {opacity: 0, y: 14}, animate: {opacity: 1, y: 0}, transition: {delay: i * 0.08, duration: 0.4}});

function Card({children, className, i = 0}: {children: React.ReactNode; className?: string; i?: number}) {
  return (
    <motion.section {...rise(i)} className={cn('min-w-0 rounded-2xl border border-border bg-card p-5', className)}>
      {children}
    </motion.section>
  );
}

function Title({children, hint}: {children: React.ReactNode; hint?: string}) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold">{children}</h2>
      {hint && <p className="mt-1 text-sm text-muted-foreground">{hint}</p>}
    </div>
  );
}

function PlatformTile({p, s, i}: {p: Platform; s: PlatformSummary; i: number}) {
  return (
    <Card i={i}>
      <div className="flex items-center justify-between">
        <PlatformPill platform={p} />
        <span className="text-sm text-muted-foreground">{s.don} đơn</span>
      </div>
      <div className="mt-4 text-sm text-muted-foreground">Lãi trước quảng cáo</div>
      <Money value={s.lai_truoc_qc} from={0} className="text-3xl font-extrabold tracking-tight" />
      <div className="mt-3 mb-1 text-sm text-muted-foreground">Phí sàn / doanh thu</div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <motion.div className="h-full rounded-full bg-alert/70" initial={{width: 0}} animate={{width: `${Math.min(1, s.phi_tren_doanh_thu) * 100}%`}} transition={{delay: 0.3 + i * 0.1, duration: 0.8, ease: 'easeOut'}} />
      </div>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-base">
        <dt className="text-muted-foreground">Doanh thu</dt>
        <dd className="text-right tabular">{vnd(s.doanh_thu)}</dd>
        <dt className="text-muted-foreground">Phí sàn</dt>
        <dd className="text-right tabular">
          {vnd(s.tong_phi)} <span className="font-semibold text-alert">· {pct(s.phi_tren_doanh_thu)}</span>
        </dd>
        <dt className="text-muted-foreground">Tiền về</dt>
        <dd className="text-right tabular">{vnd(s.tien_ve)}</dd>
        <dt className="text-muted-foreground">Hoàn / huỷ</dt>
        <dd className="text-right tabular">
          {s.hoan_hang} hoàn · {s.huy} huỷ
        </dd>
      </dl>
      {s.don_thieu_gia_von > 0 && <Pill className="mt-3 bg-switch-soft text-[oklch(0.5_0.12_60)]">{s.don_thieu_gia_von} đơn thiếu giá vốn</Pill>}
    </Card>
  );
}

function ReviewItem({platform, title, tag, tagClass, desc, end, i}: {platform: Platform; title: string; tag: string; tagClass: string; desc: string; end?: string; i: number}) {
  return (
    <motion.li initial={{opacity: 0, x: -8}} animate={{opacity: 1, x: 0}} transition={{delay: 0.35 + i * 0.05}} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-border bg-background/60 px-4 py-3">
      <PlatformPill platform={platform} />
      <span className="font-mono text-sm font-medium">{title}</span>
      <Pill className={tagClass}>{tag}</Pill>
      {end && <span className="ml-auto text-sm font-bold text-alert tabular">{end}</span>}
      <p className="basis-full text-sm text-muted-foreground">{desc}</p>
    </motion.li>
  );
}

function NeedsReview({a}: {a: Analysis}) {
  const missingCogs = a.theo_sku_san.filter(r => r.thieu_gia_von);
  let i = 0;
  return (
    <Card i={3} className="border-alert/30">
      <div className="mb-4 flex items-center gap-2">
        <h2 className="text-lg font-semibold">Đơn cần soi</h2>
        
      </div>
      <ul className="flex flex-col gap-2">
        {a.dong_lech_luat.map(x => (
          <ReviewItem key={x.order_id + x.khoan} i={i++} platform={x.platform} title={x.order_id} tag="Lệch luật" tagClass="bg-alert-soft text-alert" desc={`${x.khoan} (${x.sku}): bị trừ ${vnd(x.thuc_tru)}, đúng luật ${vnd(x.dung_luat)}`} end={`thu dư ${vnd(x.chenh)}`} />
        ))}
        {a.phi_khac_khong_khop.map(x => (
          <ReviewItem key={x.order_id} i={i++} platform={x.platform} title={x.order_id} tag="Không khớp luật" tagClass="bg-alert-soft text-alert" desc={`"Phí khác" ${vnd(x.so_tien)} trên ${x.sku}: không có trong biểu phí`} />
        ))}
        {missingCogs.map(x => (
          <ReviewItem key={x.platform + x.sku} i={i++} platform={x.platform} title={x.sku} tag="Thiếu giá vốn" tagClass="bg-switch-soft text-[oklch(0.5_0.12_60)]" desc={`${x.don} đơn chưa tính được lãi. Bổ sung giá vốn trong file giá vốn.`} />
        ))}
      </ul>
    </Card>
  );
}

function SkuTable({rows}: {rows: SkuRow[]}) {
  return (
    <Card i={4}>
      <Title>Lãi mỗi đơn theo SKU</Title>
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
    </Card>
  );
}

function AdsTable({rows}: {rows: Analysis['quang_cao']}) {
  return (
    <Card i={5}>
      <Title hint="ROAS dưới mức hoà vốn thì quảng cáo đang lỗ.">Quảng cáo</Title>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Chiến dịch</TableHead>
            <TableHead>Sàn</TableHead>
            <TableHead className="text-right">Chi phí</TableHead>
            <TableHead className="text-right">ROAS</TableHead>
            <TableHead className="text-right">Hoà vốn</TableHead>
            <TableHead>Kết luận</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map(r => (
            <TableRow key={r.chien_dich}>
              <TableCell>{r.chien_dich}</TableCell>
              <TableCell>
                <PlatformPill platform={r.platform} />
              </TableCell>
              <TableCell className="text-right tabular">{vnd(r.chi_phi)}</TableCell>
              <TableCell className="text-right tabular">{r.roas}</TableCell>
              <TableCell className="text-right tabular">{r.roas_hoa_von}</TableCell>
              <TableCell>
                <Pill className={r.ket_luan === 'lỗ' ? 'bg-alert-soft text-alert' : 'bg-profit-soft text-profit'}>{r.ket_luan}</Pill>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function FilePick({label, multiple, onPick, files}: {label: string; multiple?: boolean; onPick: (f: File[]) => void; files: File[]}) {
  return (
    <label className="flex min-w-60 flex-1 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-input bg-background/60 px-4 py-3 text-sm hover:border-ink/40">
      <FileSpreadsheet className="size-5 text-profit" />
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{label}</span>
        <span className="block truncate text-sm text-muted-foreground">{files.length ? files.map(f => f.name).join(', ') : 'Chọn tệp .xlsx'}</span>
      </span>
      <input type="file" accept=".xlsx" multiple={multiple} className="sr-only" onChange={e => onPick(Array.from(e.target.files ?? []))} />
    </label>
  );
}

export default function ImportPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [cogsFile, setCogsFile] = useState<File | null>(null);
  const [data, setData] = useState<Analysis | null>(new URLSearchParams(window.location.search).has('demo') ? (demo as Analysis) : null);
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
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="h-full overflow-y-auto">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 p-6">
        <Card>
          <h1 className="text-2xl font-extrabold tracking-tight">Import file export tháng</h1>
          <p className="mt-1 text-base text-muted-foreground">Lãi từng sàn và các đơn cần soi.</p>
          <div className="mt-4 flex flex-wrap items-stretch gap-3">
            <FilePick label="File export đơn hàng (tối đa 3)" multiple files={files} onPick={f => setFiles(f.slice(0, 3))} />
            <FilePick label="File giá vốn" files={cogsFile ? [cogsFile] : []} onPick={f => setCogsFile(f[0] ?? null)} />
            <div className="flex items-center gap-2">
              <Button size="lg" disabled={!USE_API || files.length === 0 || isBusy} onClick={() => void upload()}>
                {isBusy ? <Loader2 className="animate-spin" /> : <Upload />} Phân tích
              </Button>
              <Button size="lg" variant="outline" onClick={() => setData(demo as Analysis)}>
                <Sparkles /> Bộ file demo tháng 11
              </Button>
            </div>
          </div>
                    {error && <p className="mt-3 rounded-lg bg-alert-soft px-3 py-2 text-sm text-alert">Chưa phân tích được: {error}</p>}
        </Card>

        {data && (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              {(Object.keys(data.theo_san) as Platform[]).map((p, i) => (
                <PlatformTile key={p} p={p} s={data.theo_san[p]} i={i} />
              ))}
            </div>
            <NeedsReview a={data} />
            <SkuTable rows={data.theo_sku_san} />
            <AdsTable rows={data.quang_cao} />
            <p className="px-1 text-sm text-muted-foreground">Lãi chưa trừ ship shop bù và đóng gói.</p>
          </>
        )}
      </div>
    </main>
  );
}
