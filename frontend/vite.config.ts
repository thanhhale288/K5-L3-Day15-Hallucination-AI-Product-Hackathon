import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

// Dev: /soi-don và /import chuyển sang API Python của Thái (TH-7, TH-11).
const api = process.env.API_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {'/soi-don': api, '/import': api},
  },
});
