// Một AgentResult → hoá đơn đã soi + chỗ để chủ shop thao tác trên đề xuất.
// Chỉ đọc số trong JSON của agent (và kết quả what-if do bridge gọi tools.py). Không tự tính số.
import {useState} from 'react';
import {VStack, HStack, StackItem, Card, Section} from '@astryxdesign/core/Layout';
import {Text, Heading} from '@astryxdesign/core/Text';
import {Badge} from '@astryxdesign/core/Badge';
import {Token} from '@astryxdesign/core/Token';
import {Banner} from '@astryxdesign/core/Banner';
import {Button} from '@astryxdesign/core/Button';
import {Link} from '@astryxdesign/core/Link';
import {List, ListItem} from '@astryxdesign/core/List';
import {ProgressBar} from '@astryxdesign/core/ProgressBar';
import {InfoTip} from '@astryxdesign/core/InfoTip';
import {NumberInput} from '@astryxdesign/core/NumberInput';
import {Divider} from '@astryxdesign/core/Divider';
import {useToast} from '@astryxdesign/core/Toast';
import type {AgentResult, Line, Switch} from '../types';
import type {Choice, SwitchInfo, WhatIf} from '../agent/laiAgent';
import {DECISION, LINE_TYPE, PLATFORM, ngay, pct, vnd} from '../format';

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

function Stat({label, value, tip, isStrong}: {label: string; value: string; tip?: string; isStrong?: boolean}) {
  return (
    <VStack gap={0.5}>
      <HStack gap={1} vAlign="center">
        <Text type="supporting">{label}</Text>
        {tip && <InfoTip content={tip} size="xsm" />}
      </HStack>
      <Text type={isStrong ? 'display-3' : 'large'} weight={isStrong ? 'bold' : 'semibold'}>
        {value}
      </Text>
    </VStack>
  );
}

function LineRow({line}: {line: Line}) {
  const t = LINE_TYPE[line.type];
  const isOff = line.delta !== null && line.delta !== 0;
  return (
    <ListItem
      label={
        <HStack gap={2} vAlign="center" wrap="wrap">
          <Text type="body" weight="medium">
            {line.name}
          </Text>
          <Token label={t.label} color={t.color} size="sm" description={t.tip} />
          {isOff && <Token label="Lệch luật" color="red" size="sm" />}
        </HStack>
      }
      description={
        <VStack gap={0}>
          {line.rule_id && (
            <Text type="supporting" color="secondary">
              Luật {line.rule_id}
            </Text>
          )}
          {isOff && (
            <Text type="supporting" color="secondary">
              Đúng luật: {vnd(line.expected)} · lệch {vnd(line.delta)}
            </Text>
          )}
          {line.type === 'khong_khop' && (
            <Text type="supporting" color="secondary">
              {t.tip}
            </Text>
          )}
          {line.source_url && (
            <Text type="supporting">
              <Link href={line.source_url} target="_blank" type="supporting">
                Nguồn{line.chunk_id ? ` · ${line.chunk_id}` : ''}
              </Link>
            </Text>
          )}
        </VStack>
      }
      endContent={
        <Text type="body" weight="semibold">
          {vnd(line.amount)}
        </Text>
      }
    />
  );
}

