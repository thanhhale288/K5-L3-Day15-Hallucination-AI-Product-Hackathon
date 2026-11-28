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
  {key: 'ask', label: 'Câu hỏi (tuỳ chọn)', hint: 'Viết ở đầu hoặc cuối', dot: 'bg-profit'},
  {key: 'head', label: 'Sàn và mã đơn', hint: 'Dòng tiêu đề, giữ nguyên tên sàn', dot: 'bg-ink'},
  {key: 'date', label: 'Ngày đặt', hint: 'Để tra đúng biểu phí lúc đặt đơn', dot: 'bg-lazada'},
  {key: 'price', label: 'Giá bán', hint: '', dot: 'bg-tiktok'},
  {key: 'fee', label: 'Các khoản bị trừ', hint: 'Dán đủ, đúng như sàn ghi', dot: 'bg-alert'},
  {key: 'payout', label: 'Tiền về', hint: 'Số sàn trả cho bạn', dot: 'bg-ink'},
  {key: 'cogs', label: 'Giá vốn (tự thêm)', hint: 'Thiếu thì agent sẽ hỏi', dot: 'bg-switch'},
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

const SHOWN_FEES = 3;

/** Tin nhắn mẫu, mỗi phần có vạch màu và nhãn ở dòng đầu của phần đó.
 *  compact: thu các khoản phí còn 3 dòng, chỉ nhãn ngắn (dùng ở panel trống); đầy đủ có lời giải thích (dùng trong hộp hướng dẫn). */
export function AnnotatedExample({compact}: {compact?: boolean}) {
  const all = SAMPLE_EXAMPLE.split('\n').map((line, i) => ({line, part: partOf(line, i)}));
  const fees = all.filter(x => x.part === 'fee').length;
  let seenFees = 0;
  const rows: {line: string; part: string; more?: number}[] = [];
  for (const x of all) {
    if (compact && x.part === 'fee' && ++seenFees > SHOWN_FEES) {
      if (seenFees === SHOWN_FEES + 1) rows.push({line: `… ${fees - SHOWN_FEES} khoản nữa`, part: 'fee', more: fees - SHOWN_FEES});
      continue;
    }
    rows.push(x);
  }
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card py-1">
      {rows.map((r, i) => {
        const p = PARTS.find(x => x.key === r.part)!;
        const isFirst = rows[i - 1]?.part !== r.part;
        return (
          <motion.div
            key={i}
            initial={{opacity: 0, x: -6}}
            animate={{opacity: 1, x: 0}}
            transition={{delay: 0.05 + i * 0.035}}
            className={cn('grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4', isFirst && i > 0 && 'mt-1 border-t border-dashed border-border pt-1')}>
            <div className="flex min-w-0 items-center gap-2.5 py-0.5">
              <span className={cn('h-5 w-1 shrink-0 rounded-full', p.dot)} />
              <span className={cn('truncate text-sm', r.part === 'ask' ? 'text-base font-medium' : 'font-mono text-foreground/85', r.more && 'font-sans text-muted-foreground italic')}>{r.line}</span>
            </div>
            <div className="py-0.5 text-right">
              {isFirst && <div className={cn('text-sm', compact ? 'text-muted-foreground' : 'font-semibold')}>{p.label}</div>}
              {isFirst && !compact && p.hint && <div className="text-xs text-muted-foreground">{p.hint}</div>}
            </div>
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
  // Lúc đầu cột chat đã có danh sách đơn mẫu, nên ở đây chỉ còn khung trống.
  return [{label: 'Khung trống để tự điền', text: BLANK_TEMPLATE, icon: PencilLine}];
}
