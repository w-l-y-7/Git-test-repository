import { reactive } from 'vue'

// 登录状态统一放这里管理：刷新页面后从 localStorage 恢复，避免又跳回登录页。
// 注意：token 放在浏览器 localStorage，仅演示用；上线要考虑更安全的存法（如 HttpOnly Cookie）。
const saved = JSON.parse(localStorage.getItem('auth') || 'null')

export const authStore = reactive({
  token: saved?.token || '',
  user: saved?.user || null,

  get isLoggedIn() {
    return Boolean(this.token)
  },

  get isAdmin() {
    return this.user?.role === 'admin'
  },

  setAuth(token, user) {
    this.token = token
    this.user = user
    localStorage.setItem('auth', JSON.stringify({ token, user }))
  },

  clear() {
    this.token = ''
    this.user = null
    localStorage.removeItem('auth')
  },
})