function SwitchRow({
  sw,
  orderId,
  info,
  tried,
  controls,
}: {
  sw: Switch;
  orderId: string;
  info?: SwitchInfo;
  tried?: WhatIf;
  controls: InvoiceControls;
}) {
  const [rate, setRate] = useState<number | null>(null);
  const share = sw.share_of_profit ?? 0;
  const canTry = Boolean(controls.canWhatIf && controls.onWhatIf);
  return (
    <VStack gap={1.5}>
      <HStack gap={2}>
        <StackItem size="fill">
          <Text type="body" weight="medium">
            {sw.name}
          </Text>
        </StackItem>
        <Text type="body" weight="semibold">
          {vnd(sw.amount)} · {pct(sw.share_of_profit)} lãi
        </Text>
      </HStack>
      <ProgressBar
        label={`${sw.name} ăn ${pct(sw.share_of_profit)} lãi`}
        value={Math.min(100, Math.round(share * 100))}
        variant={share >= 0.5 ? 'error' : 'warning'}
        isLabelHidden
      />
      <HStack gap={2} vAlign="end" wrap="wrap">
        {info?.can_change_rate && (
          <NumberInput
            label={`Tỉ lệ mới (hiện ~${info.current_rate ?? '—'}%)`}
            value={rate}
            onChange={setRate}
            units="%"
            min={0}
            max={100}
            step={0.5}
            size="sm"
            width={190}
            isDisabled={!canTry}
          />
        )}
        {info?.can_change_rate && (
          <Button
            label="Thử tỉ lệ này"
            size="sm"
            variant="secondary"
            isDisabled={!canTry || rate === null || controls.isBusy}
            onClick={() => rate !== null && controls.onWhatIf?.(orderId, sw.name, rate)}
          />
        )}
        <Button
          label="Thử tắt"
          size="sm"
          variant="ghost"
          isDisabled={!canTry || controls.isBusy}
          onClick={() => controls.onWhatIf?.(orderId, sw.name, 0)}
        />
      </HStack>
      {!controls.canWhatIf && (
        <Text type="supporting" color="secondary">
          Thử đổi công tắc cần bridge (chạy tools.py thật).
        </Text>
      )}
      {tried && (
        <Card variant="muted" padding={2}>
          <Text type="supporting">
            {tried.new_rate ? `Đổi sang ${tried.new_rate}%` : 'Tắt'}: lãi mỗi đơn {vnd(tried.profit_after)}{' '}
            <Text type="supporting" weight="semibold">
              (+{vnd(tried.gain_per_order)})
            </Text>
            {tried.max_order_drop_pct !== null && ` · số đơn được giảm tối đa ${Math.round(tried.max_order_drop_pct)}% mà vẫn có lợi`}
          </Text>
        </Card>
      )}
    </VStack>
  );
}

