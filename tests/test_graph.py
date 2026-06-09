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


@pytest.mark.asyncio
async def test_graph_generates_without_auto_saving_memory() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(
        memory=memory,
        llm=OpenRouterClient(Settings(use_fake_llm=True)),
        fact_extractor=StubFactExtractor(
            [ExtractedFact(text="The user has a son named Kostik.", kind="relationship")]
        ),
    )

    state = make_initial_state(
        user_id="user_1",
        persona="wellness_friend",
        message="I have a son named Kostik",
    )
    result = await graph.ainvoke(state)

    assert result["response"]
    assert memory.search("user_1", "Kostik") == []


@pytest.mark.asyncio
async def test_save_memory_can_be_called_explicitly() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(
        memory=memory,
        llm=OpenRouterClient(Settings(use_fake_llm=True)),
        fact_extractor=StubFactExtractor(
            [ExtractedFact(text="The user has a son named Kostik.", kind="relationship")]
        ),
    )

    await graph.save_memory(
        make_initial_state(
            user_id="user_1",
            persona="wellness_friend",
            message="I have a son named Kostik",
        )
    )

    assert memory.search("user_1", "Kostik") == ["The user has a son named Kostik."]


@pytest.mark.asyncio
async def test_graph_does_not_save_when_extractor_returns_no_facts() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(
        memory=memory,
        llm=OpenRouterClient(Settings(use_fake_llm=True)),
        fact_extractor=StubFactExtractor([]),
    )

    await graph.save_memory(
        make_initial_state(user_id="user_1", persona="wellness_friend", message="hello")
    )

    assert memory.list_facts("user_1") == []


@pytest.mark.asyncio
async def test_persona_switch_keeps_user_memory() -> None:
    memory = DummyMemory()
    graph = MindlyGraph(
        memory=memory,
        llm=OpenRouterClient(Settings(use_fake_llm=True)),
        fact_extractor=StubFactExtractor(
            [ExtractedFact(text="The user has a son named Kostik.", kind="relationship")]
        ),
    )

    await graph.save_memory(
        make_initial_state(user_id="user_1", persona="wellness_friend", message="I have a son named Kostik")
    )
    result = await graph.prep_graph.ainvoke(
        make_initial_state(user_id="user_1", persona="tough_love", message="What do you remember about me?")
    )

    assert "The user has a son named Kostik." in result["memories"]
