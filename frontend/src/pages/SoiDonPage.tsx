// Màn chính (HA-6): dán đơn bên trái, hoá đơn đã soi bên phải.
import {useEffect, useState} from 'react';
import {useMediaQuery} from '@astryxdesign/core/hooks';
import {Layout, LayoutContent, LayoutPanel, VStack, HStack} from '@astryxdesign/core/Layout';
import {Text, Heading} from '@astryxdesign/core/Text';
import {TextArea} from '@astryxdesign/core/TextArea';
import {NumberInput} from '@astryxdesign/core/NumberInput';
import {Selector} from '@astryxdesign/core/Selector';
import {Button} from '@astryxdesign/core/Button';
import {Banner} from '@astryxdesign/core/Banner';
import {EmptyState} from '@astryxdesign/core/EmptyState';
import {Spinner} from '@astryxdesign/core/Spinner';
import {SAMPLES, SampleMissError, USE_API, loadSample, soiDon} from '../api';
import {isSession, type SoiResult} from '../types';
import {InvoiceView, type AskReply} from '../components/InvoiceView';
import {SessionView} from '../components/SessionView';

function PastePanel({
  text,
  setText,
  cogs,
  setCogs,
  sample,
  pickSample,
  onSubmit,
  isBusy,
}: {
  text: string;
  setText: (v: string) => void;
  cogs: number | null;
  setCogs: (v: number) => void;
  sample: string | null;
  pickSample: (file: string | null) => void;
  onSubmit: () => void;
  isBusy: boolean;
}) {
  return (
    <VStack gap={4}>
      <VStack gap={1}>
        <Heading level={2}>Dán đơn</Heading>
        <Text type="supporting">
          Dán "chi tiết thanh toán" của 1–5 đơn vừa về tiền, sàn nào cũng được (Shopee, TikTok Shop, Lazada).
        </Text>
      </VStack>
      <Selector
        label="Đơn mẫu"
        placeholder="Chọn một đơn mẫu…"
        options={SAMPLES.map(s => ({value: s.file, label: s.label}))}
        value={sample ?? undefined}
        onChange={v => pickSample(v)}
      />
      <TextArea
        label="Chi tiết thanh toán"
        value={text}
        onChange={setText}
        rows={14}
        placeholder={'[Shopee] Chi tiết thanh toán đơn …\nNgày đặt: …\nPhí cố định: -17.010đ\n…'}
      />
      <NumberInput
        label="Giá vốn mỗi sản phẩm"
        description="Không bắt buộc nếu chữ dán đã có giá vốn."
        value={cogs}
        onChange={setCogs}
        units="đ"
        min={0}
        isIntegerOnly
        isOptional
      />
      <Button label="Soi đơn" variant="primary" size="lg" isLoading={isBusy} isDisabled={!text.trim()} onClick={onSubmit} />
      <Text type="supporting" color="secondary">
        {USE_API
          ? 'Đang gọi agent thật qua API /soi-don.'
          : 'Chế độ mẫu: kết quả đọc từ file JSON mẫu (frontend/samples), chưa gọi agent.'}
      </Text>
    </VStack>
  );
}

export default function SoiDonPage() {
  const isNarrow = useMediaQuery('(max-width: 900px)', true);
  const [text, setText] = useState('');
  const [cogs, setCogs] = useState<number | null>(null);
  const [sample, setSample] = useState<string | null>(null);
  const [result, setResult] = useState<SoiResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setBusy] = useState(false);

  // ?mau=<file>: mở sẵn một mẫu (để demo và chụp màn hình).
  useEffect(() => {
    const file = new URLSearchParams(window.location.search).get('mau');
    const s = SAMPLES.find(x => x.file === file);
    if (s && !USE_API) {
      setSample(s.file);
      setText(s.paste ?? '');
      setResult(loadSample(s.file));
    }
  }, []);

  const pickSample = (file: string | null) => {
    setSample(file);
    const s = SAMPLES.find(x => x.file === file);
    setText(s?.paste ?? '');
    setResult(null);
    setError(null);
  };

  const run = async (extra?: AskReply) => {
    setBusy(true);
    setError(null);
    try {
      const sessionId = result && isSession(result) ? result.session_state_id : null;
      setResult(await soiDon({text, cogs: extra?.cogs ?? cogs, session_state_id: extra ? sessionId : null}));
    } catch (e) {
      setResult(null);
      setError(
        e instanceof SampleMissError
          ? 'Chế độ mẫu chỉ nhận các đơn mẫu. Chọn một đơn ở ô "Đơn mẫu", hoặc bật API để soi đơn bất kỳ.'
          : String(e),
      );
    } finally {
      setBusy(false);
    }
  };

  const answerAsk = (reply: AskReply) => {
    if (!USE_API) {
      setError('Chế độ mẫu không làm tiếp được sau câu hỏi. Khi nối API, agent sẽ tính tiếp với giá vốn bạn vừa nhập.');
      return;
    }
    void run(reply);
  };

  const panel = (
    <PastePanel
      text={text}
      setText={setText}
      cogs={cogs}
      setCogs={setCogs}
      sample={sample}
      pickSample={pickSample}
      onSubmit={() => void run()}
      isBusy={isBusy}
    />
  );

  const body = (
    <VStack gap={4}>
      {error && <Banner status="warning" title="Chưa soi được" description={error} collapsible={false} />}
      {isBusy && !result && (
        <HStack gap={2} vAlign="center">
          <Spinner size="sm" />
          <Text type="body">Agent đang tách dòng và tra luật…</Text>
        </HStack>
      )}
      {result &&
        (isSession(result) ? (
          <SessionView result={result} onAnswerAsk={answerAsk} isBusy={isBusy} />
        ) : (
          <InvoiceView result={result} onAnswerAsk={answerAsk} isBusy={isBusy} />
        ))}
      {!result && !error && !isBusy && (
        <EmptyState
          title="Chưa có đơn nào"
          description="Dán chi tiết thanh toán bên trái rồi bấm Soi đơn. Mỗi khoản trừ sẽ được gắn với luật phí của sàn tại ngày đặt đơn."
        />
      )}
    </VStack>
  );

  if (isNarrow) {
    return (
      <Layout
        height="auto"
        content={
          <LayoutContent role="main" padding={4}>
            <VStack gap={6}>
              {panel}
              {body}
            </VStack>
          </LayoutContent>
        }
      />
    );
  }

  return (
    <Layout
      height="fill"
      defaultHasDividers
      start={
        <LayoutPanel width={400} padding={4} role="complementary">
          {panel}
        </LayoutPanel>
      }
      content={
        <LayoutContent role="main" padding={4}>
          {body}
        </LayoutContent>
      }
    />
  );
}
