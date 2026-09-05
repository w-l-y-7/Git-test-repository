<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'

import api from '../api'
import { askStream } from '../sse'

// ---------- 状态 ----------
const sessions = ref([]) // 会话列表
const activeId = ref(null) // 当前打开的会话 id（null = 新会话）
const messages = ref([]) // 当前会话的聊天记录
const question = ref('') // 输入框内容
const sending = ref(false) // 正在等大模型回答
const openSources = ref([]) // 哪些"引用片段"展开了
const box = ref(null) // 消息区 DOM，用来滚到底部

const suggestions = [
  '公司 2026 年上半年营收多少？',
  '公司主要做什么产品？',
  '公司面临哪些风险？',
  '公司的估值和评级怎么样？',
]

// ---------- 小工具 ----------
function fmtTime(iso) {
  const d = new Date(iso)
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}`
}

function scrollDown() {
  nextTick(() => {
    if (box.value) box.value.scrollTop = box.value.scrollHeight
  })
}

// ---------- 会话操作 ----------
async function listSessions() {
  sessions.value = await api.get('/conversations')
}

async function loadMessages(id) {
  messages.value = await api.get(`/conversations/${id}/messages`)
  scrollDown()
}

function newSession() {
  activeId.value = null
  messages.value = []
  question.value = ''
}

async function openSession(id) {
  if (id === activeId.value) return
  activeId.value = id
  messages.value = []
  await loadMessages(id)
}

async function deleteSession(id) {
  await api.delete(`/conversations/${id}`)
  if (id === activeId.value) newSession()
  listSessions()
}

// ---------- 提问 ----------
async function send() {
  const text = question.value.trim()
  if (!text || sending.value) return
  question.value = ''
  sending.value = true

  // 先在本地放上"我提问的"和"AI 空的"两条气泡，AI 的内容在流式过程中逐字变多
  const userMsg = {
    id: `u-${Date.now()}`,
    role: 'user',
    content: text,
    sources: [],
    created_at: new Date().toISOString(),
  }
  const live = reactive({
    id: 'live',
    role: 'assistant',
    content: '',
    sources: [],
    created_at: new Date().toISOString(),
  })
  messages.value.push(userMsg)
  messages.value.push(live)
  scrollDown()

  try {
    // 流式：每来一小块文字就拼到 AI 气泡上；整段结束 resolve 出 done 事件
    const done = await askStream({
      question: text,
      conversation_id: activeId.value,
      onDelta(piece) {
        live.content += piece
        scrollDown()
      },
    })
    // 没开会话时后端自动建了会话，这里补上，随后以服务器记录为准重拉一遍
    if (!activeId.value) activeId.value = done.conversation_id
    await loadMessages(activeId.value)
    listSessions()
  } catch (e) {
    live.content = (live.content ? `${live.content}\n\n` : '') + `⚠️ ${e?.message || '生成出错，请重试'}`
    scrollDown()
  } finally {
    sending.value = false
  }
}

function useSuggestion(q) {
  question.value = q
  send()
}

// ---------- 当前会话标题 ----------
const currentTitle = computed(() => {
  if (!activeId.value) return '新会话'
  const cur = sessions.value.find((s) => s.id === activeId.value)
  return cur ? cur.title : '新会话'
})

// 消息增加或开始/结束"思考中"时，自动滚到最底部
watch(
  [() => messages.value.length, sending],
  () => scrollDown(),
)

// 进页面先拉会话列表
listSessions()
</script>

<template>
  <div class="chat-page">
    <!-- 左：会话列表 -->
    <div class="session-col">
      <div class="session-head">
        <span>会话</span>
        <span class="count">{{ sessions.length }}</span>
      </div>
      <button class="new-btn" @click="newSession">
        <el-icon><Plus /></el-icon>新建会话
      </button>

      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          :class="['session-item', { active: s.id === activeId }]"
          @click="openSession(s.id)"
        >
          <span class="s-title" :title="s.title">{{ s.title }}</span>
          <el-popconfirm title="删除该会话？" width="160" @confirm="deleteSession(s.id)">
            <template #reference>
              <el-icon class="del" @click.stop><Delete /></el-icon>
            </template>
          </el-popconfirm>
        </div>
        <div v-if="!sessions.length" class="empty-tip">
          还没有会话<br />点"新建会话"或直接提问
        </div>
      </div>
    </div>

    <!-- 右：聊天窗口 -->
    <div class="chat-col">
      <div class="chat-head">
        <span class="chat-title">{{ currentTitle }}</span>
      </div>

      <div ref="box" class="msg-box">
        <!-- 欢迎空态 -->
        <div v-if="!messages.length && !activeId && !sending" class="welcome">
          <div class="w-logo">金</div>
          <p class="w-title">你好，我是金融知识库助手</p>
          <p class="w-sub">回答会引用知识库原文。试试问：</p>
          <div class="chips">
            <button
              v-for="q in suggestions"
              :key="q"
              class="chip"
              @click="useSuggestion(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>

        <!-- 历史消息 -->
        <template v-else>
          <div v-if="!messages.length" class="center-hint">新会话已就绪，问点什么吧</div>

          <div v-for="m in messages" :key="m.id" :class="['msg-row', m.role]">
            <div class="bubble-wrap">
              <div v-if="m.role === 'assistant'" class="ai-line">
                <span class="ai-tag">AI</span>
                <div v-if="m.id === 'live' && !m.content" class="bubble typing">
                  <span class="dots"><i /><i /><i /></span>
                  <span class="typing-text">正在检索知识库并思考…</span>
                </div>
                <div v-else class="bubble">{{ m.content }}</div>
              </div>
              <div v-else class="bubble user-bubble">{{ m.content }}</div>

              <div class="meta-line">
                <span class="time">{{ fmtTime(m.created_at) }}</span>
              </div>

              <!-- AI 回答附带的引用片段 -->
              <div
                v-if="m.role === 'assistant' && m.sources && m.sources.length"
                class="sources"
              >
                <el-collapse v-model="openSources">
                  <el-collapse-item
                    v-for="(src, i) in m.sources"
                    :key="`${m.id}-${i}`"
                    :title="`引用片段 ${i + 1}`"
                    :name="`${m.id}-${i}`"
                  >
                    <div class="src-content">{{ src }}</div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </div>

        </template>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="输入问题，Enter 发送，Shift + Enter 换行"
          @keydown.enter.exact.prevent="send"
        />
        <div class="input-bar">
          <span class="hint">答案基于知识库内容生成，可展开上方引用片段核对原文</span>
          <el-button type="primary" :loading="sending" @click="send">发送</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  height: 100%;
  display: flex;
  min-height: 0;
}

/* ---------- 会话列 ---------- */
.session-col {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.session-head {
  padding: 14px 16px 10px;
  font-weight: 600;
  color: #303133;
  display: flex;
  justify-content: space-between;
}

.count {
  font-weight: 400;
  color: #909399;
  font-size: 13px;
}

.new-btn {
  margin: 0 12px 10px;
  height: 36px;
  border: 1px dashed #c0c4cc;
  border-radius: 8px;
  background: #fafbfc;
  color: #2f6fdb;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 13px;
}

.new-btn:hover {
  background: #ecf5ff;
  border-color: #2f6fdb;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 10px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 2px;
}

.session-item:hover {
  background: #f5f7fa;
}

.session-item.active {
  background: #ecf5ff;
}

.session-item.active .s-title {
  color: #2f6fdb;
}

.s-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: #303133;
}

.del {
  color: #c0c4cc;
  visibility: hidden;
  font-size: 15px;
}

.session-item:hover .del {
  visibility: visible;
}

.del:hover {
  color: #f56c6c;
}

.empty-tip {
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
  line-height: 1.8;
  padding-top: 30px;
}

/* ---------- 聊天列 ---------- */
.chat-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #f5f7fa;
  min-height: 0;
}

.chat-head {
  height: 48px;
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.chat-title {
  font-weight: 600;
  color: #303133;
  font-size: 15px;
}

.msg-box {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.w-logo {
  width: 56px;
  height: 56px;
  line-height: 56px;
  text-align: center;
  border-radius: 14px;
  font-size: 26px;
  color: #fff;
  background: linear-gradient(135deg, #2f6fdb, #3a7be0);
  margin-bottom: 6px;
}

.w-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.w-sub {
  color: #909399;
  font-size: 14px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 560px;
  margin-top: 12px;
}

.chip {
  border: 1px solid #d0d7e2;
  background: #fff;
  color: #2f6fdb;
  border-radius: 18px;
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
}

.chip:hover {
  background: #ecf5ff;
  border-color: #2f6fdb;
}

.center-hint {
  text-align: center;
  color: #c0c4cc;
  padding-top: 60px;
  font-size: 14px;
}

/* ---------- 气泡 ---------- */
.msg-row {
  margin-bottom: 20px;
}

.msg-row.user {
  display: flex;
  justify-content: flex-end;
}

.bubble-wrap {
  max-width: 80%;
}

.ai-line {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.ai-tag {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2f6fdb, #3a7be0);
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bubble {
  padding: 10px 14px;
  border-radius: 10px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  color: #303133;
}

.ai-line .bubble {
  background: #fff;
  border: 1px solid #e8ebf0;
}

.user-bubble {
  background: #2f6fdb;
  color: #fff;
}

.meta-line {
  display: flex;
  justify-content: flex-end;
  margin-top: 3px;
}

.msg-row.user .meta-line {
  justify-content: flex-end;
}

.time {
  font-size: 11px;
  color: #c0c4cc;
}

/* 思考中的点点动画 */
.typing {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.dots i {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 3px;
  border-radius: 50%;
  background: #2f6fdb;
  animation: blink 1.2s infinite;
}

.dots i:nth-child(2) {
  animation-delay: 0.2s;
}

.dots i:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0%, 80%, 100% {
    opacity: 0.3;
  }
  40% {
    opacity: 1;
  }
}

.typing-text {
  color: #909399;
  font-size: 13px;
}

/* ---------- 引用片段 ---------- */
.sources {
  margin-top: 10px;
  margin-left: 40px;
}

.src-content {
  white-space: pre-wrap;
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  background: #f7f8fa;
  padding: 10px;
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
}

/* ---------- 输入区 ---------- */
.input-area {
  flex-shrink: 0;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  padding: 12px 20px 14px;
}

.input-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.hint {
  color: #b0b3ba;
  font-size: 12px;
}
</style>
