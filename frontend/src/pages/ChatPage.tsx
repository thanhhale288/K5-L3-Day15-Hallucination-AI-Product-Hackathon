// Màn chính: chat với agent "Lãi đi đâu?" qua AG-UI. Dựng từ template ai-chat của Astryx:
// cột chat bên trái (dán đơn, xem agent gọi công cụ), panel kết quả bên phải (hoá đơn, đề xuất, thao tác).
import {useEffect, useRef, useState} from 'react';
import {HStack, VStack, StackItem, Layout, LayoutContent} from '@astryxdesign/core/Layout';
import {Text, Heading} from '@astryxdesign/core/Text';
import {
  ChatComposer,
  ChatComposerInput,
  ChatLayout,
  ChatMessage,
  ChatMessageBubble,
  ChatMessageList,
  ChatSystemMessage,
  ChatToolCalls,
} from '@astryxdesign/core/Chat';
import {Avatar} from '@astryxdesign/core/Avatar';
import {Card} from '@astryxdesign/core/Card';
import {ClickableCard} from '@astryxdesign/core/ClickableCard';
import {Markdown} from '@astryxdesign/core/Markdown';
import {Button} from '@astryxdesign/core/Button';
import {Badge} from '@astryxdesign/core/Badge';
import {Banner} from '@astryxdesign/core/Banner';
import {Token} from '@astryxdesign/core/Token';
import {EmptyState} from '@astryxdesign/core/EmptyState';
import {Toolbar} from '@astryxdesign/core/Toolbar';
import {Dialog, DialogHeader} from '@astryxdesign/core/Dialog';
import {useResizable, ResizeHandle} from '@astryxdesign/core/Resizable';
import {VisuallyHidden} from '@astryxdesign/core/VisuallyHidden';
import {ScrollableArea} from '@astryxdesign/core/ScrollableArea';
import {useMediaQuery} from '@astryxdesign/core/hooks';
import {useLaiAgent, type Turn} from '../agent/useLaiAgent';
import {USE_BRIDGE, type Choice} from '../agent/laiAgent';
import {SAMPLES} from '../api';
import {isSession} from '../types';
import {DECISION, PLATFORM, vnd} from '../format';
import {InvoiceView, type InvoiceControls} from '../components/InvoiceView';
import {SessionView} from '../components/SessionView';

const MAX_PASTE_LINES = 10;

function PastedText({text}: {text: string}) {
  const lines = text.split('\n');
  const shown = lines.slice(0, MAX_PASTE_LINES);
  return (
    <VStack gap={0}>
      {shown.map((l, i) => (
        <Text key={i} type="body">
          {l || ' '}
        </Text>
      ))}
      {lines.length > MAX_PASTE_LINES && (
        <Text type="supporting" color="secondary">
          … thêm {lines.length - MAX_PASTE_LINES} dòng
        </Text>
      )}
    </VStack>
  );
}

function AssistantTurn({turn, onOpenResult}: {turn: Extract<Turn, {role: 'assistant'}>; onOpenResult?: () => void}) {
  return (
    <ChatMessage sender="assistant" avatar={<Avatar name="Lãi đi đâu" size="md" />}>
      {turn.steps.length > 0 && (
        <ChatMessageBubble variant="ghost">
          <VStack gap={0.5}>
            {turn.steps.map((s, i) => (
              <Text key={i} type="supporting" color="secondary">
                • {s}
              </Text>
            ))}
          </VStack>
        </ChatMessageBubble>
      )}
      {turn.calls.length > 0 && (
        <ChatToolCalls
          label={turn.isDone ? `Đã gọi ${turn.calls.length} công cụ` : `Đang gọi công cụ (${turn.calls.length})…`}
          calls={turn.calls.map(c => ({
            key: c.id,
            name: c.label,
            target: c.target,
            status: c.status === 'running' ? 'running' : c.status,
            errorMessage: c.status === 'error' ? c.result : undefined,
          }))}
        />
      )}
      {!turn.isDone && !turn.text && turn.calls.length === 0 && (
        <ChatMessageBubble variant="ghost">
          <Text type="supporting" color="secondary">
            Agent đang đọc chữ dán…
          </Text>
        </ChatMessageBubble>
      )}
      {turn.text && (
        <ChatMessageBubble variant="ghost">
          <Markdown density="compact">{turn.text}</Markdown>
        </ChatMessageBubble>
      )}
      {turn.error && (
        <Banner status="error" title="Agent gặp lỗi" description={turn.error} collapsible={false} />
      )}
      {turn.isDone && onOpenResult && (
        <ChatMessageBubble variant="ghost">
          <Button label="Xem kết quả" size="sm" variant="secondary" onClick={onOpenResult} />
        </ChatMessageBubble>
      )}
    </ChatMessage>
  );
}

