import re


FORGET_ALL_MESSAGES = {
    "/forget_all",
    "удали все мои данные",
    "забудь все обо мне",
}

FORGET_RESPONSE_TEMPLATE = "Готово, удалено записей: {deleted}."

FORBIDDEN_TOPIC_PATTERNS = [
    re.compile(r"^(?:/avoid|/do_not_mention)\s+(?P<topic>.+)$", flags=re.IGNORECASE),
    re.compile(r"^не\s+поднимай\s+тему\s+(?P<topic>.+)$", flags=re.IGNORECASE),
    re.compile(r"^не\s+говори\s+(?:со\s+мной\s+)?(?:про|о|об)\s+(?P<topic>.+)$", flags=re.IGNORECASE),
    re.compile(r"^не\s+спрашивай\s+(?:меня\s+)?(?:про|о|об)\s+(?P<topic>.+)$", flags=re.IGNORECASE),
]