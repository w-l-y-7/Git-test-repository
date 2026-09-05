import { authStore } from './stores/auth'

// 流式问答：POST /api/ask/stream，返回 Promise。
// 后端逐帧下发 data: {...}（SSE 格式），帧里有三种 type：
//   delta 生成中的文字增量（回调 onDelta）
//   done  生成结束，resolve 这个事件（带 conversation_id 和 sources）
//   error 中途出错，reject
export function askStream({ question, conversation_id, onDelta }) {
  return new Promise((resolve, reject) => {
    ;(async () => {
      try {
        const resp = await fetch('/api/ask/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authStore.token}`,
          },
          body: JSON.stringify({ question, conversation_id: conversation_id ?? null }),
        })
        if (!resp.ok || !resp.body) {
          let detail = `请求失败（${resp.status}）`
          try {
            const j = await resp.json()
            if (j.detail) detail = j.detail
          } catch {
            /* 非 JSON 响应就算了 */
          }
          throw new Error(detail)
        }

        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true }) // stream:true 避免中文跨帧截断
          let idx
          while ((idx = buf.indexOf('\n\n')) !== -1) {
            const frame = buf.slice(0, idx)
            buf = buf.slice(idx + 2)
            const line = frame.split('\n').find((l) => l.startsWith('data:'))
            if (!line) continue
            const payload = line.startsWith('data: ') ? line.slice(6) : line.slice(5)
            let evt
            try {
              evt = JSON.parse(payload)
            } catch {
              continue
            }
            if (evt.type === 'delta') {
              if (onDelta) onDelta(evt.text || '')
            } else if (evt.type === 'done') {
              resolve(evt)
              return
            } else if (evt.type === 'error') {
              throw new Error(evt.detail || '回答生成出错，请重试')
            }
          }
        }
        throw new Error('连接结束了，但没有收到完整回答，请重试')
      } catch (e) {
        reject(e instanceof Error ? e : new Error('连接中断，请重试'))
      }
    })()
  })
}
