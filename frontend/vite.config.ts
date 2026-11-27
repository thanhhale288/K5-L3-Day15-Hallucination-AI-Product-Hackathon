import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

// Dev: /agent chuyển sang cầu AG-UI (frontend/agui/server.py); /import sang API của Thái (TH-11).
const api = process.env.API_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {'/agent': api, '/import': api},
  },
});
