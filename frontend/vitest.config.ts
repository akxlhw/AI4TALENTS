import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // 允许读取仓库根的 CHANGELOG.md（构建期 ?raw 打包进更新日志）
  server: {
    fs: {
      allow: ['..'],
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    exclude: ['**/node_modules/**', '**/tests/**/*.spec.ts', '**/e2e/**'],
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
})
