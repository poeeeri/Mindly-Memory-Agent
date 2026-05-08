import './styles.css'
import { useState, useEffect, useCallback, useMemo, useRef } from 'react'

import {
  getAppConfig,
  getChatHistory,
  getMemory,
  streamChat,
  clearChatHistory,
  forgetAllMemory,
  forgetMemoryFact
} from './api'

import LoginForm from './components/LoginForm'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import ChatView from './components/ChatView'
import MemoryView from './components/MemoryView'
import EvaluationView from './components/EvaluationView'

function App() {
  const [loggedInUser, setLoggedInUser] = useState(() => {
    return localStorage.getItem('mindly_user') || null
  })
  const [view, setView] = useState(() => {
    const saved = localStorage.getItem('mindly_view')
    return saved === 'memory' || saved === 'evaluation' ? saved : 'chat'
  })
  const [persona, setPersona] = useState(() => {
    return localStorage.getItem('mindly_persona') || 'wellness_friend'
  })

  const [message, setMessage] = useState('')
  const [histories, setHistories] = useState(new Map())
  const [facts, setFacts] = useState([])
  const [selectedFacts, setSelectedFacts] = useState(new Set())
  const [streaming, setStreaming] = useState(false)
  const [toast, setToast] = useState('')
  const [config, setConfig] = useState({ model: 'loading', memoryBackend: '', factExtractor: '' })
  const toastTimerRef = useRef(null)

  const history = useMemo(() => histories.get(loggedInUser) || [], [histories, loggedInUser])

  const showToast = useCallback((msg) => {
    setToast(msg)
    clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => setToast(''), 3200)
  }, [])

  const setCurrentHistory = useCallback((userId, nextHistory) => {
    setHistories((prev) => new Map(prev).set(userId, nextHistory))
  }, [])

  const loadConfig = useCallback(async () => {
    try {
      const res = await getAppConfig()
      setConfig({
        model: res.model,
        memoryBackend: res.memory_backend,
        factExtractor: res.fact_extractor,
      })
    } catch {
      setConfig(prev => ({ ...prev, model: 'server model' }))
    }
  }, [])

  const loadHistory = useCallback(async (userId) => {
    if (!userId) return
    try {
      const res = await getChatHistory(userId)
      setCurrentHistory(userId, res.history || [])
    } catch {
      setCurrentHistory(userId, [])
    }
  }, [setCurrentHistory])

  const loadMemory = useCallback(async (userId) => {
    if (!userId) return
    try {
      const res = await getMemory(userId)
      setFacts(res.facts || [])
    } catch {
      setFacts([])
    }
  }, [])

  useEffect(() => {
    if (!loggedInUser) return
    loadConfig()
    loadHistory(loggedInUser)
    loadMemory(loggedInUser)
    setSelectedFacts(new Set())
  }, [loggedInUser, loadConfig, loadHistory, loadMemory])

  const handleNewChat = useCallback(async () => {
    if (!loggedInUser) return
    await clearChatHistory(loggedInUser)
    setCurrentHistory(loggedInUser, [])
    showToast('Начат новый диалог. Долгосрочная память сохранена.')
  }, [loggedInUser, setCurrentHistory, showToast])

  const handleForgetAll = useCallback(async () => {
    if (!loggedInUser) return
    const result = await forgetAllMemory(loggedInUser)
    setFacts([])
    setSelectedFacts(new Set())
    showToast(`Вся долгосрочная память очищена. Удалено записей: ${result.deleted}.`)
  }, [loggedInUser, showToast])

  const handleForgetSelected = useCallback(async () => {
    if (!loggedInUser) return
    const selected = facts.filter(f => selectedFacts.has(f.id))
    if (selected.length === 0) return

    for (const fact of selected) {
      await forgetMemoryFact(loggedInUser, fact.text)
    }
    setSelectedFacts(new Set())
    await loadMemory(loggedInUser)
    showToast(`Удалено выбранных фактов: ${selected.length}.`)
  }, [loggedInUser, facts, selectedFacts, loadMemory, showToast])

  const handleForgetSingle = useCallback(async (fact) => {
    if (!loggedInUser) return
    await forgetMemoryFact(loggedInUser, fact.text)
    await loadMemory(loggedInUser)
    showToast(`Забыто: ${fact.text.substring(0, 60)}${fact.text.length > 60 ? '…' : ''}`)
  }, [loggedInUser, loadMemory, showToast])

  const handleToggleFact = useCallback((factId) => {
    setSelectedFacts(prev => {
      const next = new Set(prev)
      if (next.has(factId)) next.delete(factId)
      else next.add(factId)
      return next
    })
  }, [])

  const handleSend = useCallback(async (e) => {
    e.preventDefault()
    if (!loggedInUser) return
    const content = message.trim()
    if (!content || streaming) return

    const nextHistory = [...history, { role: 'user', content }, { role: 'assistant', content: '' }]
    setCurrentHistory(loggedInUser, nextHistory)
    setMessage('')
    setStreaming(true)

    try {
      let assistantText = ''
      await streamChat({
        userId: loggedInUser,
        persona,
        message: content,
        onChunk: (chunk) => {
          assistantText += chunk
          setCurrentHistory(loggedInUser, [
            ...nextHistory.slice(0, -1),
            { role: 'assistant', content: assistantText }
          ])
        }
      })
      await loadMemory(loggedInUser)
    } catch (error) {
      setCurrentHistory(loggedInUser, [
        ...nextHistory.slice(0, -1),
        { role: 'assistant', content: `Ошибка: ${error.message}` }
      ])
    } finally {
      setStreaming(false)
    }
  }, [loggedInUser, message, streaming, history, persona, setCurrentHistory, loadMemory])

  const handleLogin = useCallback((username) => {
    setLoggedInUser(username)
    localStorage.setItem('mindly_user', username)
  }, [])

  const handleLogout = useCallback(() => {
    setLoggedInUser(null)
    localStorage.removeItem('mindly_user')
    localStorage.removeItem('mindly_view')
    localStorage.removeItem('mindly_persona')
    setHistories(new Map())
    setFacts([])
    setSelectedFacts(new Set())
    setMessage('')
    setStreaming(false)
    setToast('')
    setView('chat')
  }, [])

  const handlePersonaChange = useCallback((newPersona) => {
    setPersona(newPersona)
    localStorage.setItem('mindly_persona', newPersona)
  }, [])

  const handleViewChange = useCallback((newView) => {
    setView(newView)
    localStorage.setItem('mindly_view', newView)
  }, [])

  const renderView = () => {
    switch (view) {
      case 'memory':
        return (
          <MemoryView
            facts={facts}
            selectedFacts={selectedFacts}
            onToggleFact={handleToggleFact}
            onForgetSelected={handleForgetSelected}
            onForgetAll={handleForgetAll}
            onForgetSingle={handleForgetSingle}
          />
        )
      case 'evaluation':
        return <EvaluationView facts={facts} persona={persona} userId={loggedInUser} />
      default:
        return (
          <ChatView
            history={history}
            message={message}
            onMessageChange={setMessage}
            onSend={handleSend}
            streaming={streaming}
          />
        )
    }
  }

  if (!loggedInUser) {
    return <LoginForm onLogin={handleLogin} />
  }

  return (
    <div className="app-shell">
      <Sidebar config={config} view={view} onViewChange={handleViewChange} onLogout={handleLogout} />
      <main className="workspace">
        <Topbar
          model={config.model}
          userId={loggedInUser}
          persona={persona}
          onPersonaChange={handlePersonaChange}
          onClearChat={handleNewChat}
        />
        {renderView()}
      </main>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}

export default App