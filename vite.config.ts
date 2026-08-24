import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './resources/js'),
    },
  },
  server: {
    port: 5173,
    host: true,
    watch: {
      usePolling: true,
      interval: 300,
      ignored: ['**/tests/**', '**/storage/**', '**/workers/**', '**/.git/**', '**/*.md'],
    },
    proxy: {
      '/api': {
        target: 'http://localhost/SheetTools/api.php',
        changeOrigin: true,
      },
    },
  },
});

