import { useState } from 'react'
import appIcon from '../assets/app_icon.png'

export default function LoginForm({ onLogin }) {
    const [name, setName] = useState('')

    const handleSubmit = (e) => {
        e.preventDefault()
        const trimmed = name.trim()
        if (trimmed) onLogin(trimmed)
    }

    return (
        <div className="login-container">
            <div className="login-card">
                <div className="brand">
                    <img className="brand-mark" src={appIcon} alt="Mindly" />
                    <div>
                        <div className="brand-title">Mindly</div>
                        <div className="brand-subtitle">memory agent</div>
                    </div>
                </div>
                <p>Введите ваше имя, чтобы начать</p>
                <form onSubmit={handleSubmit}>
                    <input
                        type="text"
                        placeholder="Ваше имя"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        autoFocus
                    />
                    <button type="submit">Войти</button>
                </form>
            </div>
        </div>
    )
}