import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  base: './', // 确保构建后路径正确
  plugins: [react()],
  build: {
    assetsDir: 'assets', // 静态资源目录
    rollupOptions: {
      output: {
        manualChunks: undefined // 确保不进行额外的代码分割，避免路径问题
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
