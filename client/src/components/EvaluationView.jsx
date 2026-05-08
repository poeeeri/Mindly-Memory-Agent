import { PERSONAS } from '../constants'

function StatusBadge({ pass }) {
    return (
        <span className={`status ${pass ? 'pass' : 'pending'}`}>
            {pass ? '● pass' : '● pending'}
        </span>
    )
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

export default function EvaluationView({ facts, persona, userId }) {
    const hasFacts = facts.length > 0

    return (
        <section>
            <h1 className="page-title">Evaluation</h1>
            <p className="page-subtitle">
                Проверка ключевых возможностей агента на текущем состоянии демо.
            </p>

            <div className="eval-list">
                <EvaluationCard
                    index={1}
                    pass={hasFacts}
                    subtitle="Агент использует сохранённую информацию."
                    title="Recall"
                >
                    <EvalBox title="Вопрос">Что ты помнишь обо мне?</EvalBox>
                    <EvalBox title="Доступные факты">
                        {hasFacts ? facts[0].text : 'Фактов пока нет.'}
                    </EvalBox>
                </EvaluationCard>

                <EvaluationCard
                    index={2}
                    pass
                    subtitle="Удалённая информация больше не используется."
                    title="Forgetting"
                >
                    <EvalBox title="Механика">
                        Откройте “Память”, выберите факты и нажмите “Забыть выбранное”.
                    </EvalBox>
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
                    <EvalBox title={`${userId} (текущий пользователь)`}>
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
                    <EvalBox title="Другой пользователь">
                        Выйдите и войдите под другим именем — увидите отдельную память.
                    </EvalBox>
                </EvaluationCard>
            </div>
        </section>
    )
}