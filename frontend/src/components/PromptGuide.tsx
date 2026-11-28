// Chỉ cho chủ shop biết phải nhắn gì: tin nhắn mẫu có chú thích từng phần, gợi ý điền sẵn vào ô chat, khung trống.
// Agent nhận: chữ dán chi tiết thanh toán (1–5 đơn, có thể kèm 1 câu yêu cầu) và câu trả lời khi agent hỏi (vd giá vốn).
// Câu hỏi tự do không kèm đơn thì agent không xử lý, nên không gợi ý kiểu đó.
import {motion} from 'motion/react';
import {BookOpenText, FileText, MessageCircleReply, PencilLine, Store} from 'lucide-react';
import {cn} from '@/lib/utils';
import {SAMPLES} from '@/api';
import {Button} from './ui/button';
import {Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger} from './ui/dialog';

export const BLANK_TEMPLATE = `[Shopee] Chi tiết thanh toán đơn <mã đơn>
Ngày đặt: <ngày/tháng/năm> · Shop thường · Ngành: <ngành hàng>
Sản phẩm: <tên sản phẩm> x1
Giá sản phẩm: <giá>đ
<Tên khoản phí 1>: -<số tiền>đ
<Tên khoản phí 2>: -<số tiền>đ
Doanh thu đơn hàng (tiền về): <số tiền>đ
Giá vốn: <số tiền>đ`;

export const SAMPLE_EXAMPLE = `Soi giúp mình đơn này, sao bị trừ nhiều vậy?
${SAMPLES.find(s => s.file === 'demo-0412.json')?.paste ?? ''}`;

type Part = {key: string; label: string; hint: string; dot: string};
const PARTS: Part[] = [
  {key: 'ask', label: 'Câu hỏi của bạn', hint: 'Tuỳ chọn, viết ở đầu hoặc cuối', dot: 'bg-profit'},
  {key: 'head', label: 'Sàn và mã đơn', hint: 'Dòng tiêu đề, giữ nguyên tên sàn', dot: 'bg-ink'},
  {key: 'date', label: 'Ngày đặt, loại shop, ngành', hint: 'Để tra đúng biểu phí lúc đặt đơn', dot: 'bg-lazada'},
  {key: 'price', label: 'Sản phẩm và giá bán', hint: '', dot: 'bg-tiktok'},
  {key: 'fee', label: 'Các khoản bị trừ', hint: 'Dán đủ, đúng như sàn ghi', dot: 'bg-alert'},
  {key: 'payout', label: 'Tiền về', hint: 'Số sàn trả cho bạn', dot: 'bg-ink'},
  {key: 'cogs', label: 'Giá vốn', hint: 'Bạn tự thêm. Thiếu thì agent sẽ hỏi', dot: 'bg-switch'},
];

function partOf(line: string, i: number): string {
  if (/^\[(Shopee|TikTok Shop|Lazada)\]|^Chi tiết|^Quyết toán/i.test(line)) return 'head';
  if (/^Ngày đặt/i.test(line)) return 'date';
  if (/^Giá vốn/i.test(line)) return 'cogs';
  if (/tiền về|Số tiền thanh toán|Số tiền quyết toán/i.test(line)) return 'payout';
  if (/:\s*-[\d.]+đ\s*$/.test(line)) return 'fee';
  if (/^(Sản phẩm|Giá|Tổng phụ)/i.test(line)) return 'price';
  return i === 0 || !line.includes(':') ? 'ask' : 'price';
}