function Suggestions({onPick}: {onPick: (paste: string, label: string) => void}) {
  return (
    <VStack gap={4} hAlign="center">
      <VStack gap={1} hAlign="center">
        <Heading level={2}>Dán chi tiết thanh toán, agent soi từng khoản trừ</Heading>
        <Text type="supporting">
          Shopee, TikTok Shop, Lazada · 1–5 đơn mỗi lần · agent gắn luật phí theo ngày đặt, chỉ công tắc ăn lãi, so sàn.
        </Text>
      </VStack>
      <VStack gap={2} hAlign="stretch">
        {SAMPLES.filter(s => s.paste).map(s => (
          <ClickableCard key={s.file} label={`Dán đơn mẫu: ${s.label}`} onClick={() => onPick(s.paste!, s.label)} padding={3}>
            <HStack gap={2} vAlign="center">
              <StackItem size="fill">
                <Text type="body">{s.label}</Text>
              </StackItem>
              <Token label="Dán thử" size="sm" />
            </HStack>
          </ClickableCard>
        ))}
      </VStack>
      <Text type="supporting" color="secondary">
        {USE_BRIDGE ? 'Đang nối agent thật qua AG-UI (/agent).' : 'Chế độ mẫu: phát lại kết quả đã tính sẵn, chưa gọi agent.'}
      </Text>
    </VStack>
  );
}

