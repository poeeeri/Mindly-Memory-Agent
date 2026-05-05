from app.memory import DummyMemory


# Проверяет forget
def test_forget_removes_matching_fact() -> None:
    memory = DummyMemory()
    memory.add("user_1", "У меня сын Костик")

    assert memory.search("user_1", "Костик")
    assert memory.forget("user_1", "Костик") == 1
    assert memory.search("user_1", "Костик") == []