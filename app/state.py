from typing import Literal
from typing_extensions import TypedDict


class ChatMessage(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


class AgentState(TypedDict, total=False):
    user_id: str
    persona: str
    message: str
    history: list[ChatMessage]
    forget_command: str | None
    memories: list[str]
    forbidden_topics: list[str]
    prompt_messages: list[ChatMessage]
    response: str
    ttft_ms: float | None