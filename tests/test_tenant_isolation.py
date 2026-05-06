from app.memory import DummyMemory


# Проверяет, что user_2 не видит память user_1
def test_dummy_memory_is_scoped_by_user_id() -> None:
    memory = DummyMemory()
    memory.add_fact("user_1", "У пользователя есть сын Костик.")

    assert memory.search("user_1", "Костик") == ["У пользователя есть сын Костик."]
    assert memory.search("user_2", "Костик") == []