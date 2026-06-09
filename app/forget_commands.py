from app.constants import FORGET_ALL_MESSAGES, FORGET_RESPONSE_TEMPLATE
from app.memory.base import MemoryStore


def is_forget_all_message(message: str) -> bool:
    return message.strip().lower() in FORGET_ALL_MESSAGES


def try_handle_forget_all(
    *,
    user_id: str,
    message: str,
    memory: MemoryStore,
    on_forget_all,
) -> dict | None:
    if not is_forget_all_message(message):
        return None
    memory_deleted = memory.forget_all(user_id)
    history_deleted = on_forget_all(user_id) if on_forget_all else 0
    deleted = memory_deleted + history_deleted
    return {
        "forget_command": "all",
        "response": FORGET_RESPONSE_TEMPLATE.format(deleted=deleted),
    }


def try_handle_forget_query(*, user_id: str, query: str, memory: MemoryStore) -> dict:
    deleted = memory.forget(user_id, query)
    return {
        "forget_command": query,
        "response": FORGET_RESPONSE_TEMPLATE.format(deleted=deleted),
    }