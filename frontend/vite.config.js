import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0', // Permite acesso externo (útil para Docker)
    port: 5173,
    watch: {
      usePolling: true,
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
  }
});
