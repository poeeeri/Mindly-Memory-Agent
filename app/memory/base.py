from typing import Protocol
from app.memory.models import MemoryFact


class MemoryStore(Protocol):
    def search(self, user_id: str, query: str) -> list[str]:
        ...

    def add(self, user_id: str, text: str) -> None:
        ...

    def add_fact(self, user_id: str, fact_text: str, source: str = "user_message") -> None:
        ...

    def add_forbidden_topic(self, user_id: str, topic: str) -> bool:
        ...

    def list_forbidden_topics(self, user_id: str) -> list[str]:
        ...

    def forget(self, user_id: str, query: str) -> int:
        ...

    def forget_all(self, user_id: str) -> int:
        ...

    def list_facts(self, user_id: str) -> list[MemoryFact]:
        ...