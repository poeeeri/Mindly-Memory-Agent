import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.graph import MindlyGraph, make_initial_state
from app.history import ChatHistoryStore
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

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# память временно заменена на объект заглушки
llm_client = OpenRouterClient(settings)
memory = build_memory(settings)
chat_history = ChatHistoryStore(max_messages=settings.history_window * 4)
mindly_graph = MindlyGraph(
    memory=memory,
    llm=llm_client,
    fact_extractor=build_fact_extractor(settings, llm_client),
    history_window=settings.history_window,
)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    persona: str = "wellness_friend"
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class ForgetResult(BaseModel):
    deleted: int


class ChatHistoryResponse(BaseModel):
    history: list[ChatMessage]


class MemoryListResponse(BaseModel):
    facts: list[MemoryFact]


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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
        chat_history.append_exchange(user_id, user_message, assistant_message)
        logger.info("chat.history.append user_id=%s messages=%s", user_id, len(chat_history.list(user_id)))


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
    logger.info("memory.list user_id=%s count=%s", user_id, len(facts))
    return MemoryListResponse(facts=facts)


@app.delete("/memory/all")
async def forget_all_memory(user_id: str) -> ForgetResult:
    deleted = memory.forget_all(user_id)
    logger.info("memory.forget_all user_id=%s deleted=%s", user_id, deleted)
    return ForgetResult(deleted=deleted)