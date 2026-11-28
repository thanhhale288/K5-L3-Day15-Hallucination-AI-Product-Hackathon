// Màn import tháng (HA-14, demo bổ sung, ngoài lát cắt). Đọc JSON của data/import_export.py
// (qua POST /import của Thái — TH-11; chưa có API thì đọc frontend/samples/import-thang-11.json).
// Mục đích: chọn ra ĐƠN CẦN SOI, không phải báo cáo lãi tổng. Mọi số do code Python tính.
import {useState} from 'react';
import {Layout, LayoutContent, VStack, HStack, StackItem, Card, Section} from '@astryxdesign/core/Layout';
import {Grid} from '@astryxdesign/core/Grid';
import {Text, Heading} from '@astryxdesign/core/Text';
import {Badge} from '@astryxdesign/core/Badge';
import {Token} from '@astryxdesign/core/Token';
import {Table} from '@astryxdesign/core/Table';
import {Button} from '@astryxdesign/core/Button';
import {FileInput} from '@astryxdesign/core/FileInput';
import {Banner} from '@astryxdesign/core/Banner';
import {InfoTip} from '@astryxdesign/core/InfoTip';
import {List, ListItem} from '@astryxdesign/core/List';
import {MetadataList, MetadataListItem} from '@astryxdesign/core/MetadataList';
import type {Platform} from '../types';
import {PLATFORM, pct, vnd} from '../format';
const USE_API = import.meta.env.VITE_IMPORT_API === '1'; // POST /import của Thái (TH-11)
import demo from '../../samples/import-thang-11.json';

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

function PlatformTile({p, s}: {p: Platform; s: PlatformSummary}) {
  return (
    <Card padding={4}>
      <VStack gap={3}>
        <HStack gap={2} vAlign="center">
          <StackItem size="fill">
            <Token label={PLATFORM[p].label} color={PLATFORM[p].color} />
          </StackItem>
          <Text type="supporting">{s.don} đơn</Text>
        </HStack>
        <VStack gap={0.5}>
          <Text type="supporting">Lãi trước quảng cáo</Text>
          <Text type="display-3" weight="bold">
            {vnd(s.lai_truoc_qc)}
          </Text>
        </VStack>
        <MetadataList>
          <MetadataListItem label="Doanh thu">{vnd(s.doanh_thu)}</MetadataListItem>
          <MetadataListItem label="Phí sàn">
            {vnd(s.tong_phi)} · {pct(s.phi_tren_doanh_thu)} doanh thu
          </MetadataListItem>
          <MetadataListItem label="Tiền về">{vnd(s.tien_ve)}</MetadataListItem>
          <MetadataListItem label="Hoàn / huỷ">
            {s.hoan_hang} hoàn · {s.huy} huỷ
          </MetadataListItem>
        </MetadataList>
        {s.don_thieu_gia_von > 0 && <Badge variant="warning" label={`${s.don_thieu_gia_von} đơn thiếu giá vốn`} />}
      </VStack>
    </Card>
  );
}