export default function ChatPage() {
  const {turns, state, isRunning, send, setLocal, note} = useLaiAgent();
  const isNarrow = useMediaQuery('(max-width: 900px)', true);
  const [isDialogOpen, setDialogOpen] = useState(false);
  const resize = useResizable({defaultSize: 600, minSize: 440, maxSize: 900, autoSaveId: 'lai-di-dau-panel'});
  const result = state.result ?? null;

  // ?mau=<file>: dán sẵn một đơn mẫu (để demo và chụp màn hình).
  const didPreset = useRef(false);
  useEffect(() => {
    if (didPreset.current) return;
    didPreset.current = true;
    const s = SAMPLES.find(x => x.file === new URLSearchParams(window.location.search).get('mau'));
    if (s?.paste) void send(s.paste);
  }, [send]);

  const controls: InvoiceControls = {
    switchInfo: state.switch_info,
    whatIf: state.what_if,
    canWhatIf: USE_BRIDGE,
    isBusy: isRunning,
    onWhatIf: (orderId, sw, rate) =>
      void send('', {type: 'what_if', order_id: orderId, switch: sw, new_rate: rate},
        rate ? `Thử đổi ${sw} sang ${rate}% ở đơn ${orderId}` : `Thử tắt ${sw} ở đơn ${orderId}`),
    decisions: state.decisions,
    onDecide: (orderId: string, text: string, choice: Choice) => {
      setLocal({decisions: {...state.decisions, [`${orderId}::${text}`]: choice}});
      note(choice === 'se_lam' ? `Bạn sẽ làm: ${text} (đơn ${orderId})` : `Bạn bỏ qua: ${text} (đơn ${orderId})`);
    },
    draftSent: state.draft_sent,
    onDraftSent: (orderId, isSent) => {
      setLocal({draft_sent: {...state.draft_sent, [orderId]: isSent}});
      note(isSent ? `Bạn đã tự gửi câu hỏi cho sàn về đơn ${orderId}` : `Bỏ đánh dấu đã gửi (đơn ${orderId})`);
    },
    onAnswerAsk: cogs => void send(`Giá vốn mỗi sản phẩm: ${vnd(cogs)}`),
  };

  const resultTitle = result
    ? isSession(result)
      ? `${result.orders.length} đơn · ${result.platform_comparison ? 'so sánh sàn' : 'nhiều đơn'}`
      : `${result.platform ? PLATFORM[result.platform].label : ''} · ${result.order_id ?? 'yêu cầu'}`
    : 'Chưa có đơn nào';

  const resultBody = result ? (
    isSession(result) ? <SessionView result={result} controls={controls} /> : <InvoiceView result={result} controls={controls} />
  ) : (
    <EmptyState title="Kết quả soi đơn hiện ở đây" description="Hoá đơn đã soi, công tắc ăn lãi, đề xuất của agent và nháp câu hỏi gửi sàn." />
  );

  const lastAssistant = [...turns].reverse().find(t => t.role === 'assistant');

  const chat = (
    <ChatLayout
      density="balanced"
      emptyState={<Suggestions onPick={paste => void send(paste)} />}
      composer={
        <ChatComposer
          onSubmit={v => v.trim() && void send(v.trim())}
          isDisabled={isRunning}
          placeholder="Dán chi tiết thanh toán của 1–5 đơn, hoặc trả lời câu hỏi của agent…"
          input={<ChatComposerInput pasteAsToken={false} maxRows={10} label="Tin nhắn cho agent" />}
          headerContext={
            state.model === 'fake' ? (
              <Token label="AI giả: chỉ đúng với DEMO-0412" color="yellow" size="sm" />
            ) : (
              <Text type="supporting" color="secondary">
                {USE_BRIDGE ? `Agent thật · AG-UI${state.model ? ` · ${state.model}` : ''}` : 'Chế độ mẫu'}
              </Text>
            )
          }
        />
      }>
      {turns.length > 0 && (
        <ChatMessageList isStreaming={isRunning}>
          {turns.map(t =>
            t.role === 'user' ? (
              <ChatMessage key={t.id} sender="user">
                <ChatMessageBubble>
                  <PastedText text={t.text} />
                </ChatMessageBubble>
              </ChatMessage>
            ) : t.role === 'system' ? (
              <ChatSystemMessage key={t.id}>{t.text}</ChatSystemMessage>
            ) : (
              <AssistantTurn
                key={t.id}
                turn={t}
                onOpenResult={isNarrow && result && t === lastAssistant ? () => setDialogOpen(true) : undefined}
              />
            ),
          )}
        </ChatMessageList>
      )}
    </ChatLayout>
  );

  const panelHeader = (
    <HStack gap={2} vAlign="center">
      <VStack gap={0}>
        <Text type="label" weight="semibold">
          Kết quả soi đơn
        </Text>
        <Text type="supporting" color="secondary">
          {resultTitle}
        </Text>
      </VStack>
      {result && <Badge variant={DECISION[result.decision].variant} label={DECISION[result.decision].label} />}
    </HStack>
  );

  return (
    <VStack height="100%">
      <Layout
        height="fill"
        content={
          <LayoutContent role="main" padding={0}>
            <VisuallyHidden as="h1">Chat soi đơn</VisuallyHidden>
            <HStack height="100%">
              <StackItem size="fill">
                <VStack height="100%">{chat}</VStack>
              </StackItem>
              {!isNarrow && (
                <>
                  <ResizeHandle direction="horizontal" resizable={resize.props} isReversed pillPlacement="start" hasDivider label="Kéo để đổi độ rộng panel kết quả" />
                  <StackItem>
                    <Card variant="transparent" height="100%" width={resize.size} padding={0}>
                      <VStack height="100%">
                        <Toolbar label="Kết quả soi đơn" dividers={['bottom']} startContent={panelHeader} />
                        <StackItem size="fill">
                          <ScrollableArea label="Kết quả soi đơn" height="100%" padding={4}>
                            {resultBody}
                          </ScrollableArea>
                        </StackItem>
                      </VStack>
                    </Card>
                  </StackItem>
                </>
              )}
            </HStack>
          </LayoutContent>
        }
      />
      <Dialog isOpen={isDialogOpen} onOpenChange={setDialogOpen} purpose="info" variant="fullscreen">
        <Layout
          header={<DialogHeader title="Kết quả soi đơn" subtitle={resultTitle} hasDivider onOpenChange={setDialogOpen} />}
          content={<LayoutContent padding={4}>{resultBody}</LayoutContent>}
        />
      </Dialog>
    </VStack>
  );
}
