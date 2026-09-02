<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

import api from '../api'

const docs = ref([]) // 已入库文档
const title = ref('') // 可选的文档标题
const fileList = ref([]) // el-upload 选中的文件
const uploading = ref(false)

function fmtTime(iso) {
  const d = new Date(iso)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadDocs() {
  docs.value = await api.get('/documents')
}

function onExceed(files) {
  // 只允许选 1 个文件：超了就用新选的替换旧的
  fileList.value = [files[0]]
}

async function doUpload() {
  const raw = fileList.value[0]?.raw
  if (!raw) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', raw)
    fd.append('title', title.value.trim())
    await api.post('/documents/upload', fd)
    ElMessage.success('上传成功，已切块向量化入库')
    title.value = ''
    fileList.value = []
    loadDocs()
  } finally {
    uploading.value = false
  }
}

async function removeDoc(id) {
  await api.delete(`/documents/${id}`)
  ElMessage.success('文档已删除')
  loadDocs()
}

onMounted(loadDocs)
</script>

<template>
  <div class="page">
    <div class="page-inner">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="上传即入库"
        description="支持 TXT / Markdown / PDF。上传后系统自动切块并向量化，之后所有人问答时都能引用到新文档的内容。"
      />

      <!-- 上传区 -->
      <el-card class="box" shadow="never">
        <template #header>
          <span class="card-title">上传文档</span>
        </template>

        <el-upload
          v-model:file-list="fileList"
          drag
          :auto-upload="false"
          :limit="1"
          :on-exceed="onExceed"
          accept=".txt,.md,.pdf"
          class="uploader"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到这里，或 <em>点击选择</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              单个文件 ≤ 10MB · 仅支持 TXT / Markdown / PDF（扫描版 PDF 需先转成可复制文字）
            </div>
          </template>
        </el-upload>

        <div class="upload-actions">
          <el-input
            v-model="title"
            placeholder="文档标题（可留空，默认用文件名）"
            clearable
            style="max-width: 360px"
          />
          <el-button type="primary" :loading="uploading" @click="doUpload">
            上传到知识库
          </el-button>
        </div>
      </el-card>

      <!-- 已入库文档 -->
      <el-card class="box" shadow="never">
        <template #header>
          <span class="card-title">已入库文档（{{ docs.length }}）</span>
        </template>

        <el-table :data="docs" stripe empty-text="还没有文档，先上传一份试试">
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="filename" label="原始文件" min-width="130" show-overflow-tooltip />
          <el-table-column prop="chunk_count" label="片段数" width="90" align="center" />
          <el-table-column label="上传时间" width="150">
            <template #default="{ row }">
              {{ fmtTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-popconfirm title="删除该文档？问答将不再引用它的内容" width="220" @confirm="removeDoc(row.id)">
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
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
  max-width: 960px;
}

.box {
  margin-top: 20px;
  border-radius: 10px;
}

.card-title {
  font-weight: 600;
}

.uploader {
  width: 100%;
}

.upload-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}
</style>