function NeedsReview({a}: {a: Analysis}) {
  const missingCogs = a.theo_sku_san.filter(r => r.thieu_gia_von);
  const count = a.dong_lech_luat.length + a.phi_khac_khong_khop.length + missingCogs.length;
  return (
    <Section>
      <VStack gap={3}>
        <HStack gap={2} vAlign="center">
          <Heading level={2}>Đơn cần soi</Heading>
          <Badge variant="error" label={String(count)} />
        </HStack>
        <Text type="supporting">Đưa từng đơn vào màn Soi đơn để agent gắn luật và soạn nháp câu hỏi gửi sàn.</Text>
        <List density="spacious">
          {a.dong_lech_luat.map(x => (
            <ListItem
              key={x.order_id + x.khoan}
              label={
                <HStack gap={2} vAlign="center" wrap="wrap">
                  <Token label={PLATFORM[x.platform].label} color={PLATFORM[x.platform].color} size="sm" />
                  <Text type="body" weight="medium">
                    {x.order_id}
                  </Text>
                  <Token label="Lệch luật" color="red" size="sm" />
                </HStack>
              }
              description={`${x.khoan} (${x.sku}): bị trừ ${vnd(x.thuc_tru)}, đúng luật ${vnd(x.dung_luat)}`}
              endContent={<Text type="body" weight="semibold">thu dư {vnd(x.chenh)}</Text>}
            />
          ))}
          {a.phi_khac_khong_khop.map(x => (
            <ListItem
              key={x.order_id}
              label={
                <HStack gap={2} vAlign="center" wrap="wrap">
                  <Token label={PLATFORM[x.platform].label} color={PLATFORM[x.platform].color} size="sm" />
                  <Text type="body" weight="medium">
                    {x.order_id}
                  </Text>
                  <Token label="Không khớp luật" color="red" size="sm" />
                </HStack>
              }
              description={`"Phí khác" ${vnd(x.so_tien)} trên ${x.sku}: không có trong biểu phí`}
            />
          ))}
          {missingCogs.map(x => (
            <ListItem
              key={x.platform + x.sku}
              label={
                <HStack gap={2} vAlign="center" wrap="wrap">
                  <Token label={PLATFORM[x.platform].label} color={PLATFORM[x.platform].color} size="sm" />
                  <Text type="body" weight="medium">
                    {x.sku}
                  </Text>
                  <Token label="Thiếu giá vốn" color="yellow" size="sm" />
                </HStack>
              }
              description={`${x.don} đơn chưa tính được lãi. Bổ sung giá vốn trong file giá vốn.`}
            />
          ))}
        </List>
      </VStack>
    </Section>
  );
}

function SkuTable({rows}: {rows: SkuRow[]}) {
  return (
    <Section>
      <VStack gap={3}>
        <HStack gap={1} vAlign="center">
          <Heading level={2}>Lãi theo SKU và sàn</Heading>
          <InfoTip content="Lãi mỗi đơn trước quảng cáo. Cột cuối: công tắc ăn bao nhiêu phần lãi của SKU trên sàn đó." />
        </HStack>
        <Table<SkuRow>
          data={rows}
          idKey={r => `${r.platform}-${r.sku}`}
          density="compact"
          columns={[
            {key: 'sku', header: 'SKU'},
            {
              key: 'platform',
              header: 'Sàn',
              renderCell: r => <Token label={PLATFORM[r.platform].label} color={PLATFORM[r.platform].color} size="sm" />,
            },
            {key: 'don', header: 'Đơn', align: 'end'},
            {key: 'ti_le_hoan', header: 'Tỉ lệ hoàn', align: 'end', renderCell: r => pct(r.ti_le_hoan)},
            {
              key: 'lai_moi_don',
              header: 'Lãi / đơn',
              align: 'end',
              renderCell: r => (r.thieu_gia_von ? <Token label="Thiếu giá vốn" color="yellow" size="sm" /> : vnd(r.lai_moi_don)),
            },
            {key: 'cong_tac_lon_nhat', header: 'Công tắc lớn nhất', renderCell: r => r.cong_tac_lon_nhat ?? '—'},
            {
              key: 'ti_le_an_lai',
              header: 'Ăn lãi',
              align: 'end',
              renderCell: r =>
                r.ti_le_an_lai === null ? (
                  '—'
                ) : (
                  <Token label={pct(r.ti_le_an_lai)} color={r.ti_le_an_lai >= 0.5 ? 'red' : 'default'} size="sm" />
                ),
            },
          ]}
        />
      </VStack>
    </Section>
  );
}

