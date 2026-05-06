from app.memory import DummyMemory, FactMemory


def test_fact_extraction_creates_atomic_fact() -> None:
    facts = FactMemory.extract_facts("У меня сын Костик, он недавно пошел в школу.")

    assert "У пользователя есть сын Костик." in facts
    assert "Костик недавно пошел в школу." in facts


def test_forget_removes_matching_fact() -> None:
    memory = DummyMemory()
    memory.add("user_1", "У меня сын Костик")

    assert memory.search("user_1", "Костик")
    assert memory.forget("user_1", "Костик") == 1
    assert memory.search("user_1", "Костик") == []


def test_list_facts_returns_structured_records() -> None:
    memory = DummyMemory()
    memory.add("user_1", "Меня зовут Анна")

    facts = memory.list_facts("user_1")

    assert facts[0].user_id == "user_1"
    assert facts[0].source == "user_message"
    assert facts[0].text == "Пользователя зовут Анна."