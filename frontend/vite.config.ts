import path from 'node:path';
import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Dev: /agent và /import cùng chuyển sang cầu AG-UI (frontend/agui/server.py, cổng 8000; /import gọi
// import_files của Thái). Muốn dùng riêng API của Thái: IMPORT_TARGET=http://localhost:8001.
const api = process.env.API_TARGET ?? 'http://localhost:8000';
const importApi = process.env.IMPORT_TARGET ?? api;

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {alias: {'@': path.resolve(__dirname, './src')}},
  server: {
    port: 5173,
    proxy: {'/agent': api, '/import': importApi},
  },
});
