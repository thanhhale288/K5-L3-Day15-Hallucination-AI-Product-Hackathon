import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import {Theme} from '@astryxdesign/core/theme';
import {InternationalizationProvider} from '@astryxdesign/core/i18n';
import viVN from '@astryxdesign/core/locales/vi-VN.generated.js';
import {themes, defaultThemeSlug} from './astryx-themes';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <InternationalizationProvider locale="vi-VN" messages={{'vi-VN': viVN}}>
      <Theme theme={themes[defaultThemeSlug as keyof typeof themes]}>
        <App />
      </Theme>
    </InternationalizationProvider>
  </StrictMode>,
);
