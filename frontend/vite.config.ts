import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [
    vue(),
    VueDevTools(),
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
        target: process.env.VITE_API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
      '/plugin-sdk': {
        target: process.env.VITE_API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
