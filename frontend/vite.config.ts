import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', restoreMocks: true,
    coverage: { provider: 'v8', include: ['src/api/**', 'src/features/**', 'src/app/**', 'src/components/**', 'src/lib/**'] } },
})
