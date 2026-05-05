import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'
import NewsDetailPage from '@/pages/NewsDetailPage.vue'
import ReaderPage from '@/pages/ReaderPage.vue'

// 定义路由配置
const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
  },
  {
    path: '/news/:id',
    name: 'news-detail',
    component: NewsDetailPage,
  },
  {
    path: '/reader',
    name: 'reader',
    component: ReaderPage,
  },
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router