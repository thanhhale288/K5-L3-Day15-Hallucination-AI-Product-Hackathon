// SessionResult (dán nhiều đơn) → thẻ so sánh sàn + hoá đơn từng đơn.
import {useState} from 'react';
import {VStack, HStack, StackItem, Section} from '@astryxdesign/core/Layout';
import {Text, Heading} from '@astryxdesign/core/Text';
import {Badge} from '@astryxdesign/core/Badge';
import {Token} from '@astryxdesign/core/Token';
import {Table} from '@astryxdesign/core/Table';
import {TabList, Tab} from '@astryxdesign/core/TabList';
import {InfoTip} from '@astryxdesign/core/InfoTip';
import type {ComparisonRow, SessionResult} from '../types';
import {DECISION, PLATFORM, vnd} from '../format';
import {InvoiceView, type AskReply} from './InvoiceView';

function ComparisonCard({pc}: {pc: NonNullable<SessionResult['platform_comparison']>}) {
  const best = PLATFORM[pc.best_platform];
  return (
    <Section>
      <VStack gap={3}>
        <HStack gap={2} vAlign="center" wrap="wrap">
          <StackItem size="fill">
            <HStack gap={1} vAlign="center">
              <Heading level={2}>So sánh sàn · {pc.product}</Heading>
              <InfoTip content="Cùng một sản phẩm, lãi thật mỗi sản phẩm trên từng sàn. Tỉ lệ phí là bảng phí của nhóm, nhiều dòng còn là giả định." />
            </HStack>
          </StackItem>
          <Token label={`Lãi nhất: ${best.label}`} color="green" />
        </HStack>
        <Table<ComparisonRow>
          data={pc.rows}
          idKey="platform"
          columns={[
            {
              key: 'platform',
              header: 'Sàn',
              renderCell: r => (
                <HStack gap={2} vAlign="center">
                  <Token label={PLATFORM[r.platform].label} color={PLATFORM[r.platform].color} size="sm" />
                  {r.platform === pc.best_platform && <Badge variant="success" label="Lãi nhất" />}
                </HStack>
              ),
            },
            {key: 'payout', header: 'Tiền về', align: 'end', renderCell: r => vnd(r.payout)},
            {
              key: 'profit',
              header: 'Lãi thật / sp',
              align: 'end',
              renderCell: r => (
                <Text type="body" weight="semibold">
                  {vnd(r.profit_per_unit ?? r.profit)}
                </Text>
              ),
            },
            {key: 'top_switch', header: 'Công tắc ăn nhiều nhất', renderCell: r => r.top_switch ?? 'Không có'},
          ]}
        />
      </VStack>
    </Section>
  );
}

export function SessionView({
  result,
  onAnswerAsk,
  isBusy,
}: {
  result: SessionResult;
  onAnswerAsk?: (reply: AskReply) => void;
  isBusy?: boolean;
}) {
  const [tab, setTab] = useState(result.orders[0]?.order_id ?? '0');
  const current = result.orders.find(o => o.order_id === tab) ?? result.orders[0];
  const d = DECISION[result.decision];
  return (
    <VStack gap={4}>
      <HStack gap={2} vAlign="center">
        <StackItem size="fill">
          <Text type="large" weight="semibold">
            Đã soi {result.orders.length} đơn
          </Text>
        </StackItem>
        <Badge variant={d.variant} label={d.label} />
      </HStack>
      {result.platform_comparison && <ComparisonCard pc={result.platform_comparison} />}
      <TabList value={tab} onChange={setTab}>
        {result.orders.map(o => (
          <Tab
            key={o.order_id}
            value={o.order_id ?? ''}
            label={`${o.platform ? PLATFORM[o.platform].label : ''} · ${o.order_id}`}
          />
        ))}
      </TabList>
      {current && <InvoiceView result={current} onAnswerAsk={onAnswerAsk} isBusy={isBusy} />}
      {result.trace_id && (
        <Text type="supporting" color="secondary">
          Mã phiên: {result.session_state_id ?? '—'} · trace {result.trace_id}
        </Text>
      )}
    </VStack>
  );
}
