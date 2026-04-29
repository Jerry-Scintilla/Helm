import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    allowedHosts: ['develop.helm.dpdns.org'],
    proxy: {
      '/plugin-ui': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/plugin-sdk': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
