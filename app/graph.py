from collections.abc import AsyncIterator
import logging
import re
import time

from langgraph.graph import END, StateGraph

from app.llm import OpenRouterClient, OpenRouterError
from app.memory.base import MemoryStore
from app.prompts import build_prompt
from app.state import AgentState, ChatMessage

logger = logging.getLogger(__name__)


# память агента спрятана за интерфейсом MemoryStore, чтобы потом заменить на MemPalace
class MindlyGraph:
    def __init__(self, *, memory: MemoryStore, llm: OpenRouterClient, history_window: int = 8) -> None:
        """
        создаем два графа: один - полный граф, включая генерацию ответа LLM (graph), другой - граф без генерации (prep_graph 
        при стриминге, чтобы сначала собрать промпт и найти релевантную память, а потом уже стримить токены напрямую из LLM);
        компилируем граф и добавляем узлы и ребра
        """
        self.memory = memory
        self.llm = llm
        self.history_window = history_window
        self.graph = self._compile_graph(include_generation=True)
        self.prep_graph = self._compile_graph(include_generation=False)

    def _compile_graph(self, *, include_generation: bool):
        graph = StateGraph(AgentState)
        graph.add_node("check_forget_command", self.check_forget_command)
        graph.add_node("retrieve_memory", self.retrieve_memory)
        graph.add_node("build_prompt", self.build_prompt)
        graph.add_node("save_memory", self.save_memory)
        graph.set_entry_point("check_forget_command")

        # пайплайн работы проверки сообщения на команду
        graph.add_conditional_edges(
            "check_forget_command",
            self._route_after_forget_check,
            {"forget": "save_memory", "continue": "retrieve_memory"},
        )
        graph.add_edge("retrieve_memory", "build_prompt")
        if include_generation:
            graph.add_node("generate_response", self.generate_response)
            graph.add_edge("build_prompt", "generate_response")
            graph.add_edge("generate_response", "save_memory")
        else:
            graph.add_edge("build_prompt", END)
        graph.add_edge("save_memory", END)
        return graph.compile()

    def check_forget_command(self, state: AgentState) -> AgentState:
        message = state["message"].strip()
        lowered = message.lower()
        if lowered in {"/forget_all", "удали все мои данные", "забудь все обо мне"}:
            deleted = self.memory.forget_all(state["user_id"])
            return {**state, "forget_command": "all", "response": f"Готово, удалено записей: {deleted}."}

        match = re.match(r"^(/forget|забудь,?|забудь что)\s+(?P<query>.+)$", lowered, flags=re.IGNORECASE)
        if match:
            query = match.group("query").strip()
            deleted = self.memory.forget(state["user_id"], query)
            return {**state, "forget_command": query, "response": f"Готово, удалено записей: {deleted}."}

        return {**state, "forget_command": None}

    def retrieve_memory(self, state: AgentState) -> AgentState:
        memories = self.memory.search(state["user_id"], state["message"])
        logger.info("memory.search user_id=%s count=%s", state["user_id"], len(memories))
        return {**state, "memories": memories}

    def build_prompt(self, state: AgentState) -> AgentState:
        history = state.get("history", [])[-self.history_window :]
        messages = build_prompt(
            persona=state["persona"],
            memories=state.get("memories", []),
            history=history,
            message=state["message"],
        )
        return {**state, "prompt_messages": messages}

    async def generate_response(self, state: AgentState) -> AgentState:
        response = await self.llm.complete_chat(state["prompt_messages"])
        return {**state, "response": response}

    def save_memory(self, state: AgentState) -> AgentState:
        # если это forget-команда - ничего не сохраняем
        if state.get("forget_command"):
            return state
        text = state["message"].strip()
        if text:
            self.memory.add(state["user_id"], text)
            logger.info("memory.add user_id=%s", state["user_id"])
        return state

    @staticmethod
    def _route_after_forget_check(state: AgentState) -> str:
        return "forget" if state.get("forget_command") else "continue"

    async def ainvoke(self, state: AgentState) -> AgentState:
        return await self.graph.ainvoke(state)

    async def astream_response(self, state: AgentState) -> AsyncIterator[str]:
        """
        здесь происходит стриминг ответа ллм модели по токенам (+ замер ttft_ms).
        только когда ответ модели полностью получен, схраняем в память 
        """
        prepared = await self.prep_graph.ainvoke(state)
        if prepared.get("forget_command"):
            yield prepared["response"]
            return

        started = time.perf_counter()
        first_token_seen = False
        chunks: list[str] = []
        try:
            async for chunk in self.llm.stream_chat(prepared["prompt_messages"]):
                if not first_token_seen:
                    prepared["ttft_ms"] = (time.perf_counter() - started) * 1000
                    logger.info("llm.ttft_ms=%.2f user_id=%s", prepared["ttft_ms"], prepared["user_id"])
                    first_token_seen = True
                chunks.append(chunk)
                yield chunk
        except OpenRouterError as exc:
            logger.exception("llm.openrouter_error user_id=%s status=%s", prepared["user_id"], exc.status_code)
            # читаемая ошибка для пользователя
            yield (
                "**OpenRouter вернул ошибку.**\n\n"
                f"- Статус: `{exc.status_code or 'request error'}`\n"
                f"- Детали: `{exc.detail}`\n\n"
                "Проверь `OPENROUTER_API_KEY`, баланс/credits и доступность модели "
                f"`{' -> '.join(self.llm.model_chain)}`."
            )
            return

        await self.save_after_stream(prepared, "".join(chunks))

    async def save_after_stream(self, state: AgentState, response: str) -> None:
        self.save_memory({**state, "response": response})


def make_initial_state(
    *,
    user_id: str,
    persona: str,
    message: str,
    history: list[ChatMessage] | None = None,
) -> AgentState:
    return {
        "user_id": user_id,
        "persona": persona,
        "message": message,
        "history": history or [],
    }