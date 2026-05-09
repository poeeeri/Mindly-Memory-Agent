from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4
from app.memory.extractor import (
    looks_like_recall_question,
    normalize_sentence,
    terms,
)
from app.memory.models import MemoryFact


class FactMemory:
    def __init__(self) -> None:
        self._facts: dict[str, list[MemoryFact]] = defaultdict(list)
        self._forbidden_topics: dict[str, list[str]] = defaultdict(list)

    def search(self, user_id: str, query: str) -> list[str]:
        facts = self._facts.get(user_id, [])
        if not query.strip():
            return [fact.text for fact in facts[-5:]]

        query_terms = terms(query)
        scored: list[tuple[int, MemoryFact]] = []
        for fact in facts:
            score = len(query_terms & terms(fact.text))
            if score > 0:
                scored.append((score, fact))

        if not scored and looks_like_recall_question(query):
            return [fact.text for fact in facts[-5:]]

        ranked = sorted(scored, key=lambda pair: pair[0], reverse=True)
        return [fact.text for _, fact in ranked[:5]]

    def add(self, user_id: str, text: str) -> None:
        self.add_fact(user_id=user_id, fact_text=text)

    def add_fact(self, user_id: str, fact_text: str, source: str = "user_message") -> None:
        normalized = normalize_sentence(fact_text)
        if not normalized:
            return
        if any(fact.text == normalized for fact in self._facts[user_id]):
            return

        self._facts[user_id].append(
            MemoryFact(
                id=str(uuid4()),
                user_id=user_id,
                text=normalized,
                source=source,
                created_at=datetime.now(timezone.utc),
            )
        )

    def add_forbidden_topic(self, user_id: str, topic: str) -> bool:
        normalized = normalize_sentence(topic)
        if not normalized:
            return False
        if normalized in self._forbidden_topics[user_id]:
            return False
        self._forbidden_topics[user_id].append(normalized)
        return True

    def list_forbidden_topics(self, user_id: str) -> list[str]:
        return list(self._forbidden_topics.get(user_id, []))

    def forget(self, user_id: str, query: str) -> int:
        query_terms = terms(query)
        before = len(self._facts.get(user_id, []))
        if not query_terms:
            return 0

        self._facts[user_id] = [
            fact for fact in self._facts[user_id] if not query_terms.intersection(terms(fact.text))
        ]
        return before - len(self._facts[user_id])

    def forget_all(self, user_id: str) -> int:
        count = len(self._facts.get(user_id, [])) + len(self._forbidden_topics.get(user_id, []))
        self._facts[user_id].clear()
        self._forbidden_topics[user_id].clear()
        return count

    def list_facts(self, user_id: str) -> list[MemoryFact]:
        return list(self._facts.get(user_id, []))

    _terms = staticmethod(terms)