function AdsTable({rows}: {rows: Analysis['quang_cao']}) {
  return (
    <Section>
      <VStack gap={3}>
        <HStack gap={1} vAlign="center">
          <Heading level={2}>Quảng cáo: ROAS so với hoà vốn</Heading>
          <InfoTip content="ROAS hoà vốn = 1 ÷ biên lãi trước quảng cáo. ROAS thấp hơn mức này thì phần doanh số do quảng cáo mang về đang lỗ." />
        </HStack>
        <Table
          data={rows}
          idKey="chien_dich"
          columns={[
            {key: 'chien_dich', header: 'Chiến dịch'},
            {
              key: 'platform',
              header: 'Sàn',
              renderCell: r => <Token label={PLATFORM[r.platform].label} color={PLATFORM[r.platform].color} size="sm" />,
            },
            {key: 'chi_phi', header: 'Chi phí', align: 'end', renderCell: r => vnd(r.chi_phi)},
            {key: 'roas', header: 'ROAS', align: 'end'},
            {key: 'roas_hoa_von', header: 'Hoà vốn', align: 'end'},
            {
              key: 'ket_luan',
              header: 'Kết luận',
              renderCell: r => <Badge variant={r.ket_luan === 'lỗ' ? 'error' : 'success'} label={r.ket_luan} />,
            },
          ]}
        />
      </VStack>
    </Section>
  );
}

export default function ImportPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [cogsFile, setCogsFile] = useState<File | null>(null);
  const [data, setData] = useState<Analysis | null>(
    new URLSearchParams(window.location.search).has('demo') ? (demo as Analysis) : null,
  );
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
    <Layout
      height="auto"
      contentWidth={1200}
      content={
        <LayoutContent role="main" padding={4}>
          <VStack gap={4}>
            <Section>
              <VStack gap={3}>
                <VStack gap={1}>
                  <Heading level={2}>Import file export tháng</Heading>
                  <Text type="supporting">
                    Tải file export đơn hàng của Shopee, TikTok Shop, Lazada và file giá vốn. Code tính lãi theo sàn, theo SKU
                    và lọc ra đơn cần soi. Đây là phần demo bổ sung, không thay luồng dán đơn.
                  </Text>
                </VStack>
                <HStack gap={3} vAlign="end" wrap="wrap">
                  <FileInput
                    label="File export đơn hàng (.xlsx)"
                    value={files}
                    onChange={f => setFiles(Array.isArray(f) ? f : f ? [f] : [])}
                    accept=".xlsx"
                    isMultiple
                    maxFiles={3}
                    width={320}
                  />
                  <FileInput
                    label="File giá vốn (.xlsx)"
                    value={cogsFile}
                    onChange={f => setCogsFile(Array.isArray(f) ? f[0] ?? null : f)}
                    accept=".xlsx"
                    width={260}
                  />
                  <Button
                    label="Phân tích"
                    variant="primary"
                    isLoading={isBusy}
                    isDisabled={!USE_API || files.length === 0}
                    onClick={() => void upload()}
                  />
                  <Button label="Dùng bộ file demo tháng 11" variant="secondary" onClick={() => setData(demo as Analysis)} />
                </HStack>
                {!USE_API && (
                  <Text type="supporting" color="secondary">
                    Chưa nối API /import: dùng nút "bộ file demo" (Shop Demo giả lập, chạy sẵn bằng data/import_export.py).
                  </Text>
                )}
              </VStack>
            </Section>

            {error && <Banner status="warning" title="Chưa phân tích được" description={error} collapsible={false} />}

            {data && (
              <>
                <Grid columns={{minWidth: 280, max: 3}} gap={4}>
                  {(Object.keys(data.theo_san) as Platform[]).map(p => (
                    <PlatformTile key={p} p={p} s={data.theo_san[p]} />
                  ))}
                </Grid>
                <NeedsReview a={data} />
                <SkuTable rows={data.theo_sku_san} />
                <AdsTable rows={data.quang_cao} />
                <Text type="supporting" color="secondary">
                  Bảng phí: {data.bang_phi}. Lãi chưa trừ ship shop bù, đóng gói và quảng cáo (trừ bảng quảng cáo).
                </Text>
              </>
            )}
          </VStack>
        </LayoutContent>
      }
    />
  );
}
