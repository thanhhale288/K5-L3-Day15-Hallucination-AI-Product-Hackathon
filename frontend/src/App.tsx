import {useState} from 'react';
import {AppShell} from '@astryxdesign/core/AppShell';
import {TopNav} from '@astryxdesign/core/TopNav';
import {HStack} from '@astryxdesign/core/Layout';
import {Heading, Text} from '@astryxdesign/core/Text';
import {SegmentedControl, SegmentedControlItem} from '@astryxdesign/core/SegmentedControl';
import SoiDonPage from './pages/SoiDonPage';
import ImportPage from './pages/ImportPage';

type View = 'soi-don' | 'import';

export default function App() {
  const [view, setView] = useState<View>(
    new URLSearchParams(window.location.search).get('view') === 'import' ? 'import' : 'soi-don',
  );
  return (
    <AppShell
      topNav={
        <TopNav
          heading={
            <HStack gap={2} vAlign="center">
              <Heading level={1}>Lãi đi đâu?</Heading>
              <Text type="supporting">Soi từng đơn trên Shopee · TikTok Shop · Lazada</Text>
            </HStack>
          }
          endContent={
            <SegmentedControl label="Chọn màn" value={view} onChange={v => setView(v as View)}>
              <SegmentedControlItem value="soi-don" label="Soi đơn" />
              <SegmentedControlItem value="import" label="Import tháng" />
            </SegmentedControl>
          }
        />
      }>
      {view === 'soi-don' ? <SoiDonPage /> : <ImportPage />}
    </AppShell>
  );
}
