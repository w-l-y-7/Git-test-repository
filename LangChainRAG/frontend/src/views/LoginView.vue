<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

import api from '../api'
import { authStore } from '../stores/auth'

const router = useRouter()

const mode = ref('login') // 'login' 登录 / 'register' 注册
const loading = ref(false)
const formRef = ref()
const form = reactive({ username: '', password: '', confirm: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    {
      validator: (_rule, value, callback) => {
        if (!value) return callback(new Error('请再次输入密码'))
        if (value !== form.password) return callback(new Error('两次输入的密码不一致'))
        callback()
      },
      trigger: 'blur',
    },
  ],
}

async function submit() {
  if (loading.value) return
  try {
    await formRef.value.validate()
  } catch {
    return // 有字段没填对，Element Plus 已标红
  }
  loading.value = true
  try {
    if (mode.value === 'register') {
      await api.post('/auth/register', {
        username: form.username.trim(),
        password: form.password,
      })
      ElMessage.success('注册成功，已自动登录')
    }
    const data = await api.post('/auth/login', {
      username: form.username.trim(),
      password: form.password,
    })
    authStore.setAuth(data.token, data.user)
    router.push('/chat')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <div class="brand">
        <div class="logo">金</div>
        <h1>金融知识库问答系统</h1>
        <p>基于 LangChain 的 RAG 智能问答 · 答案附来源引用</p>
      </div>

      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        size="large"
        @keyup.enter="submit"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码（至少 6 位）"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            placeholder="再输入一次密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          class="submit"
          size="large"
          :loading="loading"
          @click="submit"
        >
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <div class="tip">演示管理员：wly / 123456</div>
    </el-card>
  </div>
</template>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f3a5f 0%, #2b3648 60%, #3a4a63 100%);
}

.login-card {
  width: 420px;
  border-radius: 12px;
  padding: 8px 12px;
}

.brand {
  text-align: center;
  margin: 12px 0 8px;
}

.logo {
  width: 52px;
  height: 52px;
  line-height: 52px;
  border-radius: 12px;
  margin: 0 auto 12px;
  font-size: 26px;
  color: #fff;
  background: linear-gradient(135deg, #2f6fdb, #3a4a63);
}

.brand h1 {
  font-size: 22px;
  margin-bottom: 6px;
}

.brand p {
  font-size: 13px;
  color: #909399;
}

.submit {
  width: 100%;
  margin-top: 4px;
}

.tip {
  margin-top: 14px;
  text-align: center;
  font-size: 12px;
  color: #a8abb2;
}
</style>
