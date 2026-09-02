import axios from 'axios'
import { ElMessage } from 'element-plus'

import router from './router'
import { authStore } from './stores/auth'

// 统一的后端请求工具：所有页面都用它，不用各自处理 token 和错误
const api = axios.create({
  baseURL: '/api', // 开发时由 vite 代理转发到后端 8000
  timeout: 120000, // 问答要等大模型回答，给足 2 分钟
})

// 每次请求前自动带上登录 token
api.interceptors.request.use((config) => {
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

// 统一处理后端返回：接口成功直接拿到数据；失败弹一句人话
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail

    if (status === 401) {
      // 登录失效：清状态、回登录页
      authStore.clear()
      if (router.currentRoute.value.path !== '/login') {
        ElMessage.error(detail || '登录已失效，请重新登录')
        router.push('/login')
      } else {
        ElMessage.error(detail || '用户名或密码错误')
      }
    } else if (!err.response) {
      ElMessage.error('无法连接服务器，请确认后端已启动')
    } else {
      ElMessage.error(detail || `请求出错（${status}），请稍后再试`)
    }
    return Promise.reject(err)
  },
)

export default api
