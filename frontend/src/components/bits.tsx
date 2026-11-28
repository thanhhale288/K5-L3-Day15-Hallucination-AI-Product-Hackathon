// Mảnh giao diện dùng chung: số tiền lăn (NumberFlow), chip, chip sàn, chữ đậm kiểu **x** trong tóm tắt của agent.
import {useEffect, useState, type ReactNode} from 'react';
import NumberFlow from '@number-flow/react';
import {cn} from '@/lib/utils';
import type {Platform} from '@/types';
import {PLATFORM, vnd} from '@/format';

/** Số tiền từ JSON, lăn tới giá trị mới khi đổi. `from` = giá trị lúc mới hiện (để lăn khi vừa mở). */
export function Money({value, from, className}: {value: number | null | undefined; from?: number; className?: string}) {
  const [shown, setShown] = useState(from ?? value ?? 0);
  useEffect(() => {
    if (value === null || value === undefined) return;
    const t = setTimeout(() => setShown(value), 60);
    return () => clearTimeout(t);
  }, [value]);
  if (value === null || value === undefined) return <span className={className}>—</span>;
  return (
    <NumberFlow
      value={shown}
      locales="vi-VN"
      format={{signDisplay: 'auto'}}
      suffix="đ"
      className={cn('tabular', className)}
      aria-label={vnd(value)}
    />
  );
}

export function Pill({children, className}: {children: ReactNode; className?: string}) {
  return (
    <span className={cn('inline-flex h-7 items-center gap-1.5 rounded-full px-3 text-sm font-semibold whitespace-nowrap', className)}>
      {children}
    </span>
  );
}

export function PlatformPill({platform}: {platform: Platform}) {
  const p = PLATFORM[platform];
  return (
    <Pill className={p.chip}>
      <span className={cn('size-1.5 rounded-full', p.dot)} />
      {p.label}
    </Pill>
  );
}

/** Tóm tắt của agent chỉ dùng **đậm** và xuống dòng. */
export function RichText({text}: {text: string}) {
  return (
    <>
      {text.split('\n').map((line, i) => (
        <p key={i} className="min-h-[1em]">
          {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
            part.startsWith('**') && part.endsWith('**') ? (
              <strong key={j} className="font-semibold text-foreground">
                {part.slice(2, -2)}
              </strong>
            ) : (
              part
            ),
          )}
        </p>
      ))}
    </>
  );
}
