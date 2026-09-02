<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import api from '../api'
import { authStore } from '../stores/auth'

const formRef = ref()
const form = reactive({ old_password: '', new_password: '', confirm: '' })

const rules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value && value === form.old_password) return callback(new Error('新密码不能和当前密码一样'))
        callback()
      },
      trigger: 'blur',
    },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.new_password) return callback(new Error('两次输入的密码不一致'))
        callback()
      },
      trigger: 'blur',
    },
  ],
}

async function changePwd() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  await api.post('/auth/change-password', {
    old_password: form.old_password,
    new_password: form.new_password,
  })
  ElMessage.success('密码修改成功')
  formRef.value.resetFields()
}
</script>

<template>
  <div class="page">
    <div class="page-inner">
      <el-card class="box" shadow="never">
        <template #header>
          <span class="card-title">账号信息</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="用户名">
            {{ authStore.user?.username }}
          </el-descriptions-item>
          <el-descriptions-item label="角色">
            <el-tag size="small" :type="authStore.isAdmin ? 'danger' : 'info'">
              {{ authStore.isAdmin ? '管理员' : '普通用户' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="box" shadow="never">
        <template #header>
          <span class="card-title">修改密码</span>
        </template>
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="110px"
          style="max-width: 420px"
        >
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="form.old_password" type="password" show-password placeholder="输入当前密码" />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="form.new_password" type="password" show-password placeholder="至少 6 位" />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm">
            <el-input v-model="form.confirm" type="password" show-password placeholder="再输入一次" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="changePwd">保存修改</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.page {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
}

.page-inner {
  max-width: 760px;
}

.box {
  margin-bottom: 20px;
  border-radius: 10px;
}

.card-title {
  font-weight: 600;
}
</style>
