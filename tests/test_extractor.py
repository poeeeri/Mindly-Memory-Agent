import pytest

from app.memory.extractor import FactExtractionError, LLMFactExtractor


class StubLLM:
    def __init__(self, response: str) -> None:
        self.response = response

    async def complete_chat(self, messages):
        return self.response


@pytest.mark.asyncio
async def test_llm_fact_extractor_parses_json() -> None:
    extractor = LLMFactExtractor(
        llm=StubLLM(
            '{"facts":[{"text":"У пользователя есть подруга Вика.","kind":"relationship","confidence":0.93}]}'
        )
    )

    facts = await extractor.extract("моя подруга Вика умеет играть в судоку")

    assert len(facts) == 1
    assert facts[0].text == "У пользователя есть подруга Вика."
    assert facts[0].kind == "relationship"


@pytest.mark.asyncio
async def test_llm_fact_extractor_parses_fenced_json() -> None:
    extractor = LLMFactExtractor(
        llm=StubLLM(
            '```json\n{"facts":[{"text":"Пользователь хочет играть в судоку.","kind":"preference","confidence":0.88}]}\n```'
        )
    )

    facts = await extractor.extract("хочу играть в судоку")

    assert [fact.text for fact in facts] == ["Пользователь хочет играть в судоку."]


@pytest.mark.asyncio
async def test_llm_fact_extractor_raises_on_invalid_json() -> None:
    extractor = LLMFactExtractor(llm=StubLLM("not json"))

    with pytest.raises(FactExtractionError):
        await extractor.extract("У пользователя есть сын Костик.")