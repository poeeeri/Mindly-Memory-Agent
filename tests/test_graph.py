import pytest

from app.config import Settings
from app.graph import MindlyGraph, make_initial_state
from app.llm import OpenRouterClient
from app.memory import DummyMemory


# Проверяет, что граф генерирует ответ, сохраняет память
@pytest.mark.asyncio
async def test_graph_generates_and_saves_memory() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(
        memory=memory,
        llm=OpenRouterClient(Settings(use_fake_llm=True)),
    )

    state = make_initial_state(
        user_id="user_1",
        persona="wellness_friend",
        message="У меня сын Костик",
    )
    result = await graph.ainvoke(state)

    assert result["response"]
    assert memory.search("user_1", "Костик") == ["У меня сын Костик"]


# Проверяет, что память сохраняется при смене персоны
@pytest.mark.asyncio
async def test_persona_switch_keeps_user_memory() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(memory=memory, llm=OpenRouterClient(Settings(use_fake_llm=True)))

    await graph.ainvoke(
        make_initial_state(user_id="user_1", persona="wellness_friend", message="У меня сын Костик")
    )
    result = await graph.prep_graph.ainvoke(
        make_initial_state(user_id="user_1", persona="tough_love", message="Что ты помнишь обо мне?")
    )

    assert "У меня сын Костик" in result["memories"]