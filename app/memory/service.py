from collections import defaultdict
from datetime import datetime, timezone
import re
from uuid import uuid4

from app.memory.models import MemoryFact


class FactMemory:
    def __init__(self) -> None:
        self._facts: dict[str, list[MemoryFact]] = defaultdict(list)

    def search(self, user_id: str, query: str) -> list[str]:
        facts = self._facts.get(user_id, [])
        if not query.strip():
            return [fact.text for fact in facts[-5:]]

        query_terms = self._terms(query)
        scored: list[tuple[int, MemoryFact]] = []
        for fact in facts:
            score = len(query_terms & self._terms(fact.text))
            if score > 0:
                scored.append((score, fact))

        if not scored and self._looks_like_recall_question(query):
            return [fact.text for fact in facts[-5:]]

        ranked = sorted(scored, key=lambda pair: pair[0], reverse=True)
        return [fact.text for _, fact in ranked[:5]]

    def add(self, user_id: str, text: str) -> None:
        for fact_text in self.extract_facts(text):
            self._add_fact(user_id=user_id, text=fact_text, source="user_message")

    def forget(self, user_id: str, query: str) -> int:
        terms = self._terms(query)
        before = len(self._facts.get(user_id, []))
        if not terms:
            return 0

        self._facts[user_id] = [
            fact for fact in self._facts[user_id] if not terms.intersection(self._terms(fact.text))
        ]
        return before - len(self._facts[user_id])

    def forget_all(self, user_id: str) -> int:
        count = len(self._facts.get(user_id, []))
        self._facts[user_id].clear()
        return count

    def list_facts(self, user_id: str) -> list[MemoryFact]:
        return list(self._facts.get(user_id, []))

    def _add_fact(self, *, user_id: str, text: str, source: str) -> None:
        normalized = self._normalize_sentence(text)
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

    @classmethod
    def extract_facts(cls, text: str) -> list[str]:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return []

        facts: list[str] = []
        lowered = normalized.lower()

        name = cls._match_first(normalized, r"(?:меня зовут|мое имя|моё имя)\s+([А-ЯA-Z][\w-]+)")
        if name:
            facts.append(f"Пользователя зовут {name}.")

        son = cls._match_first(normalized, r"у меня (?:есть )?сын\s+([А-ЯA-Z][\w-]+)")
        if son:
            facts.append(f"У пользователя есть сын {son}.")

        daughter = cls._match_first(normalized, r"у меня (?:есть )?дочь\s+([А-ЯA-Z][\w-]+)")
        if daughter:
            facts.append(f"У пользователя есть дочь {daughter}.")

        if "пош" in lowered and "школ" in lowered:
            child = son or daughter or cls._match_first(normalized, r"\b([А-ЯA-Z][\w-]+)\b")
            if child:
                facts.append(f"{child} недавно пошел в школу.")

        work = cls._match_first(normalized, r"я работаю\s+(.+?)(?:[.!?]|$)")
        if work:
            facts.append(f"Пользователь работает {work}.")

        goal = cls._match_first(normalized, r"я хочу\s+(.+?)(?:[.!?]|$)")
        if goal:
            facts.append(f"Пользователь хочет {goal}.")

        stress = cls._match_first(normalized, r"я (?:часто )?(?:тревожусь|переживаю|стрессую)(?:\s+(.+?))?(?:[.!?]|$)")
        if stress:
            facts.append(f"Пользователь испытывает стресс {stress}.".strip())
        elif any(marker in lowered for marker in ("тревожусь", "переживаю", "стрессую")):
            facts.append("Пользователь испытывает стресс или тревогу.")

        if facts:
            return list(dict.fromkeys(cls._normalize_sentence(fact) for fact in facts))

        return [cls._normalize_sentence(normalized)]

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {term.lower() for term in re.findall(r"[\w']{3,}", text, flags=re.UNICODE)}

    @staticmethod
    def _looks_like_recall_question(text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in ("remember", "помни", "знаешь обо мне", "обо мне"))

    @staticmethod
    def _match_first(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.UNICODE)
        if not match:
            return None
        return match.group(1).strip()

    @staticmethod
    def _normalize_sentence(text: str) -> str:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return ""
        return normalized if normalized.endswith((".", "!", "?")) else f"{normalized}."