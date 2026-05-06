from app.memory import MemPalaceMemory


def test_mempalace_memory_persists_facts(tmp_path) -> None:
    palace_path = tmp_path / "palace"

    memory = MemPalaceMemory(palace_path=str(palace_path), collection_name="test_facts")
    memory.add_fact("user_1", "У пользователя есть сын Костик.")

    reopened = MemPalaceMemory(palace_path=str(palace_path), collection_name="test_facts")

    assert reopened.search("user_1", "Костик") == ["У пользователя есть сын Костик."]
    assert reopened.search("user_2", "Костик") == []


def test_mempalace_forget_all_deletes_only_user(tmp_path) -> None:
    palace_path = tmp_path / "palace"
    memory = MemPalaceMemory(palace_path=str(palace_path), collection_name="test_facts")
    memory.add_fact("user_1", "У пользователя есть сын Костик.")
    memory.add_fact("user_2", "У пользователя есть дочь Анна.")

    assert memory.forget_all("user_1") == 1

    assert memory.search("user_1", "Костик") == []
    assert memory.search("user_2", "Анна") == ["У пользователя есть дочь Анна."]