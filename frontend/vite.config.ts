import path from 'node:path';
import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Dev: /agent chuyển sang cầu AG-UI (frontend/agui/server.py, cổng 8000);
// /import sang API của Thái (`python codebase/app.py --serve --port 8001`, TH-11).
const api = process.env.API_TARGET ?? 'http://localhost:8000';
const importApi = process.env.IMPORT_TARGET ?? 'http://localhost:8001';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {alias: {'@': path.resolve(__dirname, './src')}},
  server: {
    port: 5173,
    proxy: {'/agent': api, '/import': importApi},
  },
});
