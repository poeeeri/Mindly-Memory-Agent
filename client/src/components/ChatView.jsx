import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Bot, Send, UserRound } from 'lucide-react'

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

export default function ChatView({ history, message, onMessageChange, onSend, streaming }) {
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
                                key={`${item.role}-${index}`}
                                item={item}
                                streaming={streaming && index === history.length - 1 && item.role === 'assistant'}
                            />
                        ))
                    ) : (
                        <div className="empty">
                            Вы пока ничего не писали агенту. Начните, отправив первое сообщение
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>

                <form className="composer" onSubmit={onSend}>
                    <textarea
                        disabled={streaming}
                        value={message}
                        onChange={(e) => onMessageChange(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault()
                                e.currentTarget.form?.requestSubmit()
                            }
                        }}
                        placeholder="Напишите сообщение..."
                    />
                    <button className="icon-button primary" disabled={streaming} type="submit">
                        <Send size={18} />
                    </button>
                </form>
            </section>
        </div>
    )
}