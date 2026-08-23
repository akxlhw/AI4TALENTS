import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 2012,
    strictPort: true,  // 固化端口，如果被占用则报错而不是切换端口
    host: true,
    // 允许读取仓库根的 CHANGELOG.md（构建期 ?raw 打包进更新日志）
    fs: {
      allow: ['..'],
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    // antd / echarts cores are single-package vendor libraries (~1.1MB / ~0.9MB
    // minified); they are isolated into cacheable vendor-* chunks below, so the
    // warning is raised to cover them while still flagging oversized APP code.
    chunkSizeWarningLimit: 1200,
    rolldownOptions: {
      output: {
        // Vendor manual chunking (rolldown codeSplitting groups): split the
        // monolithic index chunk into cacheable per-library vendor chunks.
        // Use [\\/] in regexes so paths match on Windows too.
        codeSplitting: {
          groups: [
            {
              name: 'vendor-react',
              test: /node_modules[\\/](react|react-dom|react-router-dom|@remix-run|scheduler)[\\/]/,
              priority: 20,
            },
            {
              name: 'vendor-antd',
              test: /node_modules[\\/](antd|rc-[a-z-]+|dayjs)[\\/]/,
              priority: 15,
            },
            {
              name: 'vendor-antd-icons',
              test: /node_modules[\\/]@ant-design[\\/]/,
              priority: 16,
            },
            {
              name: 'vendor-echarts',
              test: /node_modules[\\/](echarts|echarts-for-react)[\\/]/,
              priority: 15,
            },
            {
              name: 'vendor-zrender',
              test: /node_modules[\\/](zrender|tslib)[\\/]/,
              priority: 16,
            },
            {
              name: 'vendor-misc',
              test: /node_modules[\\/](@tanstack|axios|zustand)[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
  },
})
