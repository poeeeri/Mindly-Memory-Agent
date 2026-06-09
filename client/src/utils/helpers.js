export function formatTime(value) {
    if (!value) return 'сейчас'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return 'сейчас'
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

export function factKind(fact) {
    if (fact.source?.includes(':')) return fact.source.split(':').pop()
    if (/работ|стресс|тревог|deadline|дедлайн/i.test(fact.text)) return 'situation'
    if (/хочет|цель|план/i.test(fact.text)) return 'goal'
    return 'personal'
}