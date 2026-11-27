import {useState} from 'react';
import {useMediaQuery} from '@astryxdesign/core/hooks';
import {AppShell} from '@astryxdesign/core/AppShell';
import {TopNav} from '@astryxdesign/core/TopNav';
import {HStack} from '@astryxdesign/core/Layout';
import {Heading, Text} from '@astryxdesign/core/Text';
import {SegmentedControl, SegmentedControlItem} from '@astryxdesign/core/SegmentedControl';
import ChatPage from './pages/ChatPage';
import ImportPage from './pages/ImportPage';

type View = 'soi-don' | 'import';

export default function App() {
  const [view, setView] = useState<View>(
    new URLSearchParams(window.location.search).get('view') === 'import' ? 'import' : 'soi-don',
  );
  const isNarrow = useMediaQuery('(max-width: 700px)', true);
  return (
    <AppShell
      topNav={
        <TopNav
          heading={
            <HStack gap={2} vAlign="center">
              {isNarrow ? (
                <Text type="large" weight="bold">
                  Lãi đi đâu?
                </Text>
              ) : (
                <Heading level={1}>Lãi đi đâu?</Heading>
              )}
              {!isNarrow && <Text type="supporting">Soi từng đơn trên Shopee · TikTok Shop · Lazada</Text>}
            </HStack>
          }
          endContent={
            <SegmentedControl label="Chọn màn" size={isNarrow ? 'sm' : 'md'} value={view} onChange={v => setView(v as View)}>
              <SegmentedControlItem value="soi-don" label={isNarrow ? 'Chat' : 'Chat soi đơn'} />
              <SegmentedControlItem value="import" label={isNarrow ? 'Import' : 'Import tháng'} />
            </SegmentedControl>
          }
        />
      }>
      {view === 'soi-don' ? <ChatPage /> : <ImportPage />}
    </AppShell>
  );
}
