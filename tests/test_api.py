from fastapi.testclient import TestClient

from app.main import app, memory


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
    memory.add("api_user", "У меня сын Костик")
    client = TestClient(app)

    response = client.delete("/memory/all", params={"user_id": "api_user"})

    assert response.status_code == 200
    assert response.json()["deleted"] == 1
    assert memory.search("api_user", "Костик") == []