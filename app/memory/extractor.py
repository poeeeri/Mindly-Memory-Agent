from __future__ import annotations
import json
import re
from typing import Protocol
from pydantic import BaseModel, Field, ValidationError
from app.llm import OpenRouterClient
from app.state import ChatMessage


class FactExtractionError(RuntimeError):
    pass


class ExtractedFact(BaseModel):
    text: str = Field(min_length=1)
    kind: str = "profile"
    confidence: float = 1.0


class FactExtractionResult(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list)


class FactExtractor(Protocol):
    async def extract(self, message: str) -> list[ExtractedFact]:
        ...


class LLMFactExtractor:
    def __init__(self, *, llm: OpenRouterClient) -> None:
        self.llm = llm

    async def extract(self, message: str) -> list[ExtractedFact]:
        prompt: list[ChatMessage] = [
            {
                "role": "system",
                "content": (
                    "You extract long-term user memory facts for a wellness coaching assistant.\n"
                    "Return only valid JSON with this exact schema:\n"
                    '{"facts":[{"text":"...","kind":"profile|relationship|goal|preference|work|wellbeing|boundary","confidence":0.0}]}\n'
                    "Extract only durable facts, preferences, goals, relationships, boundaries, work context, "
                    "wellbeing patterns, and coping strategies.\n"
                    "Do not store greetings, random typos, one-off small talk, or the assistant's advice.\n"
                    "Write fact text in Russian, in third person, starting with 'Пользователь...' when appropriate.\n"
                    "If there is no useful long-term memory, return {\"facts\":[]}."
                ),
            },
            {"role": "user", "content": message},
        ]
        raw_response = await self.llm.complete_chat(prompt)
        return self._parse_response(raw_response)

    @staticmethod
    def _parse_response(raw_response: str) -> list[ExtractedFact]:
        payload = _extract_json_object(raw_response)
        try:
            result = FactExtractionResult.model_validate_json(payload)
        except (ValidationError, ValueError) as exc:
            raise FactExtractionError(str(exc)) from exc
        return [fact for fact in result.facts if fact.text.strip()]


def normalize_sentence(text: str) -> str:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return ""
    return normalized if normalized.endswith((".", "!", "?")) else f"{normalized}."


def terms(text: str) -> set[str]:
    return {term.lower() for term in re.findall(r"[\w']{3,}", text, flags=re.UNICODE)}


def looks_like_recall_question(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ("remember", "помни", "знаешь обо мне", "обо мне"))


def _extract_json_object(raw_response: str) -> str:
    stripped = raw_response.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise FactExtractionError("No JSON object found in fact extraction response.")
    return stripped[start : end + 1]