from app.memory.base import MemoryStore


class MemPalaceMemory:
    """Placeholder for the real MemPalace-backed implementation."""

    def __init__(self) -> None:
        raise NotImplementedError("MemPalace integration is planned after DummyMemory MVP.")

    def search(self, user_id: str, query: str) -> list[str]:
        raise NotImplementedError

    def add(self, user_id: str, text: str) -> None:
        raise NotImplementedError

    def forget(self, user_id: str, query: str) -> int:
        raise NotImplementedError

    def forget_all(self, user_id: str) -> int:
        raise NotImplementedError


def ensure_memory_contract(memory: MemoryStore) -> MemoryStore:
    return memory
