from app.memory import DummyMemory


def test_add_fact_stores_structured_record() -> None:
    memory = DummyMemory()

    memory.add_fact("user_1", "Пользователя зовут Анна.", source="extractor:profile")

    facts = memory.list_facts("user_1")
    assert facts[0].user_id == "user_1"
    assert facts[0].source == "extractor:profile"
    assert facts[0].text == "Пользователя зовут Анна."


def test_add_normalizes_fact_sentence() -> None:
    memory = DummyMemory()

    memory.add("user_1", "У пользователя есть сын Костик")

    assert memory.search("user_1", "Костик") == ["У пользователя есть сын Костик."]


def test_forget_removes_matching_fact() -> None:
    memory = DummyMemory()
    memory.add_fact("user_1", "У пользователя есть сын Костик.")

    assert memory.search("user_1", "Костик")
    assert memory.forget("user_1", "Костик") == 1
    assert memory.search("user_1", "Костик") == []