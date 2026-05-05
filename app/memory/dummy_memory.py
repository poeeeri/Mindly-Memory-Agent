from collections import defaultdict
import re


class DummyMemory:
    def __init__(self) -> None:
        # здесь хранятся данные
        self._items: dict[str, list[str]] = defaultdict(list)

    def search(self, user_id: str, query: str) -> list[str]:
        items = self._items.get(user_id, [])
        if not query.strip():
            return items[-5:]

        query_terms = self._terms(query)
        scored: list[tuple[int, str]] = []
        for item in items:
            score = len(query_terms & self._terms(item))
            if score > 0:
                scored.append((score, item))

        if not scored and self._looks_like_recall_question(query):
            return items[-5:]

        return [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)[:5]]

    def add(self, user_id: str, text: str) -> None:
        normalized = text.strip()
        if not normalized or normalized in self._items[user_id]:
            return
        self._items[user_id].append(normalized)

    def forget(self, user_id: str, query: str) -> int:
        terms = self._terms(query)
        before = len(self._items.get(user_id, []))
        if not terms:
            return 0
        self._items[user_id] = [
            item for item in self._items[user_id] if not terms.intersection(self._terms(item))
        ]
        return before - len(self._items[user_id])

    def forget_all(self, user_id: str) -> int:
        count = len(self._items.get(user_id, []))
        self._items[user_id].clear()
        return count

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {term.lower() for term in re.findall(r"[\w']{3,}", text, flags=re.UNICODE)}

    @staticmethod
    def _looks_like_recall_question(text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in ("remember", "помни", "знаешь обо мне", "обо мне"))
