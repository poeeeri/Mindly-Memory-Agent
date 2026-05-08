import { MessageCircle, Database, BarChart3, LogOut } from 'lucide-react'

export default function Sidebar({ view, onViewChange, config, onLogout }) {
    const items = [
        { key: 'chat', icon: MessageCircle, label: 'Чат' },
        { key: 'memory', icon: Database, label: 'Память' },
        { key: 'evaluation', icon: BarChart3, label: 'Оценка' }
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
                {items.map(({ key, icon: Icon, label }) => (
                    <button
                        key={key}
                        className={`nav-button ${view === key ? 'active' : ''}`}
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

            <button className="logout-button" onClick={onLogout} type="button">
                <LogOut size={18} />
                <span>Выйти</span>
            </button>
        </aside>
    )
}