from typing import Protocol
from app.memory.models import MemoryFact


class MemoryStore(Protocol):
    def search(self, user_id: str, query: str) -> list[str]:
        ...

    def add(self, user_id: str, text: str) -> None:
        ...

    def forget(self, user_id: str, query: str) -> int:
        ...

    def forget_all(self, user_id: str) -> int:
        ...

    def list_facts(self, user_id: str) -> list[MemoryFact]:
        ...