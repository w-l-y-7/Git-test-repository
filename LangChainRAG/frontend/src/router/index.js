import { createRouter, createWebHistory } from 'vue-router'

import { authStore } from '../stores/auth'

// 路由表：/login 登录页，其余页面都在带左侧导航的布局里（children）
// 页面用懒加载（component: () => import(...)），用到才下载，首屏更快
const routes = [
  {
    path: '/login',
    component: () => import('../views/LoginView.vue'),
    meta: { guestOnly: true }, // 已登录的人不该再看到登录页
  },
  {
    path: '/',
    component: () => import('../layouts/AppLayout.vue'),
    children: [
      { path: '', redirect: '/chat' },
      {
        path: 'chat',
        component: () => import('../views/ChatView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'kb',
        component: () => import('../views/KbView.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'profile',
        component: () => import('../views/ProfileView.vue'),
        meta: { requiresAuth: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局守卫：进每个页面前先查权限，拦住没登录的人 / 非管理员的普通用户
router.beforeEach((to) => {
  const requiresAuth = to.matched.some((r) => r.meta.requiresAuth)

  if (requiresAuth && !authStore.isLoggedIn) {
    return '/login'
  }
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return '/chat'
  }
  if (to.meta.guestOnly && authStore.isLoggedIn) {
    return '/chat'
  }
  return true
})

export default router
