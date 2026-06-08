from fastapi.testclient import TestClient

from app.main import app, chat_history, memory, mindly_graph
from app.memory.extractor import ExtractedFact


class StubFactExtractor:
    async def extract(self, message: str) -> list[ExtractedFact]:
        return [ExtractedFact(text="The user prefers quiet evenings.", kind="preference")]


def test_memory_debug_endpoint_lists_structured_facts() -> None:
    memory.forget_all("api_user")
    memory.add("api_user", "Меня зовут Анна")
    client = TestClient(app)

    response = client.get("/memory", params={"user_id": "api_user"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["facts"][0]["text"] == "Меня зовут Анна."
    assert payload["facts"][0]["source"] == "user_message"


def test_forget_all_endpoint_deletes_user_facts() -> None:
    memory.forget_all("api_user")
    chat_history.clear("api_user")
    memory.add("api_user", "У меня сын Костик")
    client = TestClient(app)

    response = client.delete("/memory/all", params={"user_id": "api_user"})

    assert response.status_code == 200
    assert response.json()["deleted"] == 1
    assert memory.search("api_user", "Костик") == []


def test_refresh_memory_endpoint_extracts_facts_from_chat_history() -> None:
    memory.forget_all("refresh_user")
    chat_history.clear("refresh_user")
    chat_history.append_exchange("refresh_user", "I prefer quiet evenings", "Noted.")
    original_extractor = mindly_graph.fact_extractor
    mindly_graph.fact_extractor = StubFactExtractor()
    client = TestClient(app)

    try:
        response = client.post("/memory/refresh", params={"user_id": "refresh_user"})
    finally:
        mindly_graph.fact_extractor = original_extractor

    assert response.status_code == 200
    assert response.json() == {"added": 1, "processed_messages": 1}
    assert memory.search("refresh_user", "quiet evenings") == ["The user prefers quiet evenings."]