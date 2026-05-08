import { PlusCircle } from 'lucide-react'

const PERSONAS = [
    { id: 'wellness_friend', label: 'Wellness friend' },
    { id: 'tough_love', label: 'Tough love' }
]

export default function Topbar({
    model,
    userId,
    persona,
    onPersonaChange,
    onClearChat,
}) {
    return (
        <div className="topbar">
            <div className="selectors">
                <div className="field">
                    <span className="field-label">User:</span>
                    <strong className="user-name">{userId}</strong>
                </div>

                <div className="persona-switch">
                    <span className="field-label">Persona:</span>
                    <div className="persona-buttons">
                        {PERSONAS.map((p) => (
                            <button
                                key={p.id}
                                className={`persona-btn ${persona === p.id ? 'active' : ''}`}
                                onClick={() => onPersonaChange(p.id)}
                                type="button"
                            >
                                <span className="persona-icon">{p.icon}</span>
                                <span>{p.label}</span>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="field">
                    <span className="field-label">Model:</span>
                    <span className="model-pill">{model || 'loading'}</span>
                </div>
            </div>

            <div className="actions">
                <button className="button primary" onClick={onClearChat} type="button">
                    <PlusCircle size={17} />
                    Новый чат
                </button>
            </div>
        </div>
    )
}