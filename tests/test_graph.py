import pytest

from app.config import Settings
from app.graph import MindlyGraph, make_initial_state
from app.llm import OpenRouterClient
from app.memory import DummyMemory
from app.memory.extractor import ExtractedFact


class StubFactExtractor:
    def __init__(self, facts: list[ExtractedFact]) -> None:
        self.facts = facts

    async def extract(self, message: str) -> list[ExtractedFact]:
        return self.facts


# Проверяет, что граф генерирует ответ, сохраняет память
@pytest.mark.asyncio
async def test_graph_generates_and_saves_memory() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(
        memory=memory,
        llm=OpenRouterClient(Settings(use_fake_llm=True)),
        fact_extractor=StubFactExtractor(
            [ExtractedFact(text="У пользователя есть сын Костик.", kind="relationship")]
        ),
    )

    state = make_initial_state(
        user_id="user_1",
        persona="wellness_friend",
        message="У меня сын Костик",
    )
    result = await graph.ainvoke(state)

    assert result["response"]
    assert memory.search("user_1", "Костик") == ["У пользователя есть сын Костик."]


@pytest.mark.asyncio
async def test_graph_does_not_save_when_extractor_returns_no_facts() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(
        memory=memory,
        llm=OpenRouterClient(Settings(use_fake_llm=True)),
        fact_extractor=StubFactExtractor([]),
    )

    await graph.ainvoke(
        make_initial_state(user_id="user_1", persona="wellness_friend", message="привет")
    )

    assert memory.list_facts("user_1") == []


# Проверяет, что память сохраняется при смене персоны
@pytest.mark.asyncio
async def test_persona_switch_keeps_user_memory() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(
        memory=memory,
        llm=OpenRouterClient(Settings(use_fake_llm=True)),
        fact_extractor=StubFactExtractor(
            [ExtractedFact(text="У пользователя есть сын Костик.", kind="relationship")]
        ),
    )

    await graph.ainvoke(
        make_initial_state(user_id="user_1", persona="wellness_friend", message="У меня сын Костик")
    )
    result = await graph.prep_graph.ainvoke(
        make_initial_state(user_id="user_1", persona="tough_love", message="Что ты помнишь обо мне?")
    )

    assert "У пользователя есть сын Костик." in result["memories"]