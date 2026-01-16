import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 7000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://backend:7001',
        changeOrigin: true,
      },
    },
  },
})