export function InvoiceView({result, controls = {}}: {result: AgentResult; controls?: InvoiceControls}) {
  const showToast = useToast();
  const [cogs, setCogs] = useState<number | null>(null);
  const d = DECISION[result.decision];
  const p = result.platform ? PLATFORM[result.platform] : null;
  const oid = result.order_id ?? '';

  if (result.decision === 'refuse') {
    return (
      <Banner status="info" title="Mình không hỗ trợ yêu cầu này" description={result.refusal_reason} collapsible={false} />
    );
  }

  const copyDraft = async () => {
    if (!result.draft_to_platform) return;
    await navigator.clipboard.writeText(result.draft_to_platform);
    showToast({body: 'Đã chép nháp. Bạn tự dán vào kênh hỗ trợ người bán của sàn.', uniqueID: 'copy-draft'});
  };
  const isSent = Boolean(controls.draftSent?.[oid]);

  return (
    <VStack gap={4}>
      <Section>
        <VStack gap={4}>
          <HStack gap={2} vAlign="center" wrap="wrap">
            {p && <Token label={p.label} color={p.color} />}
            <StackItem size="fill">
              <Heading level={2}>Đơn {result.order_id ?? '—'}</Heading>
            </StackItem>
            <Badge variant={d.variant} label={d.label} />
          </HStack>
          <Text type="supporting">
            Đặt ngày {ngay(result.order_date)} · {d.hint}
          </Text>
          <Card variant="muted" padding={4}>
            <HStack gap={8} wrap="wrap">
              <Stat label="Tiền về" value={vnd(result.payout)} tip="Số tiền sàn ghi trên chi tiết thanh toán." />
              <Stat label="Giá vốn" value={vnd(result.cogs)} />
              <Stat
                label="Lãi thật mỗi đơn"
                value={vnd(result.profit)}
                tip="Tiền về trừ giá vốn. Chưa trừ ship shop bù, đóng gói, quảng cáo."
                isStrong
              />
            </HStack>
          </Card>
        </VStack>
      </Section>

      {result.decision === 'ask' && result.question && (
        <Banner status="warning" title="Agent cần bạn trả lời để tính tiếp" description={result.question} collapsible={false}>
          <HStack gap={2} vAlign="end" wrap="wrap">
            <NumberInput label="Giá vốn mỗi sản phẩm" value={cogs} onChange={setCogs} units="đ" min={0} isIntegerOnly width={220} />
            <Button
              label="Gửi và soi tiếp"
              variant="primary"
              isLoading={controls.isBusy}
              isDisabled={!cogs || !controls.onAnswerAsk}
              onClick={() => cogs && controls.onAnswerAsk?.(cogs)}
            />
          </HStack>
        </Banner>
      )}

      {result.decision === 'escalate' && result.draft_to_platform && (
        <Banner
          status={isSent ? 'success' : 'error'}
          title={isSent ? 'Bạn đã tự gửi câu hỏi cho sàn' : 'Có khoản nên hỏi lại sàn'}
          description="Agent chỉ soạn nháp, không tự gửi. Bạn đọc lại rồi tự gửi qua kênh hỗ trợ người bán."
          collapsible={false}
          endContent={
            <HStack gap={2}>
              <Button label="Chép nháp" variant="secondary" size="sm" onClick={() => void copyDraft()} />
              {controls.onDraftSent && (
                <Button
                  label={isSent ? 'Bỏ đánh dấu' : 'Đã tự gửi'}
                  variant="ghost"
                  size="sm"
                  onClick={() => controls.onDraftSent?.(oid, !isSent)}
                />
              )}
            </HStack>
          }>
          <Text type="body">{result.draft_to_platform}</Text>
        </Banner>
      )}

      {result.lines.length > 0 && (
        <Section>
          <VStack gap={2}>
            <HStack gap={2} vAlign="center">
              <Heading level={3}>Các khoản bị trừ</Heading>
              <Badge label={String(result.lines.length)} />
            </HStack>
            <List density="spacious">
              {result.lines.map((ln, i) => (
                <LineRow key={`${ln.name}-${i}`} line={ln} />
              ))}
            </List>
          </VStack>
        </Section>
      )}

      {result.switches.length > 0 && (
        <Section>
          <VStack gap={4}>
            <HStack gap={1} vAlign="center">
              <Heading level={3}>Công tắc đang ăn lãi</Heading>
              <InfoTip content="Phần trăm = số tiền công tắc ăn ÷ lãi thật của đơn. Thử đổi tỉ lệ hoặc tắt: bridge gọi expected_amount và switch_what_if của tools.py, không qua AI." />
            </HStack>
            {result.switches.map(s => (
              <SwitchRow
                key={s.name}
                sw={s}
                orderId={oid}
                info={controls.switchInfo?.find(x => x.order_id === oid && x.switch === s.name)}
                tried={controls.whatIf?.find(x => x.order_id === oid && x.switch === s.name)}
                controls={controls}
              />
            ))}
          </VStack>
        </Section>
      )}

      {result.actions.length > 0 && (
        <Section>
          <VStack gap={2}>
            <Heading level={3}>Agent đề xuất</Heading>
            <List>
              {result.actions.map(a => {
                const choice = controls.decisions?.[`${oid}::${a.text}`];
                return (
                  <ListItem
                    key={a.text}
                    label={
                      <HStack gap={2} vAlign="center" wrap="wrap">
                        <Text type="body">{a.text}</Text>
                        {a.gain_per_order !== null && <Token label={`+${vnd(a.gain_per_order)} / đơn`} color="green" size="sm" />}
                      </HStack>
                    }
                    description={
                      choice ? (
                        <Text type="supporting" color="secondary">
                          {choice === 'se_lam' ? 'Bạn chọn: sẽ làm trên sàn' : 'Bạn chọn: bỏ qua'}
                        </Text>
                      ) : undefined
                    }
                    endContent={
                      controls.onDecide && (
                        <HStack gap={1}>
                          <Button
                            label="Sẽ làm"
                            size="sm"
                            variant={choice === 'se_lam' ? 'primary' : 'secondary'}
                            onClick={() => controls.onDecide?.(oid, a.text, 'se_lam')}
                          />
                          <Button
                            label="Bỏ qua"
                            size="sm"
                            variant={choice === 'bo_qua' ? 'primary' : 'ghost'}
                            onClick={() => controls.onDecide?.(oid, a.text, 'bo_qua')}
                          />
                        </HStack>
                      )
                    }
                  />
                );
              })}
            </List>
            <Divider />
            <Text type="supporting">
              Bạn là người bấm thật trên trang quản lý của sàn. Agent không tự tắt hay chỉnh chương trình nào.
            </Text>
          </VStack>
        </Section>
      )}

      {result.trace_id && (
        <Text type="supporting" color="secondary">
          Mã trace: {result.trace_id}
        </Text>
      )}
    </VStack>
  );
}
