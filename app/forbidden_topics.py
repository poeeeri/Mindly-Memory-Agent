from app.constants import FORBIDDEN_TOPIC_PATTERNS
from app.memory.extractor import terms


def extract_forbidden_topic(message: str) -> str | None:
    for pattern in FORBIDDEN_TOPIC_PATTERNS:
        match = pattern.match(message.strip())
        if match:
            return match.group("topic").strip(" .,!?:;\"'«»")
    return None


def filter_forbidden_memories(memories: list[str], forbidden_topics: list[str]) -> list[str]:
    forbidden_terms = set().union(*(terms(topic) for topic in forbidden_topics)) if forbidden_topics else set()
    if not forbidden_terms:
        return memories
    return [memory for memory in memories if not forbidden_terms.intersection(terms(memory))]


def build_forbidden_topic_response(topic: str, *, created: bool) -> str:
    action = "добавлена" if created else "уже была добавлена"
    return f"Понял, тема «{topic}» {action} в список тем, которые я не буду поднимать."