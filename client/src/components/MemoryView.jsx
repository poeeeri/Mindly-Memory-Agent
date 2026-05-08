import { Trash2, X } from 'lucide-react'
import { formatTime, factKind } from '../utils/helpers'

function MemoryCard({ fact, isSelected, onToggle, onDelete }) {
    const kind = factKind(fact)

    return (
        <article className="memory-card">
            <div className="memory-card-header">
                <label className="memory-checkbox">
                    <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggle(fact.id)}
                    />
                    <span className="memory-card-title">{fact.text}</span>
                </label>
                <button
                    className="memory-card-delete"
                    onClick={() => onDelete(fact)}
                    title="Забыть этот факт"
                >
                    <Trash2 size={14} />
                </button>
            </div>
            <div className="memory-card-meta">
                <span className={`badge ${kind}`}>{kind}</span>
                <span className="badge">{fact.source || 'memory'}</span>
                <span className="badge">{formatTime(fact.created_at)}</span>
            </div>
        </article>
    )
}

export default function MemoryView({
    facts,
    selectedFacts,
    onToggleFact,
    onForgetSelected,
    onForgetAll,
    onForgetSingle
}) {
    const hasFacts = facts.length > 0
    const hasSelected = selectedFacts.size > 0

    return (
        <section>
            <div className="memory-header">
                <div>
                    <h1 className="page-title">Долгосрочная память</h1>
                    <p className="page-subtitle">
                        Факты пользователя, которые агент запомнил. Их можно удалять по одному или группами.
                        <br />
                        <span className="hint">
                            Агент использует эти факты между сессиями, чтобы помнить вас и ваш контекст.
                        </span>
                    </p>
                </div>
                <div className="memory-header-actions">
                    <button
                        className="button danger"
                        onClick={onForgetAll}
                        disabled={!hasFacts}
                    >
                        <Trash2 size={17} />
                        Удалить всю память
                    </button>
                    <button
                        className="button"
                        onClick={onForgetSelected}
                        disabled={!hasSelected}
                    >
                        <X size={17} />
                        Забыть выбранное ({selectedFacts.size})
                    </button>
                </div>
            </div>

            {hasFacts ? (
                <div className="memory-grid">
                    {facts.map((fact) => (
                        <MemoryCard
                            key={fact.id}
                            fact={fact}
                            isSelected={selectedFacts.has(fact.id)}
                            onToggle={onToggleFact}
                            onDelete={onForgetSingle}
                        />
                    ))}
                </div>
            ) : (
                <div className="empty-memory">
                    <div className="empty-memory-icon">🧠</div>
                    <div className="empty-memory-text">
                        <strong>Память пуста</strong>
                        <br />
                        Напишите что-нибудь агенту, и он запомнит важное о вас.
                    </div>
                </div>
            )}
        </section>
    )
}