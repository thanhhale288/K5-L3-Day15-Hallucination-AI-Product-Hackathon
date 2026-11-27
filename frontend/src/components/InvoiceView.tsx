// Một AgentResult → hoá đơn đã soi. Chỉ đọc JSON, không tự tính số.
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
import type {AgentResult, Line} from '../types';
import {DECISION, LINE_TYPE, PLATFORM, ngay, pct, vnd} from '../format';

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
  const details: string[] = [];
  if (line.rule_id) details.push(`Luật ${line.rule_id}`);
  if (isOff) details.push(`Đúng luật: ${vnd(line.expected)} · lệch ${vnd(line.delta)}`);
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
          {details.map(d => (
            <Text key={d} type="supporting" color="secondary">
              {d}
            </Text>
          ))}
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

export interface AskReply {
  cogs: number;
}

export function InvoiceView({
  result,
  onAnswerAsk,
  isBusy,
}: {
  result: AgentResult;
  onAnswerAsk?: (reply: AskReply) => void;
  isBusy?: boolean;
}) {
  const showToast = useToast();
  const [cogs, setCogs] = useState<number | null>(null);
  const d = DECISION[result.decision];
  const p = result.platform ? PLATFORM[result.platform] : null;

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

  return (
    <VStack gap={4}>
      <Section>
        <VStack gap={4}>
          <HStack gap={2} vAlign="center" wrap="wrap">
            {p && <Token label={p.label} color={p.color} />}
            <StackItem size="fill">
              <Heading level={2}>Đơn {result.order_id}</Heading>
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
        <Banner status="warning" title="Cần bạn trả lời để tính tiếp" description={result.question} collapsible={false}>
          <HStack gap={2} vAlign="end" wrap="wrap">
            <NumberInput
              label="Giá vốn mỗi sản phẩm"
              value={cogs}
              onChange={setCogs}
              units="đ"
              min={0}
              isIntegerOnly
              width={220}
            />
            <Button
              label="Gửi và soi tiếp"
              variant="primary"
              isLoading={isBusy}
              isDisabled={!cogs}
              onClick={() => cogs && onAnswerAsk?.({cogs})}
            />
          </HStack>
        </Banner>
      )}

      {result.decision === 'escalate' && result.draft_to_platform && (
        <Banner
          status="error"
          title="Có khoản nên hỏi lại sàn"
          description="Agent chỉ soạn nháp, không tự gửi. Bạn đọc lại rồi tự gửi."
          collapsible={false}
          endContent={<Button label="Chép nháp" variant="secondary" size="sm" onClick={copyDraft} />}>
          <Text type="body">{result.draft_to_platform}</Text>
        </Banner>
      )}

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

      {result.switches.length > 0 && (
        <Section>
          <VStack gap={3}>
            <HStack gap={1} vAlign="center">
              <Heading level={3}>Công tắc đang ăn lãi</Heading>
              <InfoTip content="Phần trăm = số tiền công tắc ăn ÷ lãi thật của đơn. Trên 100% nghĩa là công tắc ăn nhiều hơn cả phần lãi còn lại." />
            </HStack>
            {result.switches.map(s => (
              <VStack key={s.name} gap={1}>
                <HStack gap={2}>
                  <StackItem size="fill">
                    <Text type="body">{s.name}</Text>
                  </StackItem>
                  <Text type="body" weight="semibold">
                    {vnd(s.amount)} · {pct(s.share_of_profit)} lãi
                  </Text>
                </HStack>
                <ProgressBar
                  label={`${s.name} ăn ${pct(s.share_of_profit)} lãi`}
                  value={Math.min(100, Math.round((s.share_of_profit ?? 0) * 100))}
                  variant={(s.share_of_profit ?? 0) >= 0.5 ? 'error' : 'warning'}
                  isLabelHidden
                />
              </VStack>
            ))}
          </VStack>
        </Section>
      )}

      {result.actions.length > 0 && (
        <Section>
          <VStack gap={2}>
            <Heading level={3}>Nên làm</Heading>
            <List>
              {result.actions.map(a => (
                <ListItem
                  key={a.text}
                  label={<Text type="body">{a.text}</Text>}
                  endContent={
                    a.gain_per_order !== null && (
                      <Token label={`+${vnd(a.gain_per_order)} / đơn`} color="green" />
                    )
                  }
                />
              ))}
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
