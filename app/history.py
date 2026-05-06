from __future__ import annotations

from collections import defaultdict

from app.state import ChatMessage


class ChatHistoryStore:
    def __init__(self, *, max_messages: int = 50) -> None:
        self.max_messages = max_messages
        self._history: dict[str, list[ChatMessage]] = defaultdict(list)

    def list(self, user_id: str) -> list[ChatMessage]:
        return list(self._history.get(user_id, []))

    def window(self, user_id: str, size: int) -> list[ChatMessage]:
        return self.list(user_id)[-size:]

    def append_exchange(self, user_id: str, user_message: str, assistant_message: str) -> None:
        self._history[user_id].extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )
        self._history[user_id] = self._history[user_id][-self.max_messages :]

    def clear(self, user_id: str) -> int:
        count = len(self._history.get(user_id, []))
        self._history[user_id].clear()
        return count