// PolicyAnswer (hỏi đáp chính sách, không kèm đơn): câu trả lời + các đoạn chính sách đã trích.
// Câu trả lời chỉ dựa trên các đoạn này; agent đã kiểm mọi con số trong câu trả lời có trong đoạn trích.
import {motion} from 'motion/react';
import {BookOpenText, ExternalLink, MessageSquareText} from 'lucide-react';
import type {PolicyAnswer} from '@/types';
import {ngay} from '@/format';
import {PlatformPill, RichText} from './bits';

export function PolicyView({result}: {result: PolicyAnswer}) {
  return (
    <div className="flex flex-col gap-4">
      <motion.section initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} className="rounded-2xl border border-border bg-card p-6">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <BookOpenText className="size-5 text-profit" /> Trả lời từ kho chính sách
        </h3>
        <div className="mt-3 flex flex-col gap-2 text-base leading-relaxed text-foreground/90">
          <RichText text={result.answer} />
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          {result.citations.length
            ? 'Agent chỉ trả lời từ các đoạn dưới đây; con số đã kiểm khớp với đoạn trích. Chính sách có thể đã đổi, mở nguồn để xem bản mới nhất.'
            : 'Không có đoạn chính sách nào khớp câu hỏi trong kho của nhóm.'}
        </p>
      </motion.section>

      {result.citations.length > 0 && (
        <motion.section initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={{delay: 0.1}} className="rounded-2xl border border-border bg-card p-5">
          <h3 className="mb-3 text-lg font-semibold">Nguồn ({result.citations.length} đoạn)</h3>
          <ul className="flex flex-col gap-2">
            {result.citations.map((c, i) => (
              <motion.li
                key={c.chunk_id}
                initial={{opacity: 0, x: -6}}
                animate={{opacity: 1, x: 0}}
                transition={{delay: 0.15 + i * 0.05}}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-border bg-background/60 px-4 py-3">
                <PlatformPill platform={c.platform} />
                <span className="font-mono text-sm">{c.chunk_id}</span>
                {c.effective_date && <span className="text-sm text-muted-foreground">hiệu lực {ngay(String(c.effective_date).slice(0, 10))}</span>}
                {c.url && (
                  <a href={c.url} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-sm font-medium text-profit hover:underline">
                    Mở nguồn <ExternalLink className="size-3.5" />
                  </a>
                )}
              </motion.li>
            ))}
          </ul>
        </motion.section>
      )}

      <p className="flex items-center gap-2 px-1 text-sm text-muted-foreground">
        <MessageSquareText className="size-4" /> Muốn biết một đơn cụ thể bị trừ đúng không: dán chi tiết thanh toán của đơn đó vào ô chat.
      </p>
    </div>
  );
}
