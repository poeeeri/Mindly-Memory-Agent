import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.forget_commands import is_forget_all_message
from app.graph import MindlyGraph, make_initial_state
from app.history import build_chat_history_store
from app.llm import OpenRouterClient
from app.logging_config import configure_logging
from app.memory.factory import build_fact_extractor, build_memory
from app.memory.models import MemoryFact
from app.state import ChatMessage

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client_dist_dir = Path(__file__).resolve().parent.parent / "client" / "dist"
client_assets_dir = client_dist_dir / "assets"
if client_assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=client_assets_dir), name="assets")


# рассказать про стриминг ответа
llm_client = OpenRouterClient(settings)

# реализация long-term памяти 
memory = build_memory(settings)
chat_history = build_chat_history_store(
    backend=settings.chat_history_backend,
    database_url=settings.database_url,
    max_messages=settings.chat_history_max_messages,
)

# рассказать про граф и как он работает, как происходит генерация ответа и сохранение в память
mindly_graph = MindlyGraph(
    memory=memory,
    llm=llm_client,
    fact_extractor=build_fact_extractor(settings, llm_client),
    history_window=settings.history_window,
    on_forget_all=chat_history.clear,
)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    persona: str = "wellness_friend"
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class ForgetResult(BaseModel):
    deleted: int


class MemoryRefreshResult(BaseModel):
    added: int
    processed_messages: int


class ChatHistoryResponse(BaseModel):
    history: list[ChatMessage]


class AppConfigResponse(BaseModel):
    model: str
    memory_backend: str
    fact_extractor: str


class MemoryListResponse(BaseModel):
    facts: list[MemoryFact]
    forbidden_topics: list[str] = Field(default_factory=list)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(client_dist_dir / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/app-config")
async def app_config() -> AppConfigResponse:
    return AppConfigResponse(
        model=settings.openrouter_model,
        memory_backend=settings.memory_backend,
        fact_extractor=settings.fact_extractor,
    )


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    stored_history = chat_history.window(request.user_id, settings.history_window)
    request_history = request.history[-settings.history_window :] if request.history else []
    state = make_initial_state(
        user_id=request.user_id,
        persona=request.persona,
        message=request.message,
        history=stored_history or request_history,
    )
    logger.info("chat.start user_id=%s persona=%s", request.user_id, request.persona)
    return StreamingResponse(
        _stream_chat_and_save_history(request.user_id, request.message, state),
        media_type="text/plain; charset=utf-8",
    )


async def _stream_chat_and_save_history(
    user_id: str,
    user_message: str,
    state: dict,
) -> AsyncIterator[str]:
    chunks: list[str] = []
    async for chunk in mindly_graph.astream_response(state):
        chunks.append(chunk)
        yield chunk

    assistant_message = "".join(chunks).strip()
    if assistant_message:
        if is_forget_all_message(user_message):
            logger.info("chat.history.skip_append_after_forget_all user_id=%s", user_id)
            return
        chat_history.append_exchange(user_id, user_message, assistant_message)
        logger.info("chat.history.append user_id=%s messages=%s", user_id, len(chat_history.list(user_id)))
        if settings.memory_refresh_mode.strip().lower() == "every_message":
            await mindly_graph.save_memory(
                make_initial_state(
                    user_id=user_id,
                    persona=state.get("persona", "wellness_friend"),
                    message=user_message,
                    history=[],
                )
            )
            logger.info("memory.refresh.every_message user_id=%s", user_id)


@app.get("/chat/history")
async def list_chat_history(user_id: str) -> ChatHistoryResponse:
    history = chat_history.list(user_id)
    logger.info("chat.history.list user_id=%s count=%s", user_id, len(history))
    return ChatHistoryResponse(history=history)


@app.delete("/chat/history")
async def clear_chat_history(user_id: str) -> ForgetResult:
    deleted = chat_history.clear(user_id)
    logger.info("chat.history.clear user_id=%s deleted=%s", user_id, deleted)
    return ForgetResult(deleted=deleted)


@app.post("/chat/new")
async def start_new_chat(user_id: str) -> ForgetResult:
    deleted = chat_history.clear(user_id)
    logger.info("chat.new user_id=%s deleted=%s", user_id, deleted)
    return ForgetResult(deleted=deleted)


@app.delete("/memory")
async def forget_memory(user_id: str, query: str) -> ForgetResult:
    deleted = memory.forget(user_id, query)
    logger.info("memory.forget user_id=%s deleted=%s", user_id, deleted)
    return ForgetResult(deleted=deleted)


@app.get("/memory")
async def list_memory(user_id: str) -> MemoryListResponse:
    facts = memory.list_facts(user_id)
    forbidden_topics = memory.list_forbidden_topics(user_id)
    logger.info(
        "memory.list user_id=%s count=%s forbidden_topics=%s",
        user_id,
        len(facts),
        len(forbidden_topics),
    )
    return MemoryListResponse(facts=facts, forbidden_topics=forbidden_topics)


@app.post("/memory/refresh")
async def refresh_memory(user_id: str) -> MemoryRefreshResult:
    history = chat_history.window(user_id, settings.memory_refresh_window)
    user_messages = [item["content"] for item in history if item["role"] == "user"]
    if not user_messages:
        logger.info("memory.refresh.skip_empty user_id=%s", user_id)
        return MemoryRefreshResult(added=0, processed_messages=0)

    before = len(memory.list_facts(user_id))
    transcript = "\n".join(f"User: {message}" for message in user_messages)
    await mindly_graph.save_memory(
        make_initial_state(
            user_id=user_id,
            persona="wellness_friend",
            message=transcript,
            history=[],
        )
    )
    after = len(memory.list_facts(user_id))
    added = max(after - before, 0)
    logger.info(
        "memory.refresh user_id=%s processed_messages=%s added=%s",
        user_id,
        len(user_messages),
        added,
    )
    return MemoryRefreshResult(added=added, processed_messages=len(user_messages))


@app.delete("/memory/all")
async def forget_all_memory(user_id: str) -> ForgetResult:
    memory_deleted = memory.forget_all(user_id)
    history_deleted = chat_history.clear(user_id)
    deleted = memory_deleted + history_deleted
    logger.info(
        "forget_all user_id=%s memory_deleted=%s history_deleted=%s",
        user_id,
        memory_deleted,
        history_deleted,
    )
    return ForgetResult(deleted=deleted)