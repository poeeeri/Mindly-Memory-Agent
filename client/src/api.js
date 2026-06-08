export async function fetchJson(url, options = {}) {
  const response = await fetch(url, options)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}

export function getAppConfig() {
  return fetchJson('/app-config')
}

export function getChatHistory(userId) {
  return fetchJson(`/chat/history?user_id=${encodeURIComponent(userId)}`)
}

export function clearChatHistory(userId) {
  return fetchJson(`/chat/history?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })
}

export function getMemory(userId) {
  return fetchJson(`/memory?user_id=${encodeURIComponent(userId)}`)
}

export function forgetAllMemory(userId) {
  return fetchJson(`/memory/all?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })
}

export function forgetMemoryFact(userId, query) {
  return fetchJson(
    `/memory?user_id=${encodeURIComponent(userId)}&query=${encodeURIComponent(query)}`,
    { method: 'DELETE' },
  )
}

export function refreshMemory(userId) {
  return fetchJson(`/memory/refresh?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
  })
}

export async function streamChat({ userId, persona, message, onChunk }) {
  const response = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      persona,
      message,
    }),
  })

  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    onChunk(decoder.decode(value, { stream: true }))
  }
}
