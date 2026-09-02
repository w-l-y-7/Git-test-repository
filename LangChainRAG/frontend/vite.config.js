import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 开发时前端跑在 5173，把 /api 开头的请求转发给后端 8000，
    // 这样页面里写的接口地址永远是 /api/...，不用关心后端在哪个端口
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
