import { MessageCircle, Database, BarChart3, LogOut } from 'lucide-react'
import appIcon from '../assets/app_icon.png'

export default function Sidebar({ view, onViewChange, onLogout }) {
    const items = [
        { key: 'chat', icon: MessageCircle, label: 'Чат' },
        { key: 'memory', icon: Database, label: 'Память' },
        { key: 'evaluation', icon: BarChart3, label: 'Оценка' }
    ]

    return (
        <aside className="sidebar">
            <div className="brand">
                <img className="brand-mark" src={appIcon} alt="Mindly" />
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

            <div className="sidebar-footer"></div>

            <button className="logout-button" onClick={onLogout} type="button">
                <LogOut size={18} />
                <span>Выйти</span>
            </button>
        </aside>
    )
}
