<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '../api'
import { authStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()

// 顶部标题随页面变化
const titles = { '/chat': '智能问答', '/kb': '知识库管理', '/profile': '个人中心' }
const pageTitle = computed(() => titles[route.path] || '')

const initial = computed(() => (authStore.user?.username || '?').slice(0, 1).toUpperCase())

function logout() {
  authStore.clear()
  ElMessage.success('已退出登录')
  router.push('/login')
}

// 刚进系统时向后端核对一次身份（角色可能变化，保证"知识库管理"菜单权限准确）
if (authStore.isLoggedIn) {
  api
    .get('/auth/me')
    .then((user) => authStore.setAuth(authStore.token, user))
    .catch(() => {}) // token 过期等情况由 axios 拦截器统一处理（回登录页）
}
</script>

<template>
  <el-container class="app-layout">
    <!-- 左侧全局导航栏 -->
    <el-aside width="220px" class="aside">
      <div class="brand">
        <div class="logo">金</div>
        <span class="brand-name">金融知识库</span>
      </div>

      <el-menu
        class="menu"
        background-color="#2b3648"
        text-color="#cfd6e4"
        active-text-color="#ffffff"
        :default-active="route.path"
        router
      >
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>问答</span>
        </el-menu-item>
        <el-menu-item v-if="authStore.isAdmin" index="/kb">
          <el-icon><FolderOpened /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/profile">
          <el-icon><User /></el-icon>
          <span>个人中心</span>
        </el-menu-item>
      </el-menu>

      <!-- 底部：当前用户 + 退出登录 -->
      <div class="side-user">
        <div class="user-line">
          <el-avatar :size="34" class="avatar">{{ initial }}</el-avatar>
          <div class="meta">
            <div class="uname">{{ authStore.user?.username }}</div>
            <el-tag size="small" :type="authStore.isAdmin ? 'danger' : 'info'">
              {{ authStore.isAdmin ? '管理员' : '普通用户' }}
            </el-tag>
          </div>
        </div>
        <button class="logout-btn" @click="logout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </button>
      </div>
    </el-aside>

    <!-- 右侧内容区 -->
    <el-container class="right">
      <el-header class="header" height="56px">
        <span class="page-title">{{ pageTitle }}</span>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-layout {
  height: 100vh;
}

.aside {
  background: #2b3648;
  display: flex;
  flex-direction: column;
  color: #fff;
}

.brand {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo {
  width: 30px;
  height: 30px;
  line-height: 30px;
  text-align: center;
  border-radius: 8px;
  font-size: 15px;
  background: linear-gradient(135deg, #2f6fdb, #4a8cff);
}

.brand-name {
  font-size: 16px;
  font-weight: 600;
}

.menu {
  flex: 1;
  border-right: none;
  padding-top: 6px;
}

.menu :deep(.el-menu-item) {
  margin: 4px 8px;
  border-radius: 8px;
}

.menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #2f6fdb, #3a7be0);
}

.side-user {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px;
}

.user-line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.avatar {
  background: #2f6fdb;
  color: #fff;
  flex-shrink: 0;
}

.meta .uname {
  font-size: 14px;
  color: #fff;
  margin-bottom: 2px;
}

.logout-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: #cfd6e4;
  background: rgba(255, 255, 255, 0.06);
  font-size: 13px;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}

.right {
  background: #f5f7fa;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.main {
  padding: 0;
  overflow: hidden;
}
</style>
