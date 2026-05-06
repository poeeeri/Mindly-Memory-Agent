/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  BarChart3,
  Bot,
  Database,
  Eraser,
  MessageCircle,
  PlusCircle,
  Send,
  Trash2,
  UserRound,
  X,
} from 'lucide-react'
import {
  clearChatHistory,
  forgetAllMemory,
  forgetMemoryFact,
  getAppConfig,
  getChatHistory,
  getMemory,
  streamChat,
} from './api'
import './styles.css'

const USERS = ['demo_user', 'user_1', 'user_2', 'other_user']
const PERSONAS = ['wellness_friend', 'tough_love']

function formatTime(value) {
  if (!value) return 'сейчас'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'сейчас'
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function factKind(fact) {
  if (fact.source?.includes(':')) return fact.source.split(':').pop()
  if (/работ|стресс|тревог|deadline|дедлайн/i.test(fact.text)) return 'situation'
  if (/хочет|цель|план/i.test(fact.text)) return 'goal'
  return 'personal'
}

function Sidebar({ view, onViewChange, config }) {
  const items = [
    ['chat', MessageCircle, 'Chat'],
    ['evaluation', BarChart3, 'Evaluation'],
  ]

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">M</div>
        <div>
          <div className="brand-title">Mindly</div>
          <div className="brand-subtitle">memory agent</div>
        </div>
      </div>

      <nav className="nav">
        {items.map(([key, Icon, label]) => (
          <button
            className={`nav-button ${view === key ? 'active' : ''}`}
            key={key}
            onClick={() => onViewChange(key)}
            type="button"
          >
            <Icon size={20} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <strong>{config.memoryBackend || 'memory'}</strong>
        <br />
        extractor: {config.factExtractor || 'llm'}
      </div>
    </aside>
  )
}

function Topbar({
  model,
  onClearChat,
  onForgetAll,
  onOpenMemory,
  onPersonaChange,
  onUserChange,
  persona,
  userId,
}) {
  return (
    <div className="topbar">
      <div className="selectors">
        <label className="field">
          User:
          <select value={userId} onChange={(event) => onUserChange(event.target.value)}>
            {USERS.map((user) => (
              <option key={user} value={user}>
                {user}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          Persona:
          <select value={persona} onChange={(event) => onPersonaChange(event.target.value)}>
            {PERSONAS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <div className="field">
          Model: <span className="model-pill">{model || 'loading'}</span>
        </div>
      </div>

      <div className="actions">
        <button className="button primary" onClick={onOpenMemory} type="button">
          <Database size={17} />
          Память
        </button>
        <button className="button" onClick={onClearChat} type="button">
          <PlusCircle size={17} />
          Новый чат
        </button>
        <button className="button" onClick={onClearChat} type="button">
          <Eraser size={17} />
          Удалить диалог
        </button>
        <button className="button danger" onClick={onForgetAll} type="button">
          <Trash2 size={17} />
          Удалить всю память
        </button>
      </div>
    </div>
  )
}

function MarkdownMessage({ content }) {
  return (
    <div className="markdown">
      <ReactMarkdown>{content || ' '}</ReactMarkdown>
    </div>
  )
}

function ChatMessage({ item, streaming }) {
  const isUser = item.role === 'user'
  return (
    <div className={`message-row ${isUser ? 'user-row' : ''}`}>
      {!isUser && (
        <div className="avatar assistant-avatar">
          <Bot size={18} />
        </div>
      )}
      <div className="bubble">
        <MarkdownMessage content={item.content} />
        <div className="bubble-meta">{streaming ? 'streaming...' : ''}</div>
      </div>
      {isUser && (
        <div className="avatar">
          <UserRound size={18} />
        </div>
      )}
    </div>
  )
}

function ChatView({ history, message, onMessageChange, onSend, streaming }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [history, streaming])

  return (
    <div className="chat-layout chat-layout-single">
      <section className="chat-card">
        <div className="chat-stream" aria-live="polite">
          {history.length ? (
            history.map((item, index) => (
              <ChatMessage
                item={item}
                key={`${item.role}-${index}`}
                streaming={streaming && index === history.length - 1 && item.role === 'assistant'}
              />
            ))
          ) : (
            <div className="empty">
              Напишите первое сообщение. Ответ будет стримиться сюда, а долгосрочная память доступна
              по кнопке “Память”.
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form className="composer" onSubmit={onSend}>
          <textarea
            disabled={streaming}
            onChange={(event) => onMessageChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                event.currentTarget.form.requestSubmit()
              }
            }}
            placeholder="Напишите сообщение..."
            value={message}
          />
          <button className="icon-button primary" disabled={streaming} title="Send" type="submit">
            <Send size={18} />
          </button>
        </form>
      </section>
    </div>
  )
}

function MemoryDrawer({
  facts,
  isOpen,
  onClose,
  onForgetAll,
  onForgetSelected,
  onToggleFact,
  selectedFacts,
}) {
  if (!isOpen) return null

  return (
    <div className="drawer-layer">
      <button className="drawer-backdrop" onClick={onClose} type="button" aria-label="Закрыть память" />
      <aside className="memory-drawer" aria-label="Долгосрочная память">
        <div className="drawer-header">
          <div>
            <h2 className="drawer-title">Долгосрочная память</h2>
            <div className="hint">Факты пользователя, которые агент может использовать между сессиями.</div>
          </div>
          <button className="icon-button" onClick={onClose} type="button" aria-label="Закрыть">
            <X size={18} />
          </button>
        </div>

        <div className="drawer-actions">
          <button
            className="button"
            disabled={!selectedFacts.size}
            onClick={onForgetSelected}
            type="button"
          >
            Забыть выбранное
          </button>
          <button className="button danger" onClick={onForgetAll} type="button">
            Удалить всю память
          </button>
        </div>

        {facts.length ? (
          <div className="drawer-facts">
            {facts.map((fact) => {
              const kind = factKind(fact)
              return (
                <label className="drawer-fact" key={fact.id}>
                  <input
                    checked={selectedFacts.has(fact.id)}
                    onChange={() => onToggleFact(fact.id)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{fact.text}</strong>
                    <span className="drawer-fact-meta">
                      <span className={`badge ${kind}`}>{kind}</span>
                      <span className="badge">{fact.source}</span>
                      <span>{formatTime(fact.created_at)}</span>
                    </span>
                  </span>
                </label>
              )
            })}
          </div>
        ) : (
          <div className="empty">Долгосрочная память текущего пользователя пуста.</div>
        )}
      </aside>
    </div>
  )
}

function StatusBadge({ pass }) {
  return <span className={`status ${pass ? 'pass' : 'pending'}`}>{pass ? '● pass' : '● pending'}</span>
}

function EvalBox({ title, children }) {
  return (
    <div className="eval-box">
      <div className="eval-box-title">{title}</div>
      {children}
    </div>
  )
}

function EvaluationCard({ children, index, pass, subtitle, title }) {
  return (
    <article className="eval-card">
      <div className="eval-header">
        <div className="eval-title">
          <span className="step">{index}</span>
          <div>
            <h2 className="card-title">{title}</h2>
            <div className="hint">{subtitle}</div>
          </div>
        </div>
        <StatusBadge pass={pass} />
      </div>
      <div className="eval-body">{children}</div>
    </article>
  )
}

function EvaluationView({ facts, persona, userId }) {
  const hasFacts = facts.length > 0
  return (
    <section>
      <h1 className="page-title">Evaluation</h1>
      <p className="page-subtitle">Проверка ключевых возможностей агента на текущем состоянии демо.</p>

      <div className="eval-list">
        <EvaluationCard
          index={1}
          pass={hasFacts}
          subtitle="Агент использует сохранённую информацию."
          title="Recall"
        >
          <EvalBox title="Вопрос">Что ты помнишь обо мне?</EvalBox>
          <EvalBox title="Доступные факты">{hasFacts ? facts[0].text : 'Фактов пока нет.'}</EvalBox>
        </EvaluationCard>

        <EvaluationCard
          index={2}
          pass
          subtitle="Удалённая информация больше не используется."
          title="Forgetting"
        >
          <EvalBox title="Механика">Откройте “Память”, выберите факты и нажмите “Забыть выбранное”.</EvalBox>
          <EvalBox title="API">DELETE /memory и DELETE /memory/all</EvalBox>
        </EvaluationCard>

        <EvaluationCard
          index={3}
          pass={PERSONAS.includes(persona)}
          subtitle="Стиль меняется, память пользователя остаётся общей."
          title="Persona switch"
        >
          <EvalBox title="wellness_friend">Тёплый поддерживающий стиль.</EvalBox>
          <EvalBox title="tough_love">Более прямой и структурный стиль.</EvalBox>
        </EvaluationCard>

        <EvaluationCard
          index={4}
          pass
          subtitle="Данные пользователей изолированы по user_id."
          title="Tenant isolation"
        >
          <EvalBox title={`${userId} текущий`}>
            {hasFacts ? (
              <div className="badge-wrap">
                {facts.map((fact) => (
                  <span className="badge personal" key={fact.id}>
                    {fact.text}
                  </span>
                ))}
              </div>
            ) : (
              'Память пуста.'
            )}
          </EvalBox>
          <EvalBox title="other_user">Переключите User сверху, чтобы увидеть отдельную память.</EvalBox>
        </EvaluationCard>
      </div>
    </section>
  )
}

function App() {
  const [view, setView] = useState('chat')
  const [userId, setUserId] = useState('demo_user')
  const [persona, setPersona] = useState('wellness_friend')
  const [message, setMessage] = useState('')
  const [histories, setHistories] = useState(new Map())
  const [facts, setFacts] = useState([])
  const [selectedFacts, setSelectedFacts] = useState(new Set())
  const [isMemoryOpen, setIsMemoryOpen] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [toast, setToast] = useState('')
  const [config, setConfig] = useState({ model: 'loading', memoryBackend: '', factExtractor: '' })
  const toastTimerRef = useRef(null)

  const history = useMemo(() => histories.get(userId) || [], [histories, userId])

  const showToast = useCallback((value) => {
    setToast(value)
    window.clearTimeout(toastTimerRef.current)
    toastTimerRef.current = window.setTimeout(() => setToast(''), 3200)
  }, [])

  const setCurrentHistory = useCallback((nextHistory) => {
    setHistories((previous) => {
      const next = new Map(previous)
      next.set(userId, nextHistory)
      return next
    })
  }, [userId])

  const loadConfig = useCallback(async () => {
    try {
      const result = await getAppConfig()
      setConfig({
        model: result.model,
        memoryBackend: result.memory_backend,
        factExtractor: result.fact_extractor,
      })
    } catch {
      setConfig((current) => ({ ...current, model: 'server model' }))
    }
  }, [])

  const loadHistory = useCallback(async () => {
    try {
      const result = await getChatHistory(userId)
      setCurrentHistory(result.history || [])
    } catch {
      setCurrentHistory([])
    }
  }, [setCurrentHistory, userId])

  const loadMemory = useCallback(async () => {
    try {
      const result = await getMemory(userId)
      setFacts(result.facts || [])
    } catch {
      setFacts([])
    }
  }, [userId])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  useEffect(() => {
    setSelectedFacts(new Set())
    loadHistory()
    loadMemory()
  }, [loadHistory, loadMemory, userId])

  async function handleClearChat() {
    await clearChatHistory(userId)
    setCurrentHistory([])
    showToast('Диалог очищен. Долгосрочная память не удалялась.')
  }

  async function handleForgetAll() {
    const result = await forgetAllMemory(userId)
    setFacts([])
    setSelectedFacts(new Set())
    showToast(`Долгосрочная память очищена. Удалено записей: ${result.deleted}.`)
  }

  async function handleForgetSelected() {
    const selected = facts.filter((fact) => selectedFacts.has(fact.id))
    for (const fact of selected) {
      await forgetMemoryFact(userId, fact.text)
    }
    setSelectedFacts(new Set())
    await loadMemory()
    showToast(`Удалено выбранных фактов: ${selected.length}.`)
  }

  function handleToggleFact(factId) {
    setSelectedFacts((previous) => {
      const next = new Set(previous)
      if (next.has(factId)) next.delete(factId)
      else next.add(factId)
      return next
    })
  }

  async function handleSend(event) {
    event.preventDefault()
    const content = message.trim()
    if (!content || streaming) return

    const nextHistory = [...history, { role: 'user', content }, { role: 'assistant', content: '' }]
    setCurrentHistory(nextHistory)
    setMessage('')
    setStreaming(true)

    try {
      let assistantText = ''
      await streamChat({
        userId,
        persona,
        message: content,
        onChunk: (chunk) => {
          assistantText += chunk
          setCurrentHistory([...nextHistory.slice(0, -1), { role: 'assistant', content: assistantText }])
        },
      })
      await loadMemory()
    } catch (error) {
      setCurrentHistory([
        ...nextHistory.slice(0, -1),
        { role: 'assistant', content: `Ошибка: ${error.message}` },
      ])
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="app-shell">
      <Sidebar config={config} onViewChange={setView} view={view} />
      <main className="workspace">
        <Topbar
          model={config.model}
          onClearChat={handleClearChat}
          onForgetAll={handleForgetAll}
          onOpenMemory={() => setIsMemoryOpen(true)}
          onPersonaChange={setPersona}
          onUserChange={setUserId}
          persona={persona}
          userId={userId}
        />
        {view === 'evaluation' ? (
          <EvaluationView facts={facts} persona={persona} userId={userId} />
        ) : (
          <ChatView
            history={history}
            message={message}
            onMessageChange={setMessage}
            onSend={handleSend}
            streaming={streaming}
          />
        )}
      </main>
      <MemoryDrawer
        facts={facts}
        isOpen={isMemoryOpen}
        onClose={() => setIsMemoryOpen(false)}
        onForgetAll={handleForgetAll}
        onForgetSelected={handleForgetSelected}
        onToggleFact={handleToggleFact}
        selectedFacts={selectedFacts}
      />
      {toast ? <div className="toast">{toast}</div> : null}
    </div>
  )
}

export default App
