from collections.abc import AsyncIterator, Callable
import logging
import re
import time

from langgraph.graph import END, StateGraph

from app.forbidden_topics import (
    build_forbidden_topic_response,
    extract_forbidden_topic,
    filter_forbidden_memories,
)
from app.forget_commands import try_handle_forget_all, try_handle_forget_query
from app.llm import OpenRouterClient, OpenRouterError
from app.memory.base import MemoryStore
from app.memory.extractor import FactExtractionError, FactExtractor
from app.prompts import build_prompt
from app.state import AgentState, ChatMessage

logger = logging.getLogger(__name__)


class MindlyGraph:
    def __init__(
        self, *, memory: MemoryStore, llm: OpenRouterClient,
        fact_extractor: FactExtractor | None = None,
        history_window: int = 8,
        on_forget_all: Callable[[str], int] | None = None,
    ) -> None:
        """
        Собираем два графа: полный graph для обычного вызова и prep_graph для
        стриминга, где сначала готовится промпт, а потом токены идут напрямую
        из LLM
        """
        self.memory = memory
        self.llm = llm
        if fact_extractor is None:
            raise ValueError("fact_extractor is required")
        self.fact_extractor = fact_extractor
        self.history_window = history_window
        self.on_forget_all = on_forget_all
        self.graph = self._compile_graph(include_generation=True)
        self.prep_graph = self._compile_graph(include_generation=False)

    def _compile_graph(self, *, include_generation: bool):
        graph = StateGraph(AgentState)
        graph.add_node("check_forget_command", self.check_forget_command)
        graph.add_node("retrieve_memory", self.retrieve_memory)
        graph.add_node("build_prompt", self.build_prompt)
        graph.set_entry_point("check_forget_command")

        # сначала проверяем команды забывания, затем идем в обычный retrieval
        graph.add_conditional_edges(
            "check_forget_command",
            self._route_after_forget_check,
            {"forget": END, "continue": "retrieve_memory"},
        )
        graph.add_edge("retrieve_memory", "build_prompt")
        if include_generation:
            graph.add_node("generate_response", self.generate_response)
            graph.add_edge("build_prompt", "generate_response")
            graph.add_edge("generate_response", END)
        else:
            graph.add_edge("build_prompt", END)
        return graph.compile()

    def check_forget_command(self, state: AgentState) -> AgentState:
        message = state["message"].strip()
        user_id = state["user_id"]

        forget_all_result = try_handle_forget_all(
            user_id=user_id,
            message=message,
            memory=self.memory,
            on_forget_all=self.on_forget_all,
        )
        if forget_all_result:
            return {**state, **forget_all_result}

        forbidden_topic = extract_forbidden_topic(message)
        if forbidden_topic:
            created = self.memory.add_forbidden_topic(user_id, forbidden_topic)
            return {
                **state,
                "forget_command": "forbidden_topic",
                "response": build_forbidden_topic_response(forbidden_topic, created=created),
            }

        match = re.match(r"^(/forget|забудь,?|забудь что)\s+(?P<query>.+)$", message, flags=re.IGNORECASE)
        if match:
            query = match.group("query").strip()
            return {**state, **try_handle_forget_query(user_id=user_id, query=query, memory=self.memory)}

        return {**state, "forget_command": None}

    def retrieve_memory(self, state: AgentState) -> AgentState:
        memories = self.memory.search(state["user_id"], state["message"])
        forbidden_topics = self.memory.list_forbidden_topics(state["user_id"])
        filtered_memories = filter_forbidden_memories(memories, forbidden_topics)
        logger.info(
            "memory.search user_id=%s count=%s filtered=%s forbidden_topics=%s",
            state["user_id"],
            len(memories),
            len(memories) - len(filtered_memories),
            len(forbidden_topics),
        )
        return {**state, "memories": filtered_memories, "forbidden_topics": forbidden_topics}

    def build_prompt(self, state: AgentState) -> AgentState:
        history = state.get("history", [])[-self.history_window :]
        messages = build_prompt(
            persona=state["persona"],
            memories=state.get("memories", []),
            forbidden_topics=state.get("forbidden_topics", []),
            history=history,
            message=state["message"],
        )
        return {**state, "prompt_messages": messages}

    async def generate_response(self, state: AgentState) -> AgentState:
        response = await self.llm.complete_chat(state["prompt_messages"])
        return {**state, "response": response}

    async def save_memory(self, state: AgentState) -> AgentState:
        # Forget-команды не сохраняем обратно в память
        if state.get("forget_command"):
            return state

        try:
            facts = await self.fact_extractor.extract(state["message"].strip())
        except (FactExtractionError, OpenRouterError) as exc:
            logger.warning("memory.fact_extraction_failed user_id=%s detail=%s", state["user_id"], exc)
            return state
        for fact in facts:
            self.memory.add_fact(
                user_id=state["user_id"],
                fact_text=fact.text,
                source=f"extractor:{fact.kind}",
            )
        logger.info("memory.add_facts user_id=%s count=%s", state["user_id"], len(facts))
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
            yield (
                "**OpenRouter вернул ошибку.**\n\n"
                f"- Статус: `{exc.status_code or 'request error'}`\n"
                f"- Детали: `{exc.detail}`\n\n"
                "Проверь `OPENROUTER_API_KEY`, баланс/credits и доступность модели "
                f"`{' -> '.join(self.llm.model_chain)}`."
            )
            return

        prepared["response"] = "".join(chunks)


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