from app.history import InMemoryChatHistoryStore, build_chat_history_store


def test_in_memory_history_keeps_recent_messages() -> None:
    store = InMemoryChatHistoryStore(max_messages=2)

    store.append_exchange("history_user", "hello", "hi")
    store.append_exchange("history_user", "how are you?", "fine")

    assert store.list("history_user") == [
        {"role": "user", "content": "how are you?"},
        {"role": "assistant", "content": "fine"},
    ]


def test_history_factory_builds_memory_store() -> None:
    store = build_chat_history_store(
        backend="memory",
        database_url="postgresql://unused",
        max_messages=4,
    )

    store.append_exchange("factory_user", "hello", "hi")

    assert store.window("factory_user", 1) == [{"role": "assistant", "content": "hi"}]