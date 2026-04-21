import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import Inspector from 'unplugin-vue-dev-locator/vite'
import traeBadgePlugin from 'vite-plugin-trae-solo-badge'

export default defineConfig({
  build: {
    sourcemap: 'hidden',
  },
  server: {
    // === 新增/修改的部分 ===
    host: '0.0.0.0',       // 允许监听所有局域网地址
    allowedHosts: [
      '.cpolar.io',        // 允许所有 cpolar 二级域名访问
      '.cpolar.top',
      '.cpolar.cn',
      'upswing-spew-negligee.ngrok-free.dev', // 直接添加报错的域名
      '.ngrok-free.dev',                     // 允许所有 .dev 后缀
      '.ngrok-free.app',                     // 允许所有 .app 后缀
      '.cpolar.io',                          // 保持对 cpolar 的支持
      '.cpolar.top'
    ],
    // =====================
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 如果后端也是 cpolar 穿透的，target 请改为后端的 cpolar https 地址
      },
    },
  },
  plugins: [
    vue(),
    Inspector(),
    traeBadgePlugin({
      variant: 'dark',
      position: 'bottom-right',
      prodOnly: true,
      clickable: true,
      clickUrl: 'https://www.trae.ai/solo?showJoin=1',
      autoTheme: true,
      autoThemeTarget: '#app',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})