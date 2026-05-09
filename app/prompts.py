from app.state import ChatMessage


PERSONA_PROMPTS = {
    "wellness_friend": (
        "You are Mindly, a warm wellness coach. Be supportive, concrete, and brief. "
        "Do not diagnose. Ask at most one gentle follow-up question."
    ),
    "tough_love": (
        "You are Mindly, a direct accountability coach. Be kind but firm, practical, "
        "and concise. Focus on the next useful action."
    ),
}


DEFAULT_PERSONA = "wellness_friend"


def get_persona_prompt(persona: str) -> str:
    return PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS[DEFAULT_PERSONA])


def build_prompt(
    *,
    persona: str,
    memories: list[str],
    forbidden_topics: list[str] | None = None,
    history: list[ChatMessage],
    message: str,
) -> list[ChatMessage]:
    memory_block = "\n".join(f"- {item}" for item in memories) if memories else "- No stored facts yet."
    forbidden_block = (
        "\n".join(f"- {item}" for item in forbidden_topics)
        if forbidden_topics
        else "- No forbidden topics."
    )
    system_prompt = (
        f"{get_persona_prompt(persona)}\n\n"
        "Relevant long-term memory for this user:\n"
        f"{memory_block}\n\n"
        "Topics the user asked not to bring up:\n"
        f"{forbidden_block}\n\n"
        "Do not proactively mention, ask about, or steer the conversation toward forbidden topics. "
        "Use memory only when it is relevant. Never reveal memory from other users."
    )
    return [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": message},
    ]