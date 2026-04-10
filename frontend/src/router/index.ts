import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'
import NewsDetailPage from '@/pages/NewsDetailPage.vue'

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
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
