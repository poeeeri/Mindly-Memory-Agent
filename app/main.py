import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.graph import MindlyGraph, make_initial_state
from app.llm import OpenRouterClient
from app.logging_config import configure_logging
from app.memory import DummyMemory
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
memory = DummyMemory()
mindly_graph = MindlyGraph(
    memory=memory,
    llm=OpenRouterClient(settings),
    history_window=settings.history_window,
)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    persona: str = "wellness_friend"
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class ForgetResult(BaseModel):
    deleted: int


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    state = make_initial_state(
        user_id=request.user_id,
        persona=request.persona,
        message=request.message,
        history=request.history,
    )
    logger.info("chat.start user_id=%s persona=%s", request.user_id, request.persona)
    return StreamingResponse(
        mindly_graph.astream_response(state),
        media_type="text/plain; charset=utf-8",
    )


@app.delete("/memory")
async def forget_memory(user_id: str, query: str) -> ForgetResult:
    deleted = memory.forget(user_id, query)
    logger.info("memory.forget user_id=%s deleted=%s", user_id, deleted)
    return ForgetResult(deleted=deleted)


@app.delete("/memory/all")
async def forget_all_memory(user_id: str) -> ForgetResult:
    deleted = memory.forget_all(user_id)
    logger.info("memory.forget_all user_id=%s deleted=%s", user_id, deleted)
    return ForgetResult(deleted=deleted)