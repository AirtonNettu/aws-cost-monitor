import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    restoreMocks: true,
    testTimeout: 15000,
    coverage: {
      provider: 'v8',
      include: [
        'src/api/**',
        'src/features/**',
        'src/app/**',
        'src/components/**',
        'src/lib/**',
      ],
    },
  },
})