/** Tin nhắn mẫu, mỗi phần có chấm màu và chú thích ở dòng đầu của phần đó. */
export function AnnotatedExample({compact}: {compact?: boolean}) {
  const lines = SAMPLE_EXAMPLE.split('\n');
  const parts = lines.map(partOf);
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card">
      {lines.map((line, i) => {
        const p = PARTS.find(x => x.key === parts[i])!;
        const isFirst = parts[i - 1] !== parts[i];
        return (
          <motion.div
            key={i}
            initial={{opacity: 0, x: -6}}
            animate={{opacity: 1, x: 0}}
            transition={{delay: 0.05 + i * 0.035}}
            className={cn('grid items-center gap-3 px-4', compact ? 'grid-cols-[1fr]' : 'grid-cols-[minmax(0,1fr)_14rem]', isFirst && i > 0 && 'border-t border-dashed border-border')}>
            <div className="flex min-w-0 items-center gap-2.5 py-1">
              <span className={cn('h-5 w-1 shrink-0 rounded-full', p.dot)} />
              <span className={cn('truncate font-mono text-sm', p.key === 'ask' ? 'font-sans text-base font-medium' : 'text-foreground/85')}>{line}</span>
            </div>
            {!compact && (
              <div className="py-1 text-right">
                {isFirst && (
                  <>
                    <div className="text-sm font-semibold">{p.label}</div>
                    {p.hint && <div className="text-xs text-muted-foreground">{p.hint}</div>}
                  </>
                )}
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

export function PromptHelpDialog({onUse}: {onUse: (text: string) => void}) {
  return (
    <Dialog>
      <DialogTrigger render={<Button variant="ghost" size="sm" className="text-sm text-muted-foreground" />}>
        <BookOpenText /> Cách viết tin nhắn
      </DialogTrigger>
      <DialogContent className="max-w-3xl sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="text-xl">Nhắn cho agent thế nào?</DialogTitle>
          <DialogDescription className="text-base">
            Mở trang chi tiết thanh toán (hoặc quyết toán) của đơn trong Seller Center, chép toàn bộ rồi dán vào ô chat. Thêm dòng giá vốn nếu sàn không ghi. Mỗi lần 1–5 đơn, khác sàn cũng được.
          </DialogDescription>
        </DialogHeader>
        <AnnotatedExample />
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-xl bg-muted/60 p-3">
            <div className="font-semibold">Agent làm được</div>
            <ul className="mt-1 list-disc pl-5 text-muted-foreground">
              <li>Soi 1 đơn hoặc 2–5 đơn một lúc</li>
              <li>So sàn khi dán cùng sản phẩm ở nhiều sàn</li>
              <li>Hỏi lại khi thiếu giá vốn, bạn trả lời là đi tiếp</li>
            </ul>
          </div>
          <div className="rounded-xl bg-muted/60 p-3">
            <div className="font-semibold">Agent không làm</div>
            <ul className="mt-1 list-disc pl-5 text-muted-foreground">
              <li>Trả lời câu hỏi không kèm chi tiết đơn</li>
              <li>Gợi ý né phí, né thuế, buff đơn</li>
              <li>Tự gửi gì cho sàn hay tự tắt chương trình</li>
            </ul>
          </div>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="outline" size="lg" className="text-base" onClick={() => onUse(BLANK_TEMPLATE)}>
            <PencilLine /> Dùng khung trống
          </Button>
          <Button size="lg" className="text-base" onClick={() => onUse(SAMPLE_EXAMPLE)}>
            <FileText /> Dùng tin nhắn mẫu
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export type Starter = {label: string; text: string; icon: typeof FileText; caret?: 'end'};

/** Gợi ý điền sẵn vào ô chat, đổi theo tình huống. */
export function starters(mode: 'start' | 'ask' | 'after'): Starter[] {
  const sample = (f: string) => SAMPLES.find(s => s.file === f)?.paste ?? '';
  if (mode === 'ask') return [{label: 'Trả lời giá vốn', text: 'Giá vốn mỗi sản phẩm: ', icon: MessageCircleReply, caret: 'end'}];
  if (mode === 'after')
    return [
      {label: 'Khung trống cho đơn khác', text: BLANK_TEMPLATE, icon: PencilLine},
      {label: 'Mẫu: cùng sản phẩm 3 sàn', text: sample('session-3-san.json'), icon: Store},
    ];
  return [
    {label: 'Mẫu: 1 đơn Shopee', text: SAMPLE_EXAMPLE, icon: FileText},
    {label: 'Mẫu: cùng sản phẩm 3 sàn', text: sample('session-3-san.json'), icon: Store},
    {label: 'Khung trống để tự điền', text: BLANK_TEMPLATE, icon: PencilLine},
  ];
}